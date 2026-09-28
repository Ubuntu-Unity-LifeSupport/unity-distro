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

| Run | Build | Action | Requests logged | logind calls: accepted / refused | Session manager gone (first request -> first 1 s tick without it) | Machine down |
|---|---|---|---|---|---|---|
| `runs/01-unity3-reboot.txt` | +unity3 | reboot | 1 | not recorded | <= 1.44 s | +60 s |
| `runs/02-unity3-poweroff.txt` | +unity3 | poweroff | 1 | not recorded | <= 0.46 s | +60 s |
| `runs/06-unity3-reboot-busmon.txt` | +unity3 | reboot | 1 | 1 / 0 | <= 0.54 s | +60 s |
| `runs/07-unity3-poweroff-busmon.txt` | +unity3 | poweroff | 1 | 1 / 0 | <= 0.44 s | +60 s |
| `runs/03-noonce-reboot.txt` | ~noonce1 | reboot | 4 in 120 ms | not recorded | <= 0.56 s | +60 s |
| `runs/04-noonce-poweroff.txt` | ~noonce1 | poweroff | 8 in 125 ms | 1 / 7 (7x ENXIO) | <= 0.59 s | +60 s |
| `runs/05-noonce-reboot-busmon.txt` | ~noonce1 | reboot | 8 in 230 ms | 1 / 7 (1x OperationInProgress, 6x ENXIO) | <= 0.67 s | +60 s |

Run 02's boot also holds a first attempt that called `Shutdown()` without
clicking the dialog (the script had no click yet); nothing was requested, and
it was cancelled with Escape before the recorded run. Run 04 was recorded
with the bus monitor too (its file name lacks `-busmon`: the monitor was
added to the script just before it).

What the measurement shows:

- FACT: without the flag, every Reboot/PowerOff after the first is refused by
  logind; with it there is exactly one call and it is accepted.
- FACT: user-visible behaviour is the same in all seven runs: the session
  manager is gone within 1.5 s, and logind reboots or powers off when the
  delay inhibitor's 60 s run out.
- FACT: in the four bus-monitored runs (04-07) logind emitted
  PrepareForShutdown just before its reply to the first call (signal cookie
  N, method return N+1); in 04 and 05 the later calls reached logind before
  that (logind answered the first call after 63 and 160 ms, and the others
  after it), and every refusal arrived 30-115 ms after PrepareForShutdown.
  The session manager quits its main loop on that signal and never processed
  a refusal: neither "Unable to shutdown/restart system via systemd" nor "Shutdown/restart
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
  fires for each late disconnect. The Unity/Cinnamon end-session dialog's
  Restart, Shutdown, Logout and IgnoreInhibitors methods also reach
  end_phase() with no phase check (handle_dialog_method_call ->
  request_reboot/request_shutdown/request_logout/do_inhibit_dialog_action,
  csm-manager.c:2653-2705, 3745-3805, 1282 unpatched; upstream master the
  same), overwriting logout_type; RequestReboot/RequestShutdown do check
  the phase (:2312, :2336).
  This is old upstream behaviour, not something 9409c18 introduced: in
  unpatched 6.4.2 (and upstream 6.6.4 / 9409c18^) the REBOOT and SHUTDOWN
  cases of csm_manager_quit() only connect "request-failed" and call
  csm_system_attempt_restart/stop; csm_quit() is called only for LOGOUT and
  the *_MDM cases (csm-manager.c:471-513). The process stayed alive after the
  request and every late disconnect sent another one - measured on +unity2 as
  twelve requests in 120 ms with OperationInProgress refusals and the MDM
  fallback (research/cinnamon-session-214-202, runs/01). 9409c18 shortened
  the window (it quits on PrepareForShutdown) but kept the request in EXIT.
  Each re-entry connects another "shutdown-prepared" handler, sets
  prepare_for_shutdown_expected again and sends another Reboot/PowerOff
  (csm-systemd.c); the inhibitor take/drop are guarded by fd checks and
  g_signal_handlers_disconnect_by_func removes every duplicate handler, so
  the only effect is the extra logind calls.
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
  prepare/complete idea but kept cinnamon-session's request in the EXIT
  phase, where gnome-session removed it in 8b187ec5. mate-session-manager keeps the request
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
  advances. What is not safe to repeat is the terminal action cinnamon-session
  has always taken in EXIT (gnome-session moved it out in 8b187ec5) - the
  logind request in csm_manager_quit(). Making that action
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
  call, with the same user-visible timing. It establishes the invariant in
  the function that owns it, at a size that is cheap to carry until upstream
  addresses it.
not_justified: >-
  The published patch description says that with the PrepareForShutdown
  backport the refusals meant "quitting on a false 'not confirmed by
  logind'". Not observed: in the bus-monitored runs without the flag (04,
  05) and with it (06, 07) no refusal was processed and that line was never
  logged, because PrepareForShutdown arrived first and the session manager
  quit on it. Structurally this order is implied only for
  OperationInProgress (it can only follow the accepted call); ENXIO is
  unexplained, and the argument also relies on GDBus dispatching the signal
  before the later replies on the same main context - so it is "not
  observed", not "unreachable". The "twelve times in 120 ms" and
  OperationInProgress facts in that description were measured on +unity2,
  before the backport; +unity3~noonce1 made 4-8 calls, refused mostly with
  ENXIO. What the patch measurably buys: one request, one handler, no
  refusals - protocol hygiene, not a fix for a visible failure. Correct the
  patch description at the next upload made for another reason.
code_risks:
  ownership_lifetime: checked - flag lives in CsmManagerPrivate, set once, never reset; the manager does not outlive the process
  callbacks_cancellation: >-
    checked - with the flag only one "shutdown-prepared" handler is connected.
    cancel_end_session() accepts phase EXIT (csm-manager.c:1066-1096, reached
    by the dialog's Cancel while dialog_action is set) and resets the phase
    to RUNNING, but not quit_requested. INFERENCE: this cannot strand a
    later end of session, because the request was already sent: if logind
    accepts it, the machine goes down anyway and PrepareForShutdown quits the
    process (prepare_for_shutdown_expected and the handler survive the
    cancel); if logind refuses it, shutdown-prepared(FALSE) quits the process.
    Not exercised in a run.
  first_request_wins: >-
    the flag is set before the outcome of the first call is known. If that
    call is refused (polkit denial, another operation), the session ends
    like a logout with no retry - the intended "one request, act on its
    answer". Without the flag, duplicate calls already in flight (runs 04,
    05: sent before the first reply) might have been accepted by accident.
    Dialog methods arriving in EXIT (above) no longer change the action:
    the first request wins. No run covers a refused first call or a polkit
    prompt; HYPOTHESIS: with interactive=TRUE each repeated call could raise
    its own polkit prompt, which the flag prevents.
  threading_reentrancy: checked - main-loop only; the re-entry is the case the flag handles
  ABI_API_file_list: not_applicable - static private field, no API change
unknowns:
  - "Why logind answers the later repeats with ENXIO rather than
    OperationInProgress was not investigated (session already closing is the
    likely reason - HYPOTHESIS)."
  - "The quit timing is 'gone before the next 1 s tick' (upper bounds in the
    table); finer timing was not measured."
  - "No run with a refused first call, a polkit prompt, or a Cancel during
    EXIT."
  - "GNOME GitLab issues could not be searched with authentication."
design_challenger_required: true
architectural_task: false
design_review_result: PENDING   # review 1: REVISE (addressed); review 2 pending
```

## Outcome

PENDING the Design Challenger.
