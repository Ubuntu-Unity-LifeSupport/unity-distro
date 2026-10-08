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

Next:
1. Existing-fix discovery for libcolumbus: newer Ubuntu and Debian, upstream (lp:libcolumbus), Launchpad bugs.
2. Then the design for the Design Challenger. C's decision (2026-10-08): this task carries libcolumbus +unity1 (`munmap` in `~Trie`); hud is not changed.
3. The Writer starts' RSS (+4.7 MB per 10 starts, no files) is a separate question: menus imported and kept, or another leak.
