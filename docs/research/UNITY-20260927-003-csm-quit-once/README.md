# UNITY-20260927-003: cinnamon-session +unity3, "request the reboot or shutdown once"

cinnamon-session `6.4.2-1+unity3` carries the backport of upstream #214
(9409c18, our 62ca2b4: wait for logind's PrepareForShutdown before quitting)
and our patch `Request-the-reboot-or-shutdown-only-once.patch` (a3d4c79): a
`quit_requested` flag that makes `csm_manager_quit()` return early after the
first call. Question from the coordinator: is the repeated `end_phase()` /
`csm_manager_quit()` entry upstream's normal behaviour that the flag only
hides, or does `csm_manager_quit()` rightly own "one request to logind"?
Agent A, target `target-desktop`, 2026-09-28.

## Before and after, live (2026-09-28, delay inhibitor held, InhibitDelayMaxSec=60)

`tools/cs-delay.sh reboot|poweroff` run as root through `systemd-run`: another
process holds a logind `shutdown` delay inhibitor, then Unity's end-session
dialog is used to reboot or power off; a tick is logged every second.
Runs 05-07 also record logind's bus traffic (`busctl monitor`).
`tools/cs-extract.sh` reads the previous boot. "Before" is a test build
without the flag, `6.4.2-1+unity3~noonce1` (NOT FOR PUBLICATION; only
`debian/patches/series` and the changelog differ from +unity3,
`tools/noonce-test-build.diff`; source commit 324d13d9ab7d, local clone only;
built with `scripts/build_sbuild.py`, sbuild exit 0). "After" is the
published `6.4.2-1+unity3` from our aptly (fadd8c6). The running binary was
checked against the installed one before the +unity3 runs 06-07 (md5
`1c6af850...`).

| Run | Build | Action | Requests logged | logind calls: accepted / refused | Session manager gone | Machine down |
|---|---|---|---|---|---|---|
| `runs/01-unity3-reboot.txt` | +unity3 | reboot | 1 | not recorded | < 1.4 s | +60 s |
| `runs/02-unity3-poweroff.txt` | +unity3 | poweroff | 1 | not recorded | < 0.5 s | +60 s |
| `runs/06-unity3-reboot-busmon.txt` | +unity3 | reboot | 1 | 1 / 0 | < 0.5 s | +60 s |
| `runs/07-unity3-poweroff-busmon.txt` | +unity3 | poweroff | 1 | 1 / 0 | < 0.5 s | +60 s |
| `runs/03-noonce-reboot.txt` | ~noonce1 | reboot | 4 in 120 ms | not recorded | < 0.6 s | +60 s |
| `runs/04-noonce-poweroff.txt` | ~noonce1 | poweroff | 8 in 125 ms | 1 / 7 (7x ENXIO) | < 0.5 s | +60 s |
| `runs/05-noonce-reboot-busmon.txt` | ~noonce1 | reboot | 8 in 230 ms | 1 / 7 (1x OperationInProgress, 6x ENXIO) | < 0.5 s | +60 s |

Run 02's boot also holds a first attempt that called `Shutdown()` without
clicking the dialog (the script had no click yet); nothing was requested, and
it was cancelled with Escape before the recorded run.

What the measurement shows:

- FACT: without the flag, every Reboot/PowerOff after the first is refused by
  logind; with it there is exactly one call and it is accepted.
- FACT: user-visible behaviour is the same in all seven runs: the session
  manager is gone within 1.5 s, and logind reboots or powers off when the
  delay inhibitor's 60 s run out.
- FACT: in every recorded run logind emitted PrepareForShutdown before its
  reply to the first call (signal cookie N, method return N+1), and every
  refusal arrived 30-115 ms after PrepareForShutdown. The session manager
  quits its main loop on that signal, so it never processed a refusal:
  neither "Unable to shutdown/restart system via systemd" nor "Shutdown/restart
  was not confirmed by logind" was logged in any run.

## Evidence card

```yaml
task_id: UNITY-20260927-003
package: cinnamon-session
target_series: resolute
issue: >-
  layer of our "request the reboot or shutdown once" patch (a3d4c79) on top of
  the #214 backport (9409c18 / 62ca2b4)
status: REPRODUCED   # the repeated requests, without the flag; table above
issue_search_result: NOT_FOUND
source_version: 6.4.2-1+unity3 (published); test build 6.4.2-1+unity3~noonce1 (not for publication)
binary_version: 6.4.2-1+unity3 on target (restored after the runs)
source_commit: >-
  Ubuntu-Unity-LifeSupport/cinnamon-session unity/resolute
  fadd8c6e97a43bb2d0e205da2fb8389b0c3a8ee3 (patch-queue a3d4c79ed27a,
  backport 62ca2b4c8e05); test build 324d13d9ab7d (local)
observed: >-
  Without the flag the session manager sends 4-8 Reboot/PowerOff calls in
  120-230 ms and logind refuses all but the first (OperationInProgress,
  ENXIO); with it, one call. No user-visible difference.
expected: one Reboot/PowerOff request per end of session
reproduction: tools/cs-delay.sh reboot|poweroff, then tools/cs-extract.sh after the next boot
evidence: runs/01-07 (above); journal boots on target 2026-09-28 13:05-13:44 UTC
root_cause_mechanism: >-
  FACT (code, 62ca2b4 = upstream master 06c8582 in this path): end_phase() in
  the EXIT phase does not advance the phase and calls csm_manager_quit().
  end_phase() is entered in EXIT once from do_phase_exit() and again from
  on_client_disconnected() / remove_clients_for_connection() every time the
  client store is empty while phase >= QUERY_END_SESSION - a state test, so it
  fires for each late disconnect. Before 9409c18, csm_manager_quit() asked
  logind and then quit the main loop at once (6.6.4, per the sweep), so the
  process ended before late disconnects could re-enter.
  9409c18 keeps the process alive until PrepareForShutdown, and every
  re-entry in that window repeats the logind call: it connects another
  "shutdown-prepared" handler, sets prepare_for_shutdown_expected again and
  sends another Reboot/PowerOff (csm-systemd.c).
invariant: >-
  one Reboot/PowerOff request to logind per end of session; actions of the
  EXIT phase must be safe to repeat, because end_phase() is re-entered in EXIT
  by design
existing_fix_result: FIXED_LOCAL   # our a3d4c79 in +unity3; no upstream fix (below)
existing_fix_evidence: >-
  Subagent sweep 2026-09-28T13:08Z: linuxmint/cinnamon-session master 06c8582
  (= 6.7.5-unstable) has 9409c18 and no guard; the only later commit in the
  path, 51cb449, touches csm-consolekit.c / csm-system.[ch] only; issues and
  PRs (#214, #216, #217, #215, #219) have nothing on repeated requests.
  gnome-session master d3c610c1 and mate-session-manager v1.28.0 have the
  same re-entry and no flag (below). GNOME GitLab issue search returned
  nothing unauthenticated - low confidence for that tracker.
upstream_precedent: >-
  gnome-session has the same state test in on_client_disconnected() /
  remove_clients_for_connection() and the same non-advancing EXIT branch, and
  no flag. It is safe there because since 1c84d283 / 8b187ec5 (2012) the
  logind request is made once, at the end of QUERY_END_SESSION
  (gsm_systemd_prepare_shutdown()), and the EXIT phase only calls
  gsm_system_complete_shutdown() (drops a delay inhibitor, guarded by fd != -1)
  and gsm_quit() - both idempotent. 9409c18 took gnome-session's
  prepare/complete idea but left the request in the EXIT phase, where
  gnome-session removed it in 8b187ec5. mate-session-manager keeps the request
  in EXIT but quits the main loop synchronously after the first one.
candidate_approaches:
  - "F1 (published, a3d4c79): csm_manager_quit() returns early after its first
    call (quit_requested flag). 6 lines, one function."
  - "F2: the same flag in end_phase()'s EXIT case."
  - "F3: callers call end_phase() only on the transition to an empty store."
  - "F4: gnome-session's structure - request the reboot/shutdown once when
    QUERY_END_SESSION ends, only complete it in EXIT."
chosen_approach: keep F1 as published
correct_layer: >-
  The re-entry itself is upstream's design, shared with gnome-session, and not
  a defect to remove: the last-client check is a state test and EXIT never
  advances. What is not safe to repeat is the terminal action 9409c18 put in
  EXIT - the logind request in csm_manager_quit(). Making that action
  idempotent at the function that performs it is exactly the property that
  makes the same re-entry harmless in gnome-session (its EXIT actions are
  idempotent). csm_manager_quit() is the owner of "one request to logind"; its
  only caller is end_phase()'s EXIT case (csm-manager.c:567 before the
  patches are applied).
defensive_workaround_rejected:
  - "F2: equivalent today (single caller) but puts a fact about the terminal
    action into the phase machine; a future second caller of
    csm_manager_quit() would bypass it."
  - "F3: does not establish the invariant - do_phase_exit() and the
    last-client test still both enter end_phase() in EXIT (at least two
    entries), and upstream gnome-session keeps the same state test."
  - "F4: the structural answer upstream gnome-session chose, but a redesign
    of the end-session path (request earlier, cancellation between
    QUERY_END_SESSION and EXIT, polkit prompts) diverging from 9409c18, which
    upstream Cinnamon ships; no measured benefit over F1 (table: identical
    user-visible behaviour). Belongs upstream if anywhere."
why_chosen: >-
  Measured: F1 reduces 4-8 logind calls with 3-7 refusals to one accepted
  call, with the same user-visible timing. It restores the invariant in the
  function that owns it, at a size that is cheap to carry until upstream
  addresses it.
not_justified: >-
  The published patch description and the 2026-09 record present the
  repeated requests as a behaviour problem. Measured: they are not visible to
  the user. The premature quit a refusal would cause (a refusal ->
  shutdown-prepared(FALSE) -> "not confirmed by logind" -> csm_quit() before
  PrepareForShutdown) did not happen in any run, because logind handles the
  calls in order, emits PrepareForShutdown before replying to the first, and
  the session manager quits on that signal (INFERENCE from the bus order
  above: it is unreachable while the first call succeeds). The patch is
  protocol hygiene - one request, one handler, no refusals - not a fix for a
  visible failure.
code_risks:
  ownership_lifetime: checked - flag lives in CsmManagerPrivate, set once, never reset; the manager does not outlive the process
  callbacks_cancellation: >-
    checked - with the flag only one "shutdown-prepared" handler is connected;
    no cancellation path exists after the EXIT phase starts
  threading_reentrancy: checked - main-loop only; the re-entry is the case the flag handles
  ABI_API_file_list: not_applicable - static private field, no API change
unknowns:
  - "Why logind answers the later repeats with ENXIO rather than
    OperationInProgress was not investigated (session already closing is the
    likely reason - HYPOTHESIS)."
  - "The quit timing is 'gone before the next 1 s tick'; finer timing was not
    measured."
  - "GNOME GitLab issues could not be searched with authentication."
design_challenger_required: true
architectural_task: false
design_review_result: PENDING
```

## Outcome

PENDING the Design Challenger.
