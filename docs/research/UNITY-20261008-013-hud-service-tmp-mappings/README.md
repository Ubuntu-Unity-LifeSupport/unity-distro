# UNITY-20261008-013: hud-service keeps deleted /tmp files mapped, and RSS grows, with every HUD query

Owner: agent B (target2). Found by the UNITY-20260929-001 Verifier.

```yaml
task_id: UNITY-20261008-013
package: libcolumbus (the symptom is in hud-service; the correct layer is libcolumbus)
target_series: resolute
issue: local - found in UNITY-20260929-001
status: INVESTIGATING
observed: >
  hud-service holds more and more deleted 128 KiB "/tmp/#<inode>" shared
  mappings (files opened with O_TMPFILE) over a session, and its RSS grows
  with them: three per HUD query, in every hud version. The cause is
  libcolumbus Trie::~Trie(), which never unmaps its tmpfile mapping.
```

## Comparison of versions (2026-10-08, target2, logs/01)

The setup was one stack for every version:
1. target2 restored to Clean-2.
2. The live publication by apt (unity +unity12 at that moment).
3. Only `apt-get install hud=<version>` between runs.

Each run started from a cold cycle and used the same `leak.sh` (a baseline, 10 HUD queries on the desktop, 10 Mines starts, 10 Writer starts, 10 queries in Writer, 60 s idle). One query is CreateQuery "" + CloseQuery, as the HUD opens and closes.

| step | 0ubuntu6 (archive) | +unity3 | +unity4 | +unity5 (newer stack) |
|---|---|---|---|---|
| baseline | 0 files, 30.4 MB | 0, 30.4 MB | 0, 30.5 MB | 0, 30.3 MB |
| + 10 queries (desktop) | +30 files, +4.6 MB | +30, +4.6 MB | +30, +4.7 MB | +30, +4.5 MB |
| + 10 Mines starts | +0, ±0 | +0, ±0 | +0, ±0 | +0, ±0 |
| + 10 Writer starts | +0, +4.7 MB | +0, +4.7 MB | +0, +4.5 MB | +0, +4.7 MB |
| + 10 queries (Writer) | +30, +3.9 MB | +30, +4.0 MB | +30, +4.0 MB | +30, +4.0 MB |
| Writer closed, 60 s idle | nothing released | nothing released | nothing released | nothing released |

- **Per query:** every HUD query leaves exactly 3 deleted `/tmp/#` files mapped, and about 0.4 MB of RSS. Nothing is released when the query is closed, or later.
- **Window starts** add no files. The 10 Writer starts add about 4.7 MB of RSS (menus imported and kept, by the code; to be checked).
- **The archive hud has it.** 0ubuntu6 behaves like +unity3 and +unity4, so our revisions did not add it.
- **Correction:** the UNITY-20260929-001 Verifier's "about 60 per Writer start, about 72 with a move" came from the HUD queries inside its steps. Window starts and the move add no files.
- **+unity5 was measured on a newer stack.** The first attempt was lost when the VM aborted on the cold start (2026-10-08 ~21:08Z; May saved the VM log). The run after the restore used the live publication of that moment: unity +unity13 and light-locker +unity3 instead of +unity12 and the archive light-locker. Its numbers are the same as the others', so the stack does not change the leak.

## Where the files come from (2026-10-08, logs/02)

`strace -f -k` on hud-service (+unity5) during one HUD query shows exactly
three `openat("/tmp", O_RDWR|O_EXCL|O_TMPFILE)` calls. All three come from
`tmpfile()` in **libcolumbus** (1.1.0+15.10.20150806), the error-tolerant
matcher hud-service uses for its search:

- `Columbus::Matcher::Matcher()` → `Columbus::WordStore::WordStore()` → a
  Trie: the first file;
- `Columbus::LevenshteinIndex::LevenshteinIndex()` → a Trie, twice: the
  second and third files.

hud-service builds one `Columbus::Matcher` per query: `ItemStore` has a
`Columbus::Matcher m_matcher` (`service/ItemStore.h:84`). So each query
creates three Tries and, when it is closed, destroys them.

**The leak is in libcolumbus `src/Trie.cc`:**
- `Trie::Trie()` opens a `tmpfile()`, `ftruncate`s it and `mmap`s it
  `MAP_SHARED`; `expand()` doubles the size, with `munmap` of the old map.
- `Trie::~Trie()` only calls `fclose(p->f)` and `delete p`. It never
  `munmap`s `p->map`.

The file descriptor is closed, which matches the steady fd count in logs/01.
The deleted file stays mapped together with its pages for the life of the
process: 3 mappings per query, and the RSS with them.


## The Writer starts (2026-10-08, logs/03)

30 Writer starts in the same session, with no HUD query, leave hud-service's RSS at 44.2-44.3 MB and add no mapping. The +4.7 MB of the first 10 starts in logs/01 is a one-time cost: the menus imported and kept. It is not a leak, so there is no follow-up.

## Existing-fix discovery (subagent, read-only, 2026-10-08)

Result: **NOT_FIXED**; issue search **NOT_FOUND** for this bug.

- **Upstream** `~unity-team/libcolumbus/trunk`: last revision 2015-08-06, the same code as our source; read through the git import `github.com/megari/libcolumbus`. `~Trie` there has no `munmap` (`src/Trie.cc:91-94`).
- **Ubuntu:** every series from trusty to resolute and stonking. resolute has `1.1.0+15.10.20150806-0ubuntu39`; its only patch is a Python 3.10 build fix, and ubuntu35 to ubuntu39 are no-change rebuilds and a symbols edit. Nothing newer in -proposed.
- **Elsewhere:** Debian does not package it; no Lomiri fork; the Arch and AUR copies carry no patches.
- **Launchpad:** nothing on the missing `munmap`. Related reports:
  - LP#1282261: SIGBUS in `Trie::append` blamed on a full /tmp. The leaked mappings keep deleted /tmp files allocated; this is not proven to be the cause.
  - LP#1257215: `tmpfile()` failure; it added the throw.
  - Several reports of hud-service memory growth without a root cause: LP#1253593, #1645186, #1670507, #1368896, #987060.
- **Reverse dependencies in resolute:** `libcolumbus1v5` is used by hud and unity-lens-applications (both installed on target2), and by python3-columbus and libcolumbus1-dev, which nothing uses.
- **Other weaknesses in the same code:**
  - `Trie::Trie()` leaks `p` (and the file) when `tmpfile()` or `expand()` throws.
  - `expand()` leaves `p->map` dangling when the new `mmap` fails after the old one was unmapped.
  - `Matcher` and `ErrorValues` delete only `operator=`, not the copy constructor; this is latent.
  - `Word`'s move assignment to itself deletes its own text.
  - No other destructor leaks: WordStore, LevenshteinIndex, ErrorValues, ErrorMatrix and Matcher are correct.

## Design (for the Design Challenger)

**Invariant:** a destroyed Trie leaves no mapping and no file behind. A
process that creates and destroys Matchers keeps a constant number of
mappings.

**Package:** libcolumbus `1.1.0+15.10.20150806-0ubuntu39+unity1`, source
format 1.0 as the archive has it. The change goes in the tree, as with hud;
the existing `debian/patches` is left as it is.

**`src/Trie.cc`:**

1. `TriePrivate` gains `TrieOffset mapSize`, the size of the current
   mapping. It is kept outside the mapping, so the destructor does not read
   the size from memory it is about to unmap. `TriePrivate` is private (a
   pimpl), so the ABI does not change; the symbols file stays.
2. **`~Trie()`:** if `p->map` is set, `munmap(p->map, p->mapSize)`, then
   `fclose(p->f)` (if open), then `delete p`.
   - Unmapping first is the natural order. Either order frees the pages once
     both are done, and the file is gone when the last reference goes.
   - A failed `munmap` in a destructor cannot be reported by an exception: it
     is written to stderr and ignored.
3. **`expand()`:**
   - Before it unmaps, the old size is taken from `p->mapSize`.
   - After a successful `munmap`, `p->map = nullptr` and `p->mapSize = 0`, so
     a failed `ftruncate` or `mmap` does not leave a dangling map for the
     destructor.
   - After a successful `mmap`, `p->mapSize = newSize`.
   - The header write (`p->h->totalSize`) stays as it is; the file format is
     unchanged.
4. **`Trie()` exception safety:** if `tmpfile()` fails, `delete p` before
   the throw. If `expand()` throws, the constructor unmaps (when mapped),
   closes the file and deletes `p`, then rethrows. Without it, the
   destructor would never run for a half-built object, and the fix would
   still leak there.
5. **Not in scope**, recorded as remarks: the latent copy constructors of
   Matcher and ErrorValues, and Word's self move. None of them is reached
   by hud or the lens, and changing the public headers would touch the ABI.

**Tests** (`test/TrieTest.cc`, run by `dh_auto_test` / ctest in the build):

- `testNoMappingLeft`: count `/proc/self/maps` lines with `(deleted)`,
  create and destroy 50 Tries with a few words each, and count again: the
  same number. Before the fix it grows by 50.
- `testNoMappingLeftAfterExpand`: a Trie that grows (enough words for
  several `expand()` calls), then destroyed: no mapping left.
- A Matcher test (`test/MatcherTest.cc` or a new one in the existing
  `coltest` set): create and destroy 20 `Columbus::Matcher`s with a small
  corpus (`index`), then count the mappings as above. This is the hud
  pattern.
- **Control:** the same tests on the unpatched source must fail. They are
  in a separate commit, and a control build is made without the fix.
- The existing tests (trie, levtrie, the others) pass.

**Target check** (Clean-2 + the live publication, then libcolumbus +unity1
from a file repository, a cold cycle):

- `leak.sh` before and after:
  - +0 deleted `/tmp/#` files per 10 queries, from +30 now;
  - RSS per query close to 0 (the first queries may still allocate caches);
- the HUD still answers: Writer "Сохранить" and Terminal "Создать окно"
  give the same results;
- unity-lens-applications: the Dash application search still finds an
  application, checked by its scope over D-Bus or by a screenshot of the
  Dash;
- running processes use the new library: no `(deleted)` libcolumbus
  mapping in hud-service.
