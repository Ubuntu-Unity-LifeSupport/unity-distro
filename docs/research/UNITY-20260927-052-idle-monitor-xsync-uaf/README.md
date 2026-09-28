# UNITY-20260927-052: unity-settings-daemon frees its XSync state when an IdleMonitor client leaves

Found by the Design Challenger in UNITY-20260927-005 (D4). Agent A, target
`target-desktop`, 2026-09-28.

## Evidence card

```yaml
task_id: UNITY-20260927-052
package: unity-settings-daemon
target_series: resolute
issue: >-
  local: use-after-free and double free of the idle monitor's global XSync
  state when an org.gnome.Mutter.IdleMonitor D-Bus client disappears
status: REPRODUCED
issue_search_result: NOT_FOUND   # Launchpad u-s-d (double free, name_vanished_callback, xevent_filter, g_slice_free, SIGABRT, idle monitor) and web, 2026-09-28T09:15Z; errors.ubuntu.com not searchable (UNKNOWN); LP #1397232 (2014, 'free(): invalid pointer', no backtrace) does not match the message but cannot be ruled out
source_version: 15.04.1+21.10.20220802-0ubuntu6 (archive) and 0ubuntu7+unity5 (ours)
binary_version: measured 0ubuntu6 and 0ubuntu7+unity5 on target
source_commit: >-
  code present since the 2014 import f88f984 (14.04.0+14.10.20141010); our
  published branch head d2c24b7 (+unity5)
observed: >-
  Two D-Bus clients each call AddUserActiveWatch on
  /org/gnome/Mutter/IdleMonitor/Core and exit without RemoveWatch. The second
  exit makes unity-settings-daemon print "double free or corruption (!prev)"
  and abort (SIGABRT, core dumped, apport crash file); systemd restarts it.
  +unity5: 4/4 runs; archive 0ubuntu6: 2/2.
expected: a client leaving removes only its own watch; the daemon keeps running.
reproduction: tools/two-clients.sh (tools/watch-client.py twice)
reproduction_result: PASS   # reproduced: 4/4 on +unity5, 2/2 on 0ubuntu6
evidence: >-
  runs/two-clients-unity5.txt, runs/two-clients-0ubuntu6.txt,
  runs/valgrind-two-clients-unity5-symbols.log, runs/valgrind-pause60-unity5.log
root_cause: >-
  gnome-settings-daemon/gsd-idle-monitor.c name_vanished_callback() - the
  per-watch GBusNameWatcher callback run when the client that added a D-Bus
  watch leaves - removes that watch and then does
  `if (xsync) g_slice_free (GsdXSync, xsync);` on the process-global
  `static GsdXSync *xsync`, which gsd_idle_monitor_init_dbus() allocates once
  for the life of the process and xevent_filter() reads on every X event.
  The pointer is not reset.
root_cause_mechanism: >-
  First client leaves: xsync is freed while the X event filter keeps reading
  xsync->sync_event_base on every X event (use-after-free); once the chunk is
  reused, XSyncAlarmNotify events are mis-recognised or missed, so idle and
  user-active watches can stop firing or fire on the wrong events
  (HYPOTHESIS - not measured). Second
  client leaves: the same pointer is freed again (double free); glibc aborts
  the daemon.
root_cause_evidence: >-
  FACT (runs/valgrind-pause60-unity5.log, 60 s of normal running first, no
  error): "Invalid free()" at the second client's exit, "Address ... is 0
  bytes inside a block of size 24 free'd" by the first, "Block was alloc'd at
  gsd_idle_monitor_init_dbus (gsd-idle-monitor.c:959)" - the xsync
  allocation; both frees come from the gio name-watcher dispatch. INFERENCE:
  the freeing line is 731 - no name_vanished_callback frame is shown (gio
  frames unsymbolised, likely a tail call), but it is the only
  g_slice_free (GsdXSync) in the file. INFERENCE:
  runs/valgrind-two-clients-unity5-symbols.log "Invalid read of size 4 at
  xevent_filter (gsd-idle-monitor.c:332)" is a read of the freed xsync -
  valgrind attributes the address to a later 25-byte allocation (it had been
  reused), offset 8 matches sync_event_base, and the same address is later
  freed by the name-watcher dispatch. The pause60 run shows no read error
  between the two exits (no X event reached the filter in that window).
invariant: >-
  The XSync state (display, event/error bases) lives as long as the process;
  a D-Bus client leaving removes only the watches that client created.
existing_fix_result: NOT_FIXED
existing_fix_evidence: >-
  Investigator sweep 2026-09-28T09:15Z: the line came in with the first
  import of the idle monitor (14.04.0+14.10.20141010, Tim Lunn, LP #1377847)
  and is unchanged in every Ubuntu branch; live heads of gitlab ubuntu-unity
  ubuntu/devel, Launchpad git-ubuntu ubuntu/devel and our unity/resolute
  still have it; stonking 26.10.1ubuntu.build1 gsd-idle-monitor.c is
  identical to ours. No tracker report of this crash found.
candidate_approaches:
  - "F1: remove the free from name_vanished_callback (it keeps
    gsd_idle_monitor_remove_watch). xsync stays owned by the process-wide
    initialisation. Upstream source of the copy does exactly this: mutter
    3.10.4/3.12.2 src/core/meta-idle-monitor.c and 3.14.0
    src/backends/meta-idle-monitor-dbus.c, and gnome-flashback 3.14.0/3.40.0,
    have name_vanished_callback = remove the watch only (links in the
    investigator's report; the global free is a Ubuntu-only addition, reason
    unknown)."
  - "F2: free and reset the pointer (xsync = NULL). Not built."
  - "F3: reference-count xsync per watch. Not built."
chosen_approach: F1
why_chosen: >-
  It restores the invariant at the one place that breaks it, with the
  smallest change (two lines removed), and matches the upstream code the file
  was copied from (mutter 3.10.4 name_vanished_callback, checked by the
  Design Challenger).
alternatives_rejected:
  - "F2: xevent_filter (line 332, the only reader besides init_xsync_global)
    dereferences xsync unconditionally, so the first departure would become a
    NULL dereference (code read)."
  - "F3: there is a single owner (the process, allocation guarded by
    dbus_name_id) and nothing to count (code read)."
code_risks:
  ownership_lifetime: checked - xsync is allocated once (gsd_idle_monitor_init_dbus, guarded by dbus_name_id, main.c:481) and never needs freeing before exit
  callbacks_cancellation: checked - destroy_dbus_watch already unwatches the name and frees the DBusWatch; the removed lines touch only the global
  threading_reentrancy: not_applicable - main loop only
  ABI_API_file_list: not_applicable - static function body, no exported symbol
unknowns:
  - "How often it happens in a real session: IdleMonitor clients on target
    are libgnome-desktop-3/4 (GnomeIdleMonitor, used by applications) and
    /usr/bin/snap (runs/idlemonitor-referencing-files.txt); after a daemon
    restart no client registered a D-Bus watch within 36 s
    (runs/idlemonitor-clients-at-restart.txt). Real-world frequency not
    measured (INFERENCE: any GnomeIdleMonitor user that exits twice)."
  - "Watch ids 1-3 seen before our clients are the daemon's own in-process
    watches (get_next_watch_serial is shared, gsd-idle-monitor.c:285-290)."
design_challenger_required: true
design_review_result: APPROVE
architectural_task: false
correct_layer: >-
  The idle monitor's D-Bus glue owns both the per-watch callback and the
  global it wrongly frees; the fix is in that callback, removing a free of
  state it does not own.
defensive_workaround_rejected: >-
  Guarding the readers (xevent_filter NULL checks) or restarting the daemon
  on crash would hide a lifetime error in the one function that causes it.
```

## Design review

Temporary Design Challenger (`.claude/agents/design-challenger.md`), separate
read-only subagent: **APPROVE** (2026-09-28). F1 is the smallest change that
restores the invariant; lifetime checked against d2c24b7 - client exit,
RemoveWatch-then-exit and a fired user-active watch all clean up through
destroy_dbus_watch, g_bus_unwatch_name inside the vanished callback is
allowed, xsync only needs freeing at exit; mutter 3.10.4's
name_vanished_callback only removes the watch. Card fixes it asked for are
applied above (two INFERENCE labels, one HYPOTHESIS, F2 wording, why_chosen /
alternatives_rejected). Test plan it asked for:

1. valgrind with real input between and after the two exits: Invalid read at
   xevent_filter:332 before, no idle-monitor error after;
2. a kept client's watch still fires after two others leave (user-active and
   idle watches);
3. plugins' own watches still work after departures (cursor hide/show);
4. RemoveWatch then exit: no error, no second removal;
5. record how the scripts are deployed on target;
6. in-tree test: say whether gsd-idle-monitor has a test seam.

In-tree test: none possible cheaply. `gnome-settings-daemon/` has no tests and
nothing in the tree tests the idle monitor (`git grep` of d2c24b7 for
idle-monitor in test files: none); a test would need an X server with XSync,
a session bus and the daemon's D-Bus export. The regression test is the live
reproducer below (fail before / pass after on target).

