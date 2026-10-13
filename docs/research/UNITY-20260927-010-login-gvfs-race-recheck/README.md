# UNITY-20260927-010: unity-session +unity1 (login gvfs race) re-checked on a clean snapshot

Legacy A-L16. unity-session `49.4+unity1` (`research/login-gvfs-race/`):
`/usr/libexec/run-systemd-session` began every session with `systemctl --user
stop graphical-session.target graphical-session-pre.target`. Stopping a
target that is not running still stops the units that are `PartOf` it *and
are starting right now*; when ibus-daemon's D-Bus activation of gvfs had
started gvfs-daemon a moment earlier, the start was killed, dbus-daemon was
never told, and every gvfs client waited out its 120 s timeout - a black
desktop for two minutes after 3 of 13 logins on 2026-09-24. The fix stops the
two targets only when one of them is not inactive.

Agent A, target `target-desktop`, 2026-09-28. No code change.

## Method

1. `target-desktop` restored to `Clean-updated-2026-09-23`; checked inside
   (no `~/.dirty`, new boot, stock packages, no aptly source).
2. Our aptly source added, **unity-session held at the stock `49.4`**,
   `apt-get full-upgrade`: everything else ours (unity `+unity11`,
   cinnamon-session `+unity3`, compiz `+unity2`, ...). "Before" and "after"
   differ in unity-session only.
3. A **cold login** is a reboot with lightdm's autologin (`tools/boot-series.sh`,
   driven from builder). The series never logs in to target over ssh before
   the graphical login - it waits for sshd's port without logging in, then
   200 s - because an ssh login as mike would start his user manager first
   and change what is measured. `tools/login-check.sh` then reads the boot's
   journal: was a gvfs-daemon start stopped within 120 s of its first start,
   how many `org.gtk.vfs.Daemon` activations timed out in dbus-daemon, how
   many clients logged a `StartServiceByName ... org.gtk.vfs.Daemon`
   timeout.
4. **Deterministic reproducer** (test-only files, removed afterwards):
   `/etc/X11/Xsession.d/95u010-early-gvfs` (`tools/`) requests
   `org.gtk.vfs.Daemon` over D-Bus in the background while Xsession runs -
   as ibus-daemon does, but always before `run-systemd-session` starts - and
   the user drop-in `gvfs-daemon.service.d/zz-u010-slow.conf`
   (`ExecStartPre=/bin/sleep 3`) keeps that start job open for 3 s. The
   script's stop then always lands inside the start: the losing order of the
   race, every time. This is the real session, the real script and the real
   gvfs-daemon, with the timing pinned - not a model unit.

## Result

| | unity-session 49.4 (stock) | 49.4+unity1 (ours) |
|---|---|---|
| cold logins, no injection | 0 of 10: no gvfs start stopped, no timeout (`runs/01`, recount `runs/03`, `runs/06`) | 0 of 10 (`runs/05`, `runs/06`) |
| cold logins with the reproducer | **3 of 3**: `gvfs-daemon.service: Control process exited, code=killed, status=15/TERM` 0.9 s into the start, `Stopped gvfs-daemon.service`; 3 activation timeouts in dbus-daemon; **29 clients** (nemo-desktop, xdg-desktop-portal, indicators, polkit agent, bamfdaemon, update-notifier, ...) with `StartServiceByName ... org.gtk.vfs.Daemon: Timeout was reached`; no gvfsd 200 s after login (`runs/02`, `runs/03`, journal `runs/07`) | **0 of 3**: the same early request and slow start, gvfs-daemon started after 6 s (3 s of it the drop-in), `Successfully activated service 'org.gtk.vfs.Daemon'`, no timeout (`runs/04`, journal `runs/08`) |

Why the cold logins without injection never hit it: on the ten stock boots
ibus-daemon asked for gvfs 10.5-20.3 s after the login, gvfs-daemon's start
job began 2.2-5.8 s after the request, and the session's targets were reached
3.5-4.5 s after that start job; no stop landed inside a start (killed 0 in
10; `runs/06`, which has the timings and counts of all 26 boots). The 2026-09-24 hits were on logins after a logout in the same
boot; the first login after a boot was never among them.

## Evidence card

```yaml
task_id: UNITY-20260927-010
package: unity-session
target_series: resolute
issue: legacy A-L16 - login race: run-systemd-session's stop of inactive graphical-session targets kills gvfs-daemon's start (unity-session +unity1)
status: REPRODUCED   # deterministically, 3/3 with the stock script; 0/10 cold logins without the reproducer
issue_search_result: FOUND   # research/login-gvfs-race
source_version: unity-session 49.4+unity1 (published)
binary_version: same, on target after installing it from our aptly
source_commit: Ubuntu-Unity-LifeSupport/unity-session 0078ead (fix), 951b463 (changelog)
observed: >-
  Stock 49.4 with the reproducer: gvfs-daemon's start killed by SIGTERM 0.9 s
  in, 3 activation timeouts, 29 clients time out, no gvfsd - every time.
  49.4+unity1 with the same reproducer: gvfs starts, no timeout. Without the
  reproducer, 0 of 10 cold logins either way.
expected: a login never kills a starting gvfs-daemon
reproduction: tools/95u010-early-gvfs + tools/zz-u010-slow.conf, tools/boot-series.sh, tools/login-check.sh
evidence: runs/01-08; target journal 2026-09-28 18:37-20:40 UTC
existing_fix_result: FIXED_LOCAL
existing_fix_evidence: before/after with unity-session as the only difference, deterministic reproducer 3/3 -> 0/3
chosen_approach: NONE - no change
code_risks:
  ownership_lifetime: not_applicable
  callbacks_cancellation: not_applicable
  threading_reentrancy: not_applicable
  ABI_API_file_list: not_applicable - no change
unknowns:
  - "Logins after a logout in the same boot (where the race was seen on
    2026-09-24) were not repeated statistically here; the reproducer covers
    the mechanism for any login."
  - "Still open by design (research/login-gvfs-race): when a previous
    session left its targets active (the session itself crashed), the stop
    is needed and the race can still happen."
  - "The reproducer sets the order; the natural rate on today's stack is
    unknown beyond 0 in 10 cold logins."
design_challenger_required: false
architectural_task: false
design_review_result: NOT_REQUIRED
```

`runs/01`, `02`, `04`, `05` print "boot 0" or the old counter on each line
(the series' own check at the time); `runs/03` and `runs/06` are the recount
with the final `tools/login-check.sh`, which first missed the kill (it looked
for "Stopped" on the line after "Starting"; the kill logs a control-process
line first).

## Outcome

`ALREADY_FIXED` / `FIXED_LOCAL`: with the order of the race pinned by the
reproducer, the stock `run-systemd-session` kills gvfs-daemon's start at
every login (3/3) and 29 session clients wait out the D-Bus timeout; with
`49.4+unity1` it never does (0/3), on the same clean system with only
unity-session different. Natural cold logins hit it 0 of 10 either way.
Target left as target = aptly (no holds, the reproducer removed), `~/.dirty`
present, xdotool installed.
