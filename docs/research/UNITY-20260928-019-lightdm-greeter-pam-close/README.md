# UNITY-20260928-019: the greeter's session cleanup is cut short by the second SIGTERM

Follow-up of UNITY-20260927-004 (`../UNITY-20260927-004-lightdm-sigterm-reach/`),
which found that the greeter's `pam_close_session` is not run in about half
of the logins from the greeter, in stock and in `+unity1`. This record answers:
how often on a clean snapshot, which path skips it and why, what that leaves
behind, and which layer owns the fix. Agent A, target `target-desktop`,
2026-09-29.

Target: snapshot `Clean-updated-2026-09-23` restored and confirmed from the
guest (fresh boot, no `~/.dirty`). Stock run: archive only, lightdm
`1.32.0-6ubuntu4`, the stock Unity session. Our run: aptly added,
`full-upgrade` to our stack, lightdm `1.32.0-6ubuntu4+unity1`, session by
cinnamon-session. Greeter `lightdm-gtk-greeter 2.0.9-0ubuntu3.1` in both;
systemd `259.5-0ubuntu3.4`, libpam `1.7.0-5ubuntu3.2`, glibc `2.43-2ubuntu2.4`.
Temporary user `utest` with a password (deleted afterwards).

## 1. Path

`tools/greeter-close-trace.bt` (bpftrace, whole machine) prints one
`SUMMARY` line per greeter session-child: SIGTERM deliveries, whether the
handler passed them on, the reaping of the greeter, and whether
`pam_close_session` (entry and return), `pam_setcred` and `pam_end` ran
after it. `tools/greeter-cycles.sh` logs `utest` out and in again through the
greeter and takes a state snapshot 20-35 s after each login.

FACT (code, `src/session-child.c`, 1.32.0, unchanged at upstream master
29b06b457b03): after `waitpid()` returns, `child_pid = 0`; the rest of `main()`
is the cleanup - X authority removal (`x_authority_write(...REMOVE...)`),
`pam_close_session`, `pam_setcred(PAM_DELETE_CRED)`, `pam_end`. For a greeter
there is no utmp/wtmp or audit record (skipped by the `XDG_SESSION_CLASS`
check). `signal_cb()` passes SIGTERM on while `child_pid > 0` and otherwise
leaves the process at once (`exit()` in stock, `_exit()` in `+unity1`).

FACT (runs): the greeter is stopped with two SIGTERMs - systemd (logind
`TerminateSession` -> scope stop) and then the lightdm daemon's own `kill()`
(`session_real_stop()`, `session.c:955-968`), 2-19 ms later. The first always
arrived while the greeter was alive and was passed on. When the second is
delivered after `child_pid = 0`, the handler ends the process in the middle of
the cleanup. The cleanup takes about as long as the gap:
`pam_close_session` alone 1.9-6.0 ms (5 measured, pam_systemd's
`ReleaseSession` over Varlink).

| Run | Build | Greeter stops | cleanup complete | cut in stage 1 (before `pam_close_session`) | cut in `pam_close_session` | cut in `pam_end` |
|---|---|---|---|---|---|---|
| `runs/00`, `runs/01` | stock | 10 | 0 | 8 | 2 | 0 |
| `runs/02` | +unity1 | 11 | 4 | 5 | 1 | 1 |

"Complete" = `pam_close_session` and `pam_end` both returned. In +unity1,
`8801` returned from `pam_close_session` and was cut inside `pam_end` (the
close ran); counting "greeter PAM session closed": stock 0/10, +unity1 5/11.
In one +unity1 stop (`32964`) the second SIGTERM landed between `waitpid()`
and `child_pid = 0` and was passed on to the reaped PID, as noted in -004; the
cleanup then ran. In one (`4546`) only systemd's SIGTERM reached the
process. The stock/ours difference (0/10 vs 5/11) is in timing, not in the
patch: `+unity1` changes only what the handler does *after* it decided to
leave. INFERENCE: different session stacks (GNOME vs cinnamon-session
logout) and load; -004 had 14/20 no-child in both builds. Three cycles in
`runs/01` and several in `runs/02`/`runs/04` did not log out (the session
manager ignored the Logout call, the script waited 60 s); those cycles have
no greeter stop and are not counted.

## 2. What the skipped cleanup leaves behind

Per module, from source (Investigator subagent, systemd v259/v259.5,
linux-pam 1.7.0, lightdm 1.32.0; FACT unless marked):

- pam_systemd close: only `ReleaseSession` (v258+ has no session FIFO).
  logind returns early for a session already stopping - and lightdm called
  `TerminateSession` before either SIGTERM - so it is a no-op here; the leader
  pidfd's death drives the same stop and garbage collection.
- pam_unix close: the "session closed for user lightdm" line only. pam_env,
  pam_umask, pam_permit: nothing. The greeter's auth stack is pam_permit, so
  `pam_setcred(DELETE)` does nothing. libpam writes `AUDIT_USER_END` /
  `AUDIT_CRED_DISP` on close and setcred (no auditd on target).
- `pam_end`: module data cleanups only.
- X authority: the greeter gets the X server's cookie in
  `/var/lib/lightdm/.Xauthority`; the same X server and cookie serve the
  user's session that follows.

Measured (state snapshots, `runs/01-*-state.txt`, `runs/02-*-state.txt`):

- logind/systemd: after every stop, skipped or not, the greeter session and
  scope were gone, `user@109` inactive, no `/run/user/109`, no uid-109 process
  - no lasting difference.
- **The greeter's cookie stays behind and opens the user's display.** When
  the second SIGTERM lands before the X authority removal has finished, the
  cookie stays in `/var/lib/lightdm/.Xauthority`, and a process running as uid
  `lightdm` (no groups) with that file connects to `:0` - the X server now
  running `utest`'s session (`xdpyinfo` succeeds; with the cookie removed:
  "Authorization required"). +unity1: 1 of the 6 cut stops left the cookie
  (`24191` -> snapshot of cycle 6), 0 of the 5 complete ones; stock `runs/01`
  cycle 3 shows the entry too (check added later). The cookie is valid until
  the user's X server exits. uid `lightdm` runs the next greeter - e.g. one
  started by user switching or `dm-tool switch-to-greeter` while this session
  runs - which can then read it (INFERENCE: not exercised).
- Missing log line "session closed for user lightdm" and, with auditd, an
  unmatched `USER_START`. lightdm.log records return value 0 instead of the
  greeter's status (log only; the daemon ignores it).
- The next login is not delayed: the user session was on seat0 within 0-1 s
  of the greeter's stop in every cycle.

User sessions (`runs/03`, `tools/restart-cycles.sh`): six `systemctl restart
lightdm` with a user session running - the session-child finished every time
(one "session closed" line from its stack, a `DEAD_PROCESS` wtmp record for
`:0`, lightdm.log "Exited with return value 1"). A user session's
session-child is not signalled at logout (-004). So only the greeter, which is
stopped twice, is affected in the measured paths. resolute has no utmp file
at all (`/var/run/utmp` absent; lightdm logs "Failed to write utmpx"); wtmp is
written.

## 3. Deterministic reproduction

`tools/force-late-sigterm.bt` (bpftrace `--unsafe`) sends one SIGTERM to the
greeter's session-child at its first `pam_getenv()` after `waitpid()` - the
`XDG_SESSION_CLASS` check right after `child_pid = 0`, i.e. where the daemon's
SIGTERM lands in stage 1. `runs/04` (+unity1): 2 of 2 forced stops cut in
stage 1 with `_exit()`, no `pam_close_session`, the cookie left behind and
`xdpyinfo` as uid lightdm on `:0` succeeding.

## 4. Fix and verification (+unity2)

lightdm `1.32.0-6ubuntu4+unity2` = `d/p/0010-session-child-finish-the-cleanup-when-SIGTERM-arrive.patch`
(Ubuntu-Unity-LifeSupport/lightdm `a/UNITY-20260928-019`: patch `db13faf`,
changelog `f5af23c`, on `unity/resolute` `50a6a5d`). Clean `sbuild` for
resolute via `scripts/build_sbuild.py`, exit 0; build manifest
`build-unity2/UNITY-20260928-019-lightdm-build-manifest.json` (sbuild log `build-unity2/sbuild.log.xz`). The
only compiler warnings in session-child.c are the four existing `-Waddress`
ones in `updwtmpx()`. File lists of `lightdm` and `liblightdm-gobject-1-0`
identical to +unity1 (Verifier: all seven binary packages). Installed on target (lightdm + liblightdm-gobject only,
from the build, not aptly), rebooted; `runs/05` (first pass), `runs/06`
(second pass: T3-T6 again, T5), `runs/07` (third pass after Verifier round 1:
T1b, T5b, T7), `runs/08` (T6c).

| Test | What | +unity1 | +unity2 |
|---|---|---|---|
| T2 regression | SIGTERM forced at the first `pam_getenv` after `waitpid` | 2/2 cut, cookie left, `:0` opens as uid lightdm (`runs/04`) | 4/4 complete, no cookie (`runs/05`) |
| T1 | natural greeter stops | 6/11 cut (`runs/02`) | 13/13 complete (7 in `runs/05`, 6 in `runs/07`; plus 40731 at the start of T3), no cookie after any real login |
| T3 | SIGTERM forced at the entry of pam_systemd's `pam_sm_close_session` (before any blocking call in it - not an EINTR test) | - | 5/5 complete, close returns 0 (`runs/05`, `runs/06`) |
| T4 | SIGTERM forced at `pam_end` | - | 5/5 complete (`runs/05`, `runs/06`) |
| T5 | SIGTERM before the greeter exists, at `fork()` of a `lightdm-greeter` session-child (handler installed, `child_pid` 0) | - | delivered to the caught handler, `_exit(0)` 0.6 ms later, no greeter; lightdm fell back to the autologin session (`runs/07`). A first version (`runs/06`) signalled at `pam_open_session`, before `signal()` installs the handler - the default action killed the process; it tests nothing of the handler (Verifier round 1) |
| T6 | greeter close blocked 60 s (temporary pam_exec hook) + forced late SIGTERM | - | 4/4: session-child ends 10.00-10.05 s after the first post-reap SIGTERM, lightdm.log "Sending SIGTERM" +115.49 s, "Terminated with signal 14" +125.49 s (`runs/08`; `runs/06` 3 more, their log overwritten by T7), cookie already removed, user session starts then |
| T7 | user sessions stopped by the daemon (`systemctl restart lightdm`, runs/03 again) | 6/6 complete (`runs/03`) | 6/6 complete: "session closed" line and wtmp `DEAD_PROCESS` for `:0` each time (`runs/07`) |

"Complete" = `pam_close_session`, `pam_setcred` and `pam_end` returned and
`main()` returned. Login delay unchanged: the user session was on seat0 within
0-1 s of the greeter's stop in T1-T4. Reaping to exit now takes 9-135 ms (one
618 ms) under the trace, the time of the cleanup that used to be cut; the
daemon waits for it before starting the user session. T6's orphaned `sleep`
kept the greeter's scope (logind session "closing") until it ended by itself;
it did not delay the user session - the daemon waits only for session-child.

Not a lightdm effect, recorded for the test runs: cinnamon-session refused
`Logout` (`NotInRunning`) or hung in it on an unresponsive at-spi-registryd
inhibitor in several cycles; those cycles have no greeter stop (and the
snapshots taken with the greeter still up show its own live cookie - not
counted). `greeter-cycles.sh` now falls back to `loginctl terminate-session`
after 20 s.

## Evidence card

```yaml
task_id: UNITY-20260928-019
package: lightdm
target_series: resolute
issue: local (follow-up of UNITY-20260927-004) - the greeter session-child's cleanup (X authority removal, pam_close_session, pam_setcred, pam_end) is cut short by the daemon's SIGTERM
status: REPRODUCED
issue_search_result: NOT_FOUND
source_version: 1.32.0-6ubuntu4+unity1 (ours, published); 1.32.0-6ubuntu4 (stock) for the before runs
binary_version: 1.32.0-6ubuntu4+unity1 on target during runs/02-04
source_commit: Ubuntu-Unity-LifeSupport/lightdm unity/resolute 50a6a5dd8974a95db064f4a19dabe22becc329c0
observed: >-
  In 16 of 21 traced greeter stops (stock 10/10, +unity1 6/11) the second
  SIGTERM - the daemon's kill() after logind's scope stop - is delivered
  after waitpid() has set child_pid = 0, and signal_cb() ends the process in
  the middle of the cleanup: before pam_close_session (13), inside it (3);
  one more inside pam_end. When it lands before the X authority removal is
  done, the greeter's cookie stays in /var/lib/lightdm/.Xauthority and
  opens the user's X display as uid lightdm (1 of 6 cut +unity1 stops,
  2 of 2 forced).
expected: >-
  once the greeter has exited, session-child finishes its cleanup - removes
  the greeter's X authority, closes the PAM session, ends PAM - whatever
  further SIGTERMs arrive
reproduction: >-
  natural: tools/greeter-cycles.sh under tools/greeter-close-trace.bt;
  deterministic: add tools/force-late-sigterm.bt (bpftrace --unsafe)
evidence: runs/00-04; target journal 2026-09-29 08:00-08:52 UTC
root_cause: >-
  signal_cb() treats a SIGTERM that arrives after the session process was
  reaped like one that arrives before the session started: "no child, just
  quit". lightdm stops a greeter twice (logind TerminateSession -> scope stop,
  then kill()), so the second SIGTERM regularly arrives during the cleanup
  and aborts it.
root_cause_mechanism: >-
  FACT (code): child_pid is 0 before fork() and again after waitpid(); the
  handler cannot tell the two apart. FACT (runs): first SIGTERM from systemd,
  passed on to the live greeter; greeter reaped; second SIGTERM from the
  daemon 2-19 ms after the first, while the 2-6 ms pam_close_session and the
  X authority write run; handler -> exit()/_exit().
root_cause_evidence: runs/01, runs/02 (SUMMARY lines), runs/04 (forced), code at src/session-child.c signal_cb() and main() after waitpid()
invariant: >-
  after the session process has been reaped, session-child runs its whole
  cleanup exactly once; a SIGTERM before the session process exists still
  ends session-child at once (the -004 / LP #2168421 behaviour, _exit)
existing_fix_result: NOT_FIXED
existing_fix_evidence: >-
  Investigator subagent 2026-09-29: canonical/lightdm (ubuntu/lightdm)
  master 29b06b457b03, tags 1.33.0/1.33.1 - signal_cb unchanged, no commit
  touches it; issues/PRs searched for pam_close_session, signal_cb, SIGTERM,
  session-child, "session closed", TerminateSession, _exit,
  session_real_stop: only #484 (exit() deadlock; our +unity1) and #45
  (sessions stuck closing, unrelated); PR #414 is pam_end in the forked
  child for pam_cap, unrelated. Launchpad lightdm and ubuntu/+source/lightdm:
  nothing on a skipped greeter close (LP #1441356 and #1172752 related, not
  this). Ubuntu devel still 1.32.0-6ubuntu4; Debian sid 1.33.1-3 with no
  signal changes (BTS titles only).
design_challenger_required: true
architectural_task: false
design_review_result: APPROVE   # review 1: REVISE (hang bound, watchdog, store order, EINTR/fork notes, tests), review 2: APPROVE
correct_layer: >-
  session-child owns its cleanup and its SIGTERM handler; the handler is
  where "stop the session" is turned into an action, so it is where a
  SIGTERM after the session ended must mean "finish". Two independent
  stoppers (logind for the scope, the daemon for its own process) are
  legitimate and can each signal; session-child must be correct under
  both, not rely on one of them being removed.
candidate_approaches:
  - "S1: a volatile sig_atomic_t flag set right after waitpid() returns;
    signal_cb() returns without action when it is set. Before fork and in
    the forked child it still _exit()s. Four lines."
  - "S2: signal(SIGTERM, SIG_IGN) right after waitpid(). Same effect, one
    line, but an ignored disposition survives execve(): any helper a PAM
    module spawns during pam_close_session would ignore SIGTERM too."
  - "S3: block SIGTERM with sigprocmask() after waitpid(). Same effect;
    the signal mask also survives execve() into PAM helpers."
  - "D1: in the daemon, skip session_real_stop()'s kill() when
    TerminateSession succeeded (the scope stop already signals everything).
    Removes the second SIGTERM for this path only; any other second SIGTERM
    still aborts the cleanup, and it changes daemon behaviour for every
    session type."
  - "F2 from -004: self-pipe / signalfd - rejected there (no main loop while
    PAM runs)."
chosen_approach: >-
  S1 + watchdog (revised after Design Challenger review 1): session_ended
  (volatile sig_atomic_t) set right after waitpid() and before child_pid = 0;
  child_pid made volatile so the two stores keep their order; signal_cb():
  if session_ended, arm alarm(10) on the first such signal and return;
  otherwise pass on / _exit() as in +unity1.
why_chosen: >-
  It fixes the handler's decision where the ambiguity is (child_pid == 0
  meaning two different things), keeps the pre-fork _exit of +unity1, and
  does not depend on how many stoppers there are. The alarm keeps the other
  half of what the handler is for - a stop request ends session-child in
  bounded time - so a cleanup that blocks cannot hold the next session for
  systemd's 90 s. Precedent: gdm-session-worker _exit()s from a raw handler
  only before the session starts and turns SIGTERM into an orderly shutdown
  that runs pam_close_session afterwards (session-worker-main.c,
  gdm-session-worker.c uninitialize_pam).
defensive_workaround_rejected: >-
  D1 removes the measured trigger for one caller and changes the daemon for
  every session type; the handler's ambiguity stays. S2/S3 have no place to
  arm a watchdog and change the stop signal of anything exec'd during the
  cleanup (SIG_IGN and the mask survive execve, a caught handler resets to
  SIG_DFL) - a minor point, since session-child already runs PAM with SIGHUP
  and SIGPIPE ignored, inherited from the daemon (lightdm.c:545-558; SigIgn
  0x1001 measured on a greeter session-child).
f3_relation: >-
  S1 alone is -004's rejected F3 ("ignore SIGTERM once the child is reaped"),
  and -004's objection holds for it: the daemon waits for session-child
  before starting the user session (session_watch_cb -> STOPPED ->
  seat.c session_stopped_cb) and has no timeout of its own
  (session_real_stop "FIXME: Handle timeout"). The watchdog is what answers it.
hang_bound: >-
  Without the watchdog, S1 would widen the exposure: a blocking cleanup would
  hold the next session in every double stop, not only in the 6/20 where
  both SIGTERMs are used up before child_pid = 0; bounded only by the scope's
  stop timeout - measured on target: session-cN.scope TimeoutStopUSec=1min
  30s (DefaultTimeoutStopUSec, logind sets none on the scope), KillMode
  control-group, FinalKillSignal 9, SendSIGHUP yes. And one path would be
  unbounded: a single late SIGTERM with no logind scope stop behind it (no
  login1 session, e.g. pam_systemd failed to register) - today it _exit()s,
  S1 alone would never end. With the watchdog: the first SIGTERM after
  reaping arms alarm(10); SIGALRM is SIG_DFL in session-child (not in SigIgn
  or SigCgt on target), so the process ends 10 s later at the latest; no
  path waits longer than today's worst case, the double stop waits at most
  10 s instead of 90 s when the cleanup blocks. The measured cleanup takes
  2-6 ms (pam_close_session), so 10 s is three orders of magnitude of
  headroom; pam_systemd's own ReleaseSession call is bounded by sd-varlink's
  45 s default and handles EINTR. The alarm is not inherited across fork()
  by a PAM helper. A PAM module that uses alarm()/SIGALRM itself during the
  close would replace the watchdog - accepted, noted. When logind itself is
  broken, pam_systemd's IPC limits (45 s Varlink, ~25 s D-Bus fallback) are
  longer than 10 s: the alarm then ends session-child and the rest of the
  cleanup is skipped - no worse than today. Unchanged by the fix: when both
  SIGTERMs are passed on before reaping (-004: 6/20), no alarm is armed and
  a blocking cleanup still waits for the scope's 90 s SIGKILL, as today
  (arming the alarm after waitpid() when a SIGTERM was passed on would
  close that too - a separate defect, proposed as a follow-up).
code_risks:
  ownership_lifetime: not_applicable - no object lifetime changes
  callbacks_cancellation: >-
    checked - after reaping, SIGTERM no longer cancels the cleanup; the
    alarm ends it after 10 s (hang_bound). A returning handler interrupts
    non-restartable calls (poll, ppoll, nanosleep, some socket calls with
    timeouts) inside PAM modules with EINTR; glibc signal() sets SA_RESTART,
    so read/write/fsync/waitpid restart. Before the change those calls were
    not interrupted but ended with the process, so an EINTR-handling bug in a
    module can at worst fail its close - still more than was done before.
    Not directly tested: T3 forces the signal at the entry of pam_systemd's close, before its Varlink wait; natural stops 15957, 24216, 12945 had the signal arrive during the close and it still returned 0 (incidental).
  threading_reentrancy: >-
    checked - session_ended and cleanup_alarm_set are volatile sig_atomic_t;
    child_pid is volatile so the compiler keeps "session_ended = 1" before
    "child_pid = 0" (both volatile accesses); the handler may run on any of
    session-child's threads, and alarm(), kill() and _exit() are
    async-signal-safe
  fork_inheritance: >-
    a helper a PAM module fork()s during the cleanup inherits the handler
    with session_ended set, so until it execs it ignores SIGTERM (arming its
    own alarm); before, it _exit()ed. After execve the disposition is SIG_DFL.
  ABI_API_file_list: not_applicable - static function and static variables in one program
remaining_windows: >-
  unchanged by the fix, recorded: between waitpid() returning and
  session_ended = 1 the handler kill()s the reaped PID (32964 in runs/02;
  harmful only on PID reuse); in the parent between fork() and the store to
  child_pid the handler _exit()s and orphans the new child; in the forked
  child before exec the flag is 0 and the handler _exit()s (correct); if
  fork() fails the flag is never set and a late SIGTERM still _exit()s (no
  session ran). volatile orders the two stores for the compiler; on a
  weakly ordered CPU (arm64) a handler on another thread could still see
  child_pid = 0 before session_ended = 1 for nanoseconds - moot on amd64,
  the only architecture we build; __atomic_store_n(SEQ_CST) if that changes.
  Two threads running the handler at once may both call alarm(10), which
  re-arms the same timer.
cookie_file: /var/lib/lightdm/.Xauthority -rw------- lightdm:lightdm in /var/lib/lightdm drwxr-x--- lightdm:lightdm
test_plan: >-
  On the fixed build, under greeter-close-trace.bt: T1 natural cycles (>= 10
  greeter stops): every cleanup complete, no leftover cookie, login delay
  unchanged. T2 forced SIGTERM at the first pam_getenv after waitpid (stage
  1): complete (red on +unity1: runs/04). T3 forced inside pam_systemd's
  pam_sm_close_session (at its entry): close completes. T4 forced inside
  pam_end: completes. T5 one SIGTERM into a greeter session-child at fork(), before its
  greeter is exec'd: still _exit()s at once. T6 a cleanup that blocks
  (temporary pam_exec close_session hook sleeping 60 s, greeter PAM service
  only): session-child ends by SIGALRM about 10 s after the second SIGTERM,
  and the user session follows. lightdm's in-tree suite
  (tests/src/libsystem.c fakes pam_close_session) could host a
  deterministic test; not used - debian/rules skips the suite and the knob
  would add test-harness code to the patch.
unknowns:
  - "Why stock cut 10/10 and +unity1 6/11 - timing of the session stack, not measured further."
  - "A greeter started for user switching reading the leftover :0 cookie is not exercised."
```

## Design review

Temporary Design Challenger, separate read-only subagent.

1. **REVISE**: S1 alone is -004's rejected F3 and `hang_bound` did not answer
   its objection (the daemon waits for session-child; one path - a single late
   SIGTERM without a logind scope stop - would be unbounded); add a watchdog or
   justify leaving it out; `child_pid` must be volatile with the flag written
   first; EINTR and fork-inheritance risks missing; tests only forced stage 1.
   Led to the `alarm()` watchdog, the measured scope timeout and signal masks,
   and tests T3-T6.
2. **APPROVE**: the card and the drafted 0010 match; 10 s defensible; in-tree
   suite not blocking. Remarks folded in: T6 runs with the forced late
   SIGTERM; the 6/20 passed-on path keeps today's 90 s bound (follow-up);
   arm64 store ordering noted.
