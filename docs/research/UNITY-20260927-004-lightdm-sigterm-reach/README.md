# UNITY-20260927-004: lightdm +unity1's SIGTERM `_exit()` fix on our default stack

lightdm `1.32.0-6ubuntu4+unity1` carries one patch for LP #2168421 /
canonical/lightdm#484: `signal_cb()` in `src/session-child.c` leaves with
`_exit()` instead of `exit()` when it has no child to pass SIGTERM to
(`research/lightdm-sigterm-exit/`). The 2026-09 record reproduced the hang only
with the reporter's conditions (libgnutls preloaded, tcache off) and a model
that *set* `child_pid = 0` with gdb. This record answers: is the path reached
at all on our default stack, does the fix change anything for us, and is
`_exit()` in the handler the right layer. Agent A, target `target-desktop`,
2026-09-28.

Default stack on target: lightdm `+unity1`, greeter `lightdm-gtk-greeter`
(`60-lightdm-gtk-greeter.conf` wins over unity-greeter), autologin for mike,
PAM service `lightdm-greeter` (pam_env, pam_permit, pam_unix, pam_systemd,
common-session), systemd 259.5-0ubuntu3.4, glibc 2.43-2ubuntu2.4.

## 1. The path is reached on every login from the greeter

`tools/ld-sigterm-trace.bt` (bpftrace, whole machine) logs every SIGTERM to or
from a lightdm process, its delivery, and what `signal_cb()` does next:
`kill()` (passes it on) or `_exit()`/`exit()` straight after the delivery (the
no-child branch). `tools/login-cycle.sh` logs a test user out and in again
through the greeter (a temporary user `utest` with a password, deleted
afterwards). Run 01 used a version of the script that matched threads by their
own comm; runs 03-04 match them by the thread-group leader (a process-directed
signal can land on any of session-child's four threads: lightdm, pool-spawner,
gmain, gdbus - `runs/05`).

What happens when the greeter stops (FACT, every stop in the runs):

1. `systemd` (PID 1) sends SIGTERM to the greeter's session-child: logind is
   stopping the greeter's scope (`session-cN.scope: Killing process ... with
   signal SIGTERM` in the journal). The upstream sweep traces this to lightdm's
   own `session_stop()` -> `login1_service_terminate_session()` ->
   logind `TerminateSession` -> forced scope stop (lightdm session.c:931,
   systemd v259.5 logind-session-dbus.c:200-223 / logind-session.c:876-921;
   independent of KillUserProcesses).
2. session-child passes it on to the greeter, which exits; session-child
   reaps it and sets `child_pid = 0`.
3. The lightdm daemon sends its own SIGTERM (`session_real_stop()`,
   session.c:955-968), 2.4-11.8 ms after the first (17 stops measured).
4. If that second SIGTERM is delivered after step 2, `signal_cb()` takes the
   no-child branch - `exit()` in stock, `_exit()` in +unity1 - while the main
   thread is in its cleanup (X authority, `pam_close_session`, `pam_end`).

| Greeter stops | Build | no-child branch | 2nd SIGTERM before `child_pid = 0` (passed on) | merged with the 1st (already pending) | undetermined |
|---|---|---|---|---|---|
| `runs/01` (1), `runs/02` (4) | +unity1 | 2 | 0 | 1 | 2 (old thread filter) |
| `runs/03` (6) | +unity1 | 3 | 2 | 1 | 0 |
| `runs/04` (6) | stock 1.32.0-6ubuntu4 | 4 | 2 | 0 | 0 |

9 of 15 determinate stops took the no-child branch. All 23 deliveries in the
thread-aware runs 03-04 went to the main thread. `runs/02` also holds three failed login attempts (my
script typed the user name into the password field; no SIGTERM involved).
A user session's session-child at logout was never signalled: it reaps its
child and returns from `main()` (`runs/01`, pid 1395).

Side effect, same in both builds (FACT, journal): when the no-child branch
runs, the greeter's `pam_close_session` does not complete - "session closed
for user lightdm" is logged 0 or 1 times instead of 2 (pam_unix in both the
service and common-session). logind has already been told to terminate the
session (step 1).

## 2. `exit()` from the handler does not hang on our default stack

In stock, the no-child branch ran `exit()` 4 times in `runs/04`, taking
0.2-2.5 ms each. To cover the reporter's timing (SIGTERM landing inside
`malloc()`), `tools/ld-sigterm-model.sh` repeats the 2026-09 model on the
stock greeter session-child (debug info from Ubuntu's ddebs, installed only
for the test): gdb sets `child_pid = 0` and takes `main_arena.mutex`, then
SIGTERM; `tools/ld-fini-free.bt` (attached to that process only) records the
destructors that run and their allocator calls.

| Run | tcache | Arena lock held | Result | Allocator calls in `exit()` |
|---|---|---|---|---|
| `runs/07-model-stock-lock.txt` | default | yes | exited, `exit()` 6.6 ms | 35 `free` from libselinux's destructor |
| `runs/07-model-stock-lock-notcache.txt` | off | yes | exited, 5.0 ms | same |
| `runs/07-model-stock-lock-notcache2.txt` | off | yes | exited, 6.8 ms | same |
| `runs/07-model-stock-lock-notcache3.txt` | off | yes | exited, 5.2 ms | 35 `free`, **all `free(NULL)`** |

A normal `exit()` at the end of `main()` in +unity1 runs the same destructors:
35 `free` from `_dl_call_fini` (`runs/06-exit-allocator-calls-pid-scoped.txt`,
round 1). FACT: on the default stack the only allocator calls in `exit()` are
libselinux's destructor freeing pointers that are NULL (SELinux is off), which
returns without touching the arena; no other destructor allocates. The #484
deadlock cannot happen here through the allocator.

Correction to the 2026-09 record: it lists session-child's libraries as
libpam, libaudit, libsystemd, libnss_systemd. The greeter's session-child on
target now also maps libselinux, libmount, libblkid, glib/gio, libgcrypt and
libgpg-error (pam_gnome_keyring), pam_cap and others, and no libsystemd or
libgnutls (`runs/05`). The conclusion "no destructor touches the arena" still
holds, now measured rather than read from the maps.

## Evidence card

```yaml
task_id: UNITY-20260927-004
package: lightdm
target_series: resolute
issue: LP #2168421 / canonical/lightdm#484 - reachability of signal_cb()'s exit() on our default stack, and the layer of our _exit() fix
status: REPRODUCED   # the no-child branch, naturally, on every greeter login (9/15 stops); the hang: NOT_REPRODUCED on the default stack
issue_search_result: FOUND   # #484 open, maintainer asked the reporter to try _exit (2026-09-28); LP task New
source_version: 1.32.0-6ubuntu4+unity1 (published); stock 1.32.0-6ubuntu4 for the before runs
binary_version: 1.32.0-6ubuntu4+unity1 on target (restored after the runs)
source_commit: >-
  Ubuntu-Unity-LifeSupport/lightdm unity/resolute
  50a6a5dd8974a95db064f4a19dabe22becc329c0 (patch 91ac0049a44e)
observed: >-
  On every login from the greeter, logind's scope stop and the lightdm daemon
  each send the greeter's session-child a SIGTERM; in 9 of 15 stops the second
  arrives after the greeter was reaped and signal_cb() leaves through the
  no-child branch during cleanup. On the default stack exit() there completes
  in < 7 ms even with the arena lock held; its only allocator calls are 35
  free(NULL).
expected: session-child leaves promptly on SIGTERM, whatever it interrupts
reproduction: tools/login-cycle.sh under tools/ld-sigterm-trace.bt; tools/ld-sigterm-model.sh + tools/ld-fini-free.bt
evidence: runs/01-07; target journal 2026-09-28 13:58-14:50 UTC
root_cause_mechanism: >-
  FACT (code, 1.32.0 = upstream master 29b06b4 in this path): signal_cb()
  calls exit() when child_pid == 0. child_pid is 0 before fork() (the handler
  is installed first), in the forked child until execve, and after waitpid()
  returns. FACT (runs): lightdm stops a greeter with two SIGTERMs (logind
  TerminateSession -> scope stop, then its own kill()), so the second often
  lands after waitpid(). exit() is not async-signal-safe (POSIX XSH 2.4.3,
  signal-safety(7)); it runs atexit handlers and ELF destructors in whatever
  state the interrupted code left, and it hangs if a destructor needs a lock
  the interrupted code holds - the reporter's libgnutls destructor in free()
  on the main arena (research/lightdm-sigterm-exit, stock5).
invariant: >-
  a signal handler only calls async-signal-safe functions; session-child
  leaves promptly on SIGTERM whatever code it interrupted
existing_fix_result: FIXED_LOCAL   # our 91ac004 in +unity1; upstream has no fix (issue open)
existing_fix_evidence: >-
  Subagent sweep 2026-09-28: canonical/lightdm tags 1.33.0 (e42f6d6f) and
  1.33.1 (73987eb9), master 29b06b457b03 - no commit touches signal_cb, it
  still calls exit() (session-child.c:165-172); open PRs #414/#452/#475/#483
  touch session-child.c but not the handler; #484 open with one maintainer
  reply suggesting _exit; LP #2168421 New. No older report of session-child
  hanging on SIGTERM among the 484 GitHub issues/PRs (title+body scan;
  Launchpad beyond #2168421 not searched).
effect_for_us: >-
  FACT: none measurable on the default stack today - stock and +unity1 leave
  equally fast, and exit()'s destructors do not touch the heap. The fix
  matters when a library whose destructor frees memory (or takes another lock
  the interrupted code can hold) is loaded into the greeter's session-child:
  a PAM or NSS module pulling in libgnutls reproduced the hang in 2026-09
  (stock5, LD_PRELOAD model). Which real modules do that (sssd, krb5,
  fingerprint, smartcard stacks) is not checked. The exposure is on every
  greeter login, not a rare path.
candidate_approaches:
  - "F1 (published): _exit() instead of exit() in the no-child branch. One
    line; kill() and _exit() are async-signal-safe."
  - "F2: self-pipe / g_unix_signal_add / signalfd so the handler only records
    the signal and the main code decides."
  - "F3: block or ignore SIGTERM once the child is reaped, so the cleanup
    (X authority, pam_close_session, pam_end) always finishes."
chosen_approach: keep F1 as published
correct_layer: >-
  The defect is a non-async-signal-safe call inside a signal handler; the
  handler is where it is fixed, and _exit() keeps exactly the handler's
  stated intent ("otherwise just quit") without the destructors. gdm's
  session worker does the same before the session starts (_exit in a raw
  handler, 6b858695, kept by 039e3422 "to ensure a stuck pam module doesn't
  prevent the process from dying"); upstream's only response to #484 is to
  suggest _exit. The same change also covers the pre-fork and pre-exec windows
  where child_pid is 0.
defensive_workaround_rejected:
  - "F2: session-child has no main loop at that point - its main thread
    blocks in waitpid() and then in PAM calls - so a self-pipe or GLib source
    would never be dispatched while the cleanup runs; it would need a
    restructuring of session-child for no measured gain."
  - "F3: would change behaviour, not fix the handler: lightdm and logind stop
    the greeter with SIGTERM and lightdm has no timeout of its own, so a
    cleanup that blocks (a PAM module, D-Bus to a logind that is tearing the
    session down) would hold the next session until systemd's 90 s SIGKILL -
    the symptom #484 is about. Whether the skipped pam_close_session of the
    greeter matters is a separate question (unknowns)."
why_chosen: >-
  It removes the only non-async-signal-safe call from the handler with the
  handler's semantics unchanged, as upstream suggests and gdm does; measured
  here as behaviour-neutral on our default stack (no hang either way, same
  exit timing), and in 2026-09 as fixing the hang under the reporter's
  conditions.
not_justified: >-
  The 2026-09 record says the path is "not triggered by target's default PAM
  stack" and models it by setting child_pid with gdb. Measured now: the
  no-child branch runs on most greeter logins without any help; what the
  default stack lacks is not the path but a destructor that can block. Its
  library list for session-child is also outdated (above).
code_risks:
  ownership_lifetime: not_applicable - no object lifetime changes
  callbacks_cancellation: >-
    checked - _exit skips atexit handlers, ELF destructors and stdio flushing;
    session-child writes to the daemon with write() on pipes and g_printerr
    goes to unbuffered stderr (sweep, INFERENCE); the X authority removal,
    utmp/audit record and PAM close were already skipped by exit() on this
    branch
  threading_reentrancy: >-
    checked - the handler can run on any of session-child's four threads;
    kill() and _exit() are safe on any thread, exit() from a GLib thread while
    the main thread runs PAM would not be. All 23 deliveries recorded with the
    thread-aware trace (runs 03-04) went to the main thread.
  ABI_API_file_list: not_applicable - one line in a static function
unknowns:
  - "Which real PAM/NSS modules would load a library with a blocking
    destructor into the greeter's session-child (sssd, krb5, fprintd,
    smartcard) - not checked."
  - "Consequences of the greeter's skipped pam_close_session / pam_end (both
    builds, about half of greeter logins): nothing observed; modules with
    close-time work (pam_gnome_keyring, pam_cap) not examined. Upstream
    PR #414 is about PAM session close; not read."
  - "child_pid is a plain static read in the handler (strictly it should be
    volatile sig_atomic_t) and errno is not saved around kill() - INFERENCE,
    no effect measured."
  - "In two stops the handler passed the second SIGTERM on to a child that
    waitpid() had already reaped (delivered between waitpid() and child_pid =
    0): a kill() to a stale PID; a reuse of that PID in those microseconds
    was not observed or tested."
  - "Exit-time locks other than the allocator (stdio list lock) not examined;
    session-child's cleanup does little stdio."
design_challenger_required: true
architectural_task: false
design_review_result: PENDING
```

## Target state

Restored: lightdm `1.32.0-6ubuntu4+unity1`, no drop-in, no lightdm-dbgsym,
user `utest` deleted, test scripts and `/var/tmp` files removed. `libc6-dbg`
was already installed before this task.

## Outcome

PENDING the Design Challenger.
