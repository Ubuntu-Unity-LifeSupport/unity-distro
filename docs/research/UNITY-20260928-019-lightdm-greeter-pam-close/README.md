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
design_review_result: PENDING
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
chosen_approach: S1 (pending Design Challenger)
why_chosen: >-
  It fixes the handler's decision where the ambiguity is (child_pid == 0
  meaning two different things), keeps the pre-fork _exit of +unity1, leaves
  signal dispositions of anything exec'd during the cleanup at their
  defaults, and does not depend on how many stoppers there are.
defensive_workaround_rejected: >-
  D1 hides the symptom for one caller; S2/S3 leak the changed disposition or
  mask into PAM helpers.
hang_bound: >-
  With S1 a blocking cleanup is no longer escaped by the second SIGTERM.
  It is still bounded where the second SIGTERM exists: that case is the
  double stop, and the first one is logind's scope stop, which systemd
  finishes with SIGKILL after the scope's stop timeout (90 s default) - the
  same bound as today when both SIGTERMs are used before child_pid = 0
  (-004: 6/20). A session stopped only by the daemon's kill() gets one
  SIGTERM, passed on while the child lives, and behaves as today.
code_risks:
  ownership_lifetime: not_applicable - no object lifetime changes
  callbacks_cancellation: checked - the change makes the cleanup
    uncancellable by SIGTERM after reaping (hang_bound above); SIGKILL still ends it
  threading_reentrancy: checked - the flag is volatile sig_atomic_t, written once on the main thread before the cleanup, read in the handler on any thread
  ABI_API_file_list: not_applicable - static function and a static variable in one program
unknowns:
  - "Why stock cut 10/10 and +unity1 6/11 - timing of the session stack, not measured further."
  - "A greeter started for user switching reading the leftover :0 cookie is not exercised."
```
