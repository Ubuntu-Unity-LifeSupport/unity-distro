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

### Design review, round 1: REVISE (all points taken)

The Design Challenger (an independent subagent) confirmed the diagnosis
and the layer:
- `~Trie` is the only leak.
- `Trie.cc` is the only place with a mapping or a tmpfile.
- 128 KiB is the 1 KiB start size doubled seven times, so 3 × 128 KiB per
  query is ~0.4 MB.
- The Tries really are destroyed when a query closes: `WindowImpl` keeps a
  weak pointer to its token, and each activation builds a new token,
  ItemStore and Matcher.
- The ABI is safe: `TriePrivate` lives in `Trie.cc`, `Trie.hh` is not
  installed, and no Trie symbol is exported (`libcolumbus.map` ends in
  `local: *`).

Its points:

1. **`expand()` leaves `MAP_FAILED`, not `nullptr`, when `mmap` fails.**
   `p->h` is then dangling too, and the next `expand()` would take the
   "first time" branch and truncate the file to 1 KiB. Revised: the old
   mapping stays valid until the new one exists, so a failure changes
   nothing.
2. **`mapSize` and the header cannot differ after a successful expand.**
   `mapSize` is still kept, for the state after a failure.
3. **The order of `munmap` and `fclose` does not matter** for a `MAP_SHARED`
   O_TMPFILE: the inode goes when both the fd and the mapping are gone.
4. **Exception safety** is cheap hardening and has no double free. It is
   structured once: `TriePrivate` gets a destructor (unmap, close) and the
   constructor holds it in a `unique_ptr` until it is complete.
   `~Trie` becomes `delete p`. The try scope covers `addNewNode(0)`, which
   can call `expand()`. No new exported symbol (with
   `DPKG_GENSYMBOLS_CHECK_LEVEL=4`, a new symbol under the wildcard
   exports would fail the build): the cleanup stays file-local.
5. **The test could pass without proving anything.** In this sbuild,
   `/proc` is mounted with "or warn". If `/proc/self/maps` cannot be read,
   0 = 0 passes, on the control too.
   - The test asserts the file opened.
   - It checks liveness: while a Trie lives, the count is baseline + 1
     (+3 for an indexed Matcher), and after destruction it is back to
     baseline.
   - It counts every `(deleted)` line, not only `/tmp/#`: in the chroot
     `/tmp` is ext4, which supports O_TMPFILE, but glibc's fallback names
     the file `/tmp/tmpfXXXXXX`.
6. **The expand test proves expand ran:** the live mapping spans more than
   1 KiB. The Matcher test calls `index()` with two fields: without
   `index()` only the WordStore Trie exists, and two fields give hud's
   three Tries.
7. **hud stays as it is.** One Matcher per query is hud's design; after the
   fix it costs CPU, not memory.
8. **unity-lens-applications** (C's addition) does not leak per search. It
   runs in the long-lived `unity-scope-loader` with long-lived Matchers.
   It leaks when the application menu is re-indexed: `app_menu.changed`
   after a 5 s timeout builds a new searcher and frees the old one, so
   +3 Tries each time. Its search behaviour is unchanged, because the fix
   touches only destruction and no pointer into the mapping leaves the
   Trie. The target plan measures that re-index.
9. **Target:** a liveness check (a query open: +3; after CloseQuery:
   baseline), and no "(deleted)" libcolumbus mapping in both processes
   after the cold cycle.
10. **Version:** `1.1.0+15.10.20150806-0ubuntu39+unity1` sorts above
    `0ubuntu39` and `0ubuntu39build1`, and below `0ubuntu39.1` or
    `0ubuntu40`. An Ubuntu upload of either would replace the fix without
    it: the usual risk of a carried package, noted here.

Remark, left alone: `madvise(MADV_RANDOM | MADV_WILLNEED)` combines two
advice values with `|`, which is not valid (it ends up as
`MADV_WILLNEED`). It is pre-existing and harmless.

## Design, revised after round 1

**`src/Trie.cc`** (no header, export or symbols change):

- **`TriePrivate`** gains `TrieOffset mapSize` and a destructor: if `map`
  is set (never `MAP_FAILED`, see below) `munmap(map, mapSize)`, logging a
  failure to stderr; then `fclose(f)` if open.
- **`Trie::Trie()`** builds `TriePrivate` in a `std::unique_ptr`:
  `tmpfile()` (throws as now), `expand()`, the header,
  `addNewNode(0)`, then `p = holder.release()`. On any throw, the
  `unique_ptr` cleans up.
- **`Trie::~Trie()`** is `delete p`.
- **`expand()`:**
  1. `newSize` (1024 when `mapSize` is 0, or twice `mapSize`; above
     `UINT32_MAX / 2` it throws "Trie too large" first, round 2);
  2. `ftruncate(newSize)` (throws on failure, with the old map unchanged);
  3. `mmap` into a local variable; on `MAP_FAILED` it throws, with the old
     map, `h` and `mapSize` unchanged;
  4. the old map is unmapped (a failure is logged);
  5. `map`, `h` and `mapSize` are assigned, then the header's `totalSize`
     and `madvise` as now.

**Tests (`test/`, run by ctest in the build):**

- a helper `deletedMappings()`: opens `/proc/self/maps` (asserts it
  opened) and counts the lines ending in `(deleted)`;
- `TrieTest`:
  - `testNoMappingLeft`: baseline; while a Trie lives, baseline + 1;
    after 50 create/destroy cycles, baseline;
  - `testNoMappingLeftAfterExpand`: a Trie with enough distinct words for
    several expansions; while alive, its mapping is larger than 1 KiB
    (read from the maps line); after destruction, baseline;
- `MatcherTest` (the existing `testCorpus()` helper, or an inline corpus
  with two fields, then `index()`): while one indexed Matcher lives,
  baseline + 3; after 20 create, index and destroy cycles, baseline;
- **control:** the same tests on the unpatched source fail (the trie test
  compiles `Trie.cc` directly, the matcher test links the in-tree
  library).

**Target check** (Clean-2 + the live publication, then libcolumbus +unity1
from a file repository, a cold cycle; before and after):

- **hud-service:**
  - `leak.sh`: +0 deleted files per 10 queries (now +30), and RSS per
    query close to 0 after the first queries;
  - liveness: while a query is open, +3; after CloseQuery, the baseline;
  - the HUD answers as before: Writer "Сохранить", Terminal "Создать окно".
- **unity-lens-applications:**
  - `unity-scope-loader` running the applications scope (`pgrep -x
    unity-scope-loa`, then `applications` in `/proc/PID/cmdline`);
  - its deleted mappings before and after K re-indexes: add and remove a
    desktop file in `~/.local/share/applications`, waiting more than 5 s
    each time;
  - expected +3 per re-index before the fix and +0 after;
  - the Dash still finds an application (its scope over D-Bus, or a
    screenshot).
- **Both processes** have no "(deleted)" libcolumbus mapping after the
  cold cycle.

### Design review, round 2: REVISE (one point, taken)

The Design Challenger checked the two questions:

- **A later `expand()` after a failed `mmap` is correct.**
  - The file stays at the new size while the map, `h`, `mapSize` and the
    header keep the old one.
  - `append()` keeps calling `expand()` with a correct bound, the next
    `ftruncate` to the same size does nothing, and the `mmap` is retried.
  - Pages of the file beyond the mapping are just not mapped.
- **"Throw with everything unchanged" is safe for the callers.**
  - `append` moves `firstFree` only after `expand()` returns.
  - A failed `addNewNode` or `addNewSibling` leaves only an orphaned node;
    links are written after both appends.
  - A failed `insertWord` leaves prefix nodes without a word (they are not
    found), and `numWords` is unchanged.
  - The callers (`LevenshteinIndex::insertWord`, `WordStore::getID`)
    update their own state only after the insert returns.

The one point: `TrieOffset` is `uint32_t`. Above 2 GiB, `2 * mapSize`
wraps to 0. The old order (unmap first) then failed cleanly. The new order
would truncate the file to 0 under the live mapping, and the next access
would raise SIGBUS. Taken into the design: before `ftruncate`, `expand()`
throws `runtime_error("Trie too large")` if `mapSize > UINT32_MAX / 2`. Our
users never get near that size.
