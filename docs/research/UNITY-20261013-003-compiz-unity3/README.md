# UNITY-20261013-003, UNITY-20261013-004: compiz +unity3 (compizconfig closes descriptors once)

Agent A, target `target-desktop`.

## What was wrong

On 2026-10-13 the Unity session ended at login once on `target-desktop`:
`unity-active-plugins-safety-check` (run by `unity7.service` before compiz)
aborted with "buffer overflow detected" while reading
`~/.config/compiz-1/compizconfig/done_upgrades`, `unity7.service` failed and
lightdm went back to the greeter. The abort itself is reproduced every time
with a completed upgrades file whose size cannot be measured (a FIFO); in
the core of the original abort the file's descriptor was gone.

- **UNITY-20261013-004 (the cause).** libcompizconfig closed descriptors
  twice:
  - the plugin metadata cache (`compiz.cpp`): the `.pb` file was read
    through a protobuf `FileInputStream` on `fileno()` of a `FILE`; the
    stream's `Close()` closed the descriptor and `fclose()` closed the same
    number again, once per plugin on every `ccsContextNew()`; the cache
    writer did the same with a `FileOutputStream`;
  - `iniparser_dump_ini`: `fclose()` of a stream made with `fdopen()` on
    the lock's descriptor, then `ini_file_unlock()` closed that descriptor
    again.

  With the gsettings backend, dconf and GDBus threads open files while the
  plugins load. When one of them had just been given the number, the second
  close took that file away: in a loop of direct runs, dconf reported
  "will not work properly" in some runs, and one run aborted on a dconf
  assertion after a chain of closes on numbers that had already been given
  to other files; in the core of the original abort the completed upgrades
  file had lost its descriptor. The same code runs inside compiz itself at start
  (the ccp plugin), where the X and ICE connections and the plugins' xml
  files are open.
- **UNITY-20261013-003 (the abort).** `ccsUnixTextFileReadFromStart` took
  `ftell()`'s result as an unsigned size without checking it. On a
  descriptor that was gone, `ftell()` returned -1, the size became
  4294967295 and the read aborted the program.

The preloaded libraries of the session (gtk-nocsd, unity-gtk4-menu) take
no part: the threads come from libcompizconfig's gsettings backend, the
double closes happen with or without them, and no close in the recorded
stacks comes from them.

## What is fixed

| package | version | change |
|---|---|---|
| compiz | 1:0.9.14.2+25.10.20250930-0ubuntu3+unity3 | Commits on the published +unity2 (`5610bd4`), branch `a/UNITY-20261013-003`. |

- `bb5dd6e` (-004): the plugin metadata cache file is closed once; the
  writer flushes the stream before `fclose()`, reports a failed write or
  close, and removes a cache entry that was not written completely.
- `5dd6985` (-004): the saved ini file is closed once; `ini_file_lock()`
  also closes the descriptor when it cannot allocate the lock.
- `a21a2e4` (-003): a file whose size cannot be measured is treated like
  one that cannot be read; the caller then skips the settings upgrade check
  and tries again next time.
- `e758979`, `4d7ead5`: tests (`compizconfig_test_fd_ownership`, a program
  that counts descriptors closed twice; reader tests in
  `compizconfig_test_ccs_text_file`), run by `make check`.
- `cb67cb7`: changelog. No change to `debian/control`.

## Build

Built with `scripts/build_sbuild.py` from `4d7ead5`, chroot snapshot
T=20261008T083223Z. `make check`: 1439 tests, all pass. The manifest is in
`build/`.

## Checks

- **Tests:** on +unity2 with the new tests, five of the six new tests fail
  (the reader cases with "buffer overflow detected", the ini cases with a
  close failing with EBADF, the cache case with closes on closed
  descriptors); the read-append-read test passes on both. On +unity3 all
  pass (`gate/base-red.txt`).
- **Target** (`gate/target-test.txt`): closes of already closed
  descriptors in compiz, compiz-config-profile-setter and
  unity-active-plugins-safety-check at session start go from 106 / 258 /
  99 on +unity2 to 0 on +unity3 in three cold boots; in 100 traced direct
  runs of the safety check from 3157 (libcompizconfig) and 18 (GLib) to 0,
  and dconf's "will not work properly" from 4 to 0; 200 further runs
  without tracing: no failure, no dconf message; with an unreadable
  completed upgrades file the session starts and the programs log a
  warning.

## Verification

- Target test before publication: PASS (`gate/target-test.txt`).
- Check on the target after publication: PASS. Published 2026-10-13
  08:01:51Z as `unity-resolute-20261013-003`; the target updated from the
  live repository, cold boot: the session is up, and compiz, the profile
  setter and the safety check close no descriptor twice
  (`gate/target-verification.txt`).
- Independent verification: PASS (the Verifier reviewed the diff against the
  approved design, the tests on +unity2 and +unity3, the build record and
  the target record against its raw measurements).

## Not changed / known limits

- The compiz crash on another test machine after "Failed to load plugin"
  and an xml read error is consistent with this mechanism (descriptors
  taken from compiz at start) but not proven.
- Follow-ups: UNITY-20261013-005 (`ini_file_lock` truncates before it
  locks), UNITY-20261013-006 (`iniparser_new` releases its read lock early),
  UNITY-20261013-012 (the new tests leave their `/tmp/ccs-*` directories).
- `CompTimerTestCallback.TimerOrder`, a timing-dependent test of compiz
  core, failed once in a +unity2 build with the new tests and passed in the
  +unity3 builds; unrelated.

## Publication

- **Database backup:** `/home/claude/backups/UNITY-20261013-003-20261013T075435Z`.
  21 files, complete, equal to live; list sha256
  `0f7d552ad18e8df773032a7fdd660fff0d74afb1aa6e9d5673ecc6adb65c39bd`.
- **Repository:** 25 records added to `unity-resolute`: the source, the 17
  binary packages of +unity2 at +unity3, and 7 debug-symbol packages
  (`-dbgsym`) published for compiz for the first time. The sha256 of every
  pool file matches the build manifest.
- **Snapshot:** `unity-resolute-20261013-003`, which is the live
  `unity-resolute-20261012-006` plus these 25 records
  (`gate/snapshot-diff.txt`).
- **Version safety:** SAFE (`gate/version-check.json`,
  `gate/version-safety.json`).
- **Peer notice:** agent B, ACK.
