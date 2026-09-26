# A-1: all six known issues re-checked from a clean snapshot (2026-09-26, agent A)

Task from the coordinator (May away, autonomous mode): roll `target` back to
`Clean-updated-2026-09-23`, add our aptly the way a user would (key +
`deb [signed-by=...] http://192.168.56.10:8080 resolute main`), `full-upgrade`,
and walk known issues #1-#6 with real input.

Rollback verified inside the guest (marker gone, archive versions). The upgrade
took 48 packages, all of ours: unity `+unity10`, u-s-d `+unity4`, compiz
`+unity2`, cinnamon-session `+unity3`, light-locker `+unity2`, lightdm
`+unity1`, unity-session `+unity1`, xorg-server `1.3+unity1`, nux
`0ubuntu15+unity2`, gtk-nocsd `4.8-1+unity2`, appmenu `+unity1`, indicators
`+unity1/2`. 10 archive phased updates held back, none of ours. Test tools added
afterwards (`xdotool`, `gdb`, `x11-utils`) - not part of what a user gets.

Real input throughout: the USB tablet's and the PS/2 mouse's evdev nodes
(found by name), never XTEST for pointer actions; Unity's dialogs are nux
windows inside compiz, so they are judged from `gnome-screenshot` pixels and
the bus (`EndSessionDialog.Open`).

| # | Issue | Result | Runs |
|---|---|---|---|
| 1 | Pointer invisible after login | **fixed**: shown after real motion every time, one u-s-d, name never lost | 12 of 12 cold autologins (`runs/A1-cursor.log`) |
| 2 | Session menu dead after cancelling | **fixed**: menu opens, indicator calls `EndSessionDialog.Open`, dialog drawn, cancel closes it | shutdown 20 (cross/Escape) + logout 20 + 3, instrumented 20 + 10 (`runs/A1-dlg2*.log`) |
| 3 | Pointer moves, clicks nothing | **fixed**: border drag with a second button / wheel, 0 stuck, resize intact | 50 (5 variants x 10, `runs/A1-resize.log`) |
| 3b | same, title-bar move with a second button (new case) | **not stuck**; see finding below | 30 (+unity10) + 15 (+unity9) (`runs/A1-title*.log`) |
| 4 | Wallpaper over Calamares (OEM) | **not tested here** - OEM two-stage install on VM `oem-test`, agent B's package; B verified it on 2026-09-24 | - |
| 5 | light-locker aborts at login | **fixed**: stock light-locker aborted at the first boot after rollback (SIGABRT 12:14:54, `/var/log/apport.log.1`); after the upgrade apport recorded no crash of anything in ~30 boots | ~30 boots |
| 6 | Shutdown confirmation twice | **fixed**: one dialog (Unity's), then restart / logout; no second window | restart 4 + logout 3 (`runs/A1-logout.log`, watcher files) |

Invalid runs, kept for honesty: the first #3 series (no `xdotool` on the clean
snapshot, then 100 stacked sensor windows - the harness failing, not the desktop);
one restart run (r3) and one menu cycle clicked before Unity had drawn its panel
(see below).

## Findings

1. **Behaviour change, low: a second button during a title-bar move cancels the
   move** on unity `+unity10` (0 of 10 moves completed with the right button
   pressed mid-move; the window returns to where it started). On `+unity9`, 3 of
   5 completed. Nothing gets stuck in either. Cause: the `+unity10` early return
   in `Edge::ButtonDownEvent` - the title bar is an `Edge` of type GRAB. Not
   changed yet: cancelling on a second button is defensible; letting the move
   finish would need the right button ignored by the title bar during a move
   rather than by all edges. For May's call.
2. **Slow session start on this VM, not attributed to our packages.** After
   `full-upgrade`, boot-to-compiz took 89-164 s and the panel appeared 9-19 s
   after compiz; across the 12 boots since the rollback `Startup finished`
   ranged from 47 s to 2 min 8 s and lightdm-to-compiz from 35 to 73 s, with
   unrelated services slow alike (e2scrub 31 s, apport 23 s, accounts-daemon
   19 s, dbus 12 s). A click in the first 1-2 minutes lands on a desktop that
   is not drawn yet - that, not #2, explains the two early misses. The stock
   session start was not measured separately, so this is an observation, not a
   verdict (`tools/panelwait.sh`).
3. **Journal on a clean boot with our packages**: one instance of every session
   daemon checked (u-s-d, compiz, panel service, cinnamon-session, nemo-desktop,
   light-locker, bamf, indicators, fallback mount helper, ibus); apport empty.
   Warnings are third-party or pre-existing: vmwgfx on VirtualBox, zeitgeist,
   PipeWire/pulse, portals, EDID, gnome-keyring's `discover_other_daemon`,
   `uwidgets-runner.desktop is marked executable` (same mode in the archive
   package), cinnamon-session's "Could not get session id" (it runs as a
   user service outside the logind session - upstream code, not our patches).
