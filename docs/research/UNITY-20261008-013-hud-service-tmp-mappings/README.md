# UNITY-20261008-013: hud-service keeps deleted /tmp files mapped, and RSS grows, with every HUD query

Owner: agent B (target2). Found by the UNITY-20260929-001 Verifier.

```yaml
task_id: UNITY-20261008-013
package: hud (hud-service)
target_series: resolute
issue: local - found in UNITY-20260929-001
status: INVESTIGATING
observed: >
  hud-service holds more and more deleted 128 KiB "/tmp/#<inode>" shared
  mappings (files opened with O_TMPFILE) over a session, and its RSS grows
  with them.
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

Next:
1. Which library creates the three files per query: strace with stacks on CreateQuery and CloseQuery. Dee's own code opens no O_TMPFILE file (its only mmap is the file resource manager, which hud does not use), so the suspects are Qt, GLib and columbus.
2. Then the design for the Design Challenger.
