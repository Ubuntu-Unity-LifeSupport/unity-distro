# UNITY-20260928-020: gtest-nux-slow segfaults in the package build

Owner: agent B (target2). nux's `make check-headless` (run by
`dh_auto_test`) segfaulted in most sbuilds on 2026-09-28. It hit
`gtest-nux-slow` (113 tests; the build log's fourth suite), in different
tests:

- `TestWindowThread.WatchFd`, `.MultiWatchFd`, `.OneFdEvent`;
- `EmbeddedContext.WindowThreadIsEmbedded` and other `EmbeddedContext*`.

It also hit the published, unchanged +unity2 (0 of 2 sbuilds clean), and it
blocked the clean build of UNITY-20260927-027. Retrying is not a fix.

**Outcome: two independent races, both in nux's test code. Two test-only
patches, and the suite is clean.**

1. **The dummy X server resets between tests.** A test that connects during
   a reset gets `XOpenDisplay() == NULL`. `EmbeddedContext` dereferences it.
2. **The `TestWindowThread` fixture deletes its watchdog thread while the
   thread is still running.** The thread then runs on freed memory.

```yaml
task_id: UNITY-20260928-020
package: nux
target_series: resolute
issue: local - gtest-nux-slow SIGSEGV in dh_auto_test (from UNITY-20260927-027)
status: REPRODUCED
issue_search_result: NOT_FOUND  # Launchpad nux: TestWindowThread, noreset, gtest-nux, dummy-xorg: 0; the two files unchanged upstream since 2015 / 2014
source_version: 4.0.8+18.10.20180623-0ubuntu15+unity2 (9793c23) for the reproduction; fix on top of 027's 35ecca4
source_commit: d50b77c, d869093 (+ changelog 0274bc5) in packages/nux, branch b/UNITY-20260927-027 (local)
observed: >
  FACT (logs/01): gtest-nux-slow of unchanged +unity2 built on target2
  (kernel 7.0.0-34, the same as builder) under the package's own
  dummy-xorg-test-runner.sh: SIGSEGV in 5 of 6 runs. On an own dummy Xorg
  without -noreset: 9 of 10. With -noreset: 4 of 10, all in
  TestWindowThread.
  FACT (logs/02): two crash sites.
  (1) EmbeddedContext's constructor, gtest-nux-windowthread.cpp:294:
      DefaultRootWindow() of a NULL display.
  (2) nux::SystemThread::Run, SystemThread.cpp:91, in the TestWindowThread
      watchdog thread, while the main thread is already in
      ~GraphicsDisplay (the fixture's members being destroyed).
expected: every run of gtest-nux-slow passes; the package builds without retries
reproduction: tests/loop.sh, tests/xrun.sh, tests/twt.sh (target2; the nux tree built there with dpkg-buildpackage, nocheck)
evidence: logs/01-04
root_cause: see "Mechanism"
root_cause_mechanism: >
  (1) Xorg without -noreset regenerates whenever its last client
  disconnects; the tests connect and disconnect test by test, so the server
  resets about once per test (88 and 114 GLX initialisations in two runs).
  An XOpenDisplay during the reset fails.
  (2) ~TestWindowThread deletes the nux::SystemThread watchdog. The
  watchdog's write to the quit pipe ends the test. SystemThread::Run then
  still reads parent_ and calls SetThreadState and TerminateChildThreads on
  the object. When the main thread wins, that object is already freed.
  NThread's destructor only detaches the thread.
invariant: >
  A test server connection is available for the whole suite; a fixture
  does not free an object that a thread it started is still using.
existing_fix_result: NOT_FIXED
candidate_approaches:
  - (A) retry the build - rejected (coordinator; it only hides both races)
  - (B) fix in nux's thread API (NThread) - rejected for this task: the race is the test's use; see "Layer"
  - (C) two test patches - chosen
chosen_approach: >
  tests-dummy-xorg-noreset.patch (Xorg -noreset in dummy-xorg-test-runner.sh)
  and tests-windowthread-join-watchdog.patch (std::thread watchdog, joined
  in ~TestWindowThread)
why_chosen: both races are in test code; the library is not in either crash path as a cause
design_challenger_required: false  # test-only, one line and one fixture member
design_review_result: NOT_REQUIRED
architectural_task: false
correct_layer: >
  The test harness and the test fixture. (1) is a property of how the test
  X server is started. (2) is the fixture's lifetime error. Nothing in nux's
  library code is changed; the shipped binaries are not affected.
defensive_workaround_rejected: >
  A NULL check in EmbeddedContext alone would turn (1) into test failures
  instead of crashes, not remove the reset. Retrying hides both.
code_risks:
  ownership_lifetime: checked  # the watchdog is joined before the pipes and the window thread go
  callbacks_cancellation: not_applicable
  threading_reentrancy: checked  # the joined thread only sleeps and writes to a pipe
  ABI_API_file_list: not_applicable  # tests only; nothing installed changes
unknowns:
  - why the races became frequent after 2026-09-24 is INFERENCE: the build
    chroot's 446 package versions are identical between the passing
    2026-09-24 build and the failing ones (logs/04); the builder's kernel
    changed from 7.0.0-31 to 7.0.0-34, which may change thread and wakeup
    timing. Not measured on the old kernel.
  - nux's NThread cannot be joined and then deleted (its destructor detaches
    unconditionally). A latent API defect; no caller of ours is known to
    need it. Not changed here.
  - unity's tests/dummy-xorg-test-runner.sh starts Xorg the same way,
    without -noreset (unity's tests are off in its package build).
```

## Mechanism

### 1. The server reset

`tests/dummy-xorg-test-runner.sh` starts
`Xorg $DISPLAY -config … -logfile …` without `-noreset`. An X server without
`-noreset` goes through a new server generation whenever the last client
closes its connection. The nux suites create and destroy their windows and
displays test by test. The Xorg logs show a regeneration nearly every
test: "Initializing extension GLX" appears 88 times in a failing run and
114 in a passing one.

A test that calls `XOpenDisplay()` while the server is regenerating gets
NULL. `EmbeddedContext`'s constructor passes that straight to
`DefaultRootWindow()` (core 1). Without `-noreset`, `TestWindowThread` tests
crashed too (run 6 in logs/01 §2); a core of that case was not taken, so
which of the two races hit them there is not known.

With `-noreset` there is one server generation per run, and no
`EmbeddedContext` crash in 10 runs (logs/01 §3).

### 2. The watchdog thread

`TestWindowThread::QuitAfter()` starts a `nux::SystemThread` that sleeps and
then writes to `quit_pipe_`. The window thread's main loop sees the pipe,
exits and signals `test_quit_pipe_`. `WaitForQuit()` returns, the test body
ends, and `~TestWindowThread` runs `delete quit_thread`.

The watchdog's `QuitTask` has returned from `write()` by then, but not from
`SystemThread::Run()`. Run then reads `parent_` and calls
`SetThreadState()` and `TerminateChildThreads()` on `this` (SystemThread.cpp
lines 81-91). When the main thread runs first, that memory is freed. Core 2
catches it exactly: the watchdog is at SystemThread.cpp:91, and the main
thread is in `~GraphicsDisplay`, destroying the fixture's members after the
destructor body.

Joining the thread before `delete` is not possible with nux's API as it is:
`NThread::~NThread` calls `pthread_detach` unconditionally, which is
undefined for a joined thread. The watchdog is test code, so the fix uses
`std::thread` and joins it.

## Fix

Two quilt patches, test-only, in the nux branch of UNITY-20260927-027:

- `tests-dummy-xorg-noreset.patch`: `-noreset` on the runner's Xorg line.
- `tests-windowthread-join-watchdog.patch`: the watchdog becomes a
  `std::thread`, joined in the destructor before the pipes close and the
  window thread is destroyed.

Measured on target2 (logs/03):

| | before | after |
|---|---|---|
| `TestWindowThread.*`, Xorg `-noreset` | 5 of 20 runs SIGSEGV | 0 of 30 |
| full `gtest-nux-slow`, the runner | 5 of 6 SIGSEGV | 0 of 20, 113/113 each |

## Layer

Both causes are in how the tests use the X server and a thread, not in
what nux ships. `Nux/SystemThread.cpp` and `NuxCore/ThreadGNU.cpp` have a
real ownership weakness: detach in the destructor, no safe join-and-delete.
A search of unity and nux for `CreateSystemThread` outside the tests finds
one caller: unity's `hud/StandaloneHud.cpp`, a standalone developer
prototype, not part of the session. It has the same pattern (`delete st`
right after `wt->Run()`). Changing the thread API would be an architectural
change in a shared library, and nothing in the session needs it. It is
recorded as an unknown, not made.

## Result

- **Package:** `packages/nux`, local branch `b/UNITY-20260927-027`:
  - d50b77c `tests-dummy-xorg-noreset.patch`;
  - d869093 `tests-windowthread-join-watchdog.patch`;
  - 0274bc5 changelog.

  These are on top of 027's 35ecca4 and ship in the same unreleased
  `0ubuntu15+unity3`.
- **sbuild of 0274bc5, three times in a row:** all successful, suites 130 /
  11 / 18 / 113 pass (logs/05, `build/` manifest of the third build). Before
  the fix: 1 clean build in 5 for 027, 0 in 2 for the published +unity2.
- The exported symbols of libnux, libnux-core and libnux-graphics equal
  +unity2's; only tests change.
- UNITY-20260927-027 can now take its clean build to the Verifier.

target2 is rolled back to `Clean-2` afterwards.
