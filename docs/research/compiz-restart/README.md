# Restarting compiz (`killall -1 compiz`)

The release notes give `killall -1 compiz` as the workaround for #3 (the
cursor stops responding) and warn that afterwards "windows from every
workspace may land on the first one". This checks that side bug. It is real,
and it was one of four things a compiz restart got wrong on our stack. All
four are fixed:

| # | What | Where | Fixed in |
|---|------|-------|----------|
| 1 | compiz segfaulted whenever it exited (SIGHUP, SIGTERM) | Unity `ThumbnailGenerator` | unity `+unity6` |
| 2 | windows on lower workspaces moved up 32 px per restart, until they were on the first row | compiz core `setWindowFrameExtents` | compiz `+unity2` |
| 3 | every window not focused since the restart had no title bar, buttons or frame | Unity `DecoratedWindow` + Yaru's 0 px inactive shadow | unity `+unity8` |
| 4 | gtk-nocsd's crash handler crashed at every crash of a GTK program, compiz included | gtk-nocsd (backports) | gtk-nocsd `+unity2` |

Measured on `target`, 2026-09-24, starting from the full upgrade from our
aptly (unity `+unity5`, compiz `+unity1`, nux `0ubuntu15+unity1`, gtk-nocsd
stock `0~20260321+0b77e1b-1`). Workspaces set to 2x2 through the same key the
Settings checkbox writes (`org.compiz.core` `hsize`/`vsize` at
`/org/compiz/profiles/unity/plugins/core/`); it applies live, the geometry
became 2560x1600. One xterm on each viewport plus a gnome-terminal on (1280,0)
(`runs/vpsetup.sh`), positions dumped with `runs/vpdump.sh`.

Clocks: builder's was about 1 h 40 min behind until 15:37Z (agent B found
it), so the builder-side times in the changelogs and `~/AGENTS-LOG.md` for
this work are that much early. Target's was 1 h 07 min behind (not
synchronised; found at 17:26Z when apt refused our `InRelease` as "not valid
yet", set from builder then), so the EEST times quoted from its journal below
are that much early too. Intervals are unaffected.

unity `+unity6` and `+unity7`, and gtk-nocsd `+unity1`, were built and tried
on target only; each lacked a fix found later. What is published is unity
`+unity8`, compiz `+unity2`, gtk-nocsd `+unity2`.

## Result

unity `+unity8`, compiz `+unity2`, gtk-nocsd `+unity2` on target, one xterm on
each of the four viewports (`runs/final.sh`):

- five `killall -1 compiz` in a row: compiz restarts in place (same pid), every
  window at the same position to the pixel after each one, the two on the
  lower row included (y 1032); no segfault, no core dump, no
  `g_hash_table` critical, `/var/crash` empty
  (`runs/15-final-five-sighup-positions.txt`);
- all four viewports after a restart: every window where it was, every one
  with its title bar and buttons (`runs/16-final-viewports.png`);
- `systemctl --user restart unity7.service`: no core dump, positions kept.

Not covered: logging out (compiz is stopped the same way as by `systemctl`,
not measured here), multi-monitor, `unity --replace`. Restarting still shows
about 10 s of bare wallpaper while compiz loads its plugins, as it did before.

## 1. compiz segfaulted whenever it exited

`killall -1 compiz` → SIGSEGV in `~UnityScreen`
(`runs/03-compiz-sighup-backtrace.txt`):

```
#0  __pthread_clockjoin_ex (threadid=0, ...)
#1  unity::ThumbnailGeneratorImpl::~ThumbnailGeneratorImpl  ThumbnailGenerator.cpp:94
...
#6  unity::UnityScreen::~UnityScreen  unityshell.cpp:526
#9  CompManager::finiPlugin
```

`~ThumbnailGeneratorImpl` did `pthread_join(thumbnail_thread_)` with no thread
ever created - nobody had opened a preview. `systemctl --user restart
unity7.service` (SIGTERM) crashed the same way with `+unity5`. Upstream's own
`TestThumbnailGenerator.TestNoURIThumbnail` does exactly that and died with
139 in our chroot; with the fix all 5 tests pass
(`runs/05-test-thumbnail-generator-red-green.txt`). The same file had more
thread bugs, fixed in the same commit: finished thumbnail threads never
reaped, the cleanup thread's flag never initialised and cleared under the
wrong name (so it ran at most once), never joined, and its directory handle
leaked.

Before the crash compiz printed 421 `g_hash_table_remove_internal: assertion
'hash_table != NULL' failed`. `runs/04-hash-table-criticals-gdb.txt`:
`~UnityScreen` calls `unity_a11y_finalize()`, which frees the accessible
table, and then destroys the panels, whose nux objects remove themselves from
it. Guarded in `a11y/unitya11y.cpp`.

While compiz crashed, each restart moved every window down by 32 px: X
reparents a dead window manager's clients to the root at their absolute
position, and the new compiz frames them there.

## 2. Windows on lower workspaces moved up to the first row

With (1) fixed, a restart is clean, and windows still moved: the ones on the
upper row stayed where they were, the ones on the lower row went up 32 px per
restart - 712, 680, 648 - and stopped once they were on the upper row
(`runs/11-unity7-five-sighup.txt`, `runs/12-unity7-viewports-after-sighup.png`:
the lower viewports empty). Given enough restarts that is the release notes'
"windows land on the first workspace".

`runs/drift.sh` on one window: at y 332, the client went to 300 when Unity
removed the 32 px title bar on exit and back to 332 when the new compiz added
it; at y 1032, 1000 and it stayed there.

compiz core, `CompWindow::setWindowFrameExtents`: the first time a window gets
frame extents (`!alreadyDecorated`, true for every window after a restart) it
moves the client by the new decoration, then takes the move back if that puts
the window past the bottom or the right of the workarea - the workarea of the
*current* viewport. A window on a lower viewport is always past its bottom.
Windows on the right do not drift only because Unity's frame has no left or
right border (`_NET_FRAME_EXTENTS` 0, 0, 32, 0).

Fix: move the workarea to the window's viewport, the way `outputDevice()`
already moves the window's geometry to the current one. Nothing changes for a
window on the current viewport, which is where new windows are mapped.

Compiz Reloaded has an open issue about windows moving between outputs on a
restart ([compiz-core#187](https://gitlab.com/compiz/compiz-core/-/issues/187),
[!179](https://gitlab.com/compiz/compiz-core/-/merge_requests/179)); that is
the 0.8 C code and multi-monitor output selection, not this.

## 3. Unfocused windows lost their title bars after a restart

After a restart only the focused window had a title bar, buttons and a shadow
(`runs/09-decorations-after-sighup-5-15-30s.png`); the others stayed bare
until they were focused (`runs/10-decorations-focus-restores.png`, d0 → d1).
The frame was there (`_NET_FRAME_EXTENTS` 0,0,32,0), nothing was painted in
it.

Unity's introspection (needs `libxpathselect1.4v5`, `runs/decostate.py`)
showed the bare windows `framed=1 fully_decorated=1 shadow_rect=(0, 0, 0, 0)`
(`runs/07-decorations-introspection-before.txt`). `Window::Impl::Draw()`
returns at once on an empty shadow rect - background, title and buttons
included.

Two causes, both needed:

- **The inactive shadow is empty.** Yaru, the default theme, sets
  `-UnityDecoration-inactive-shadow-radius: 0px`. `BuildShadowTexture` ran
  with radius 0 for the inactive texture and 10 for the active one
  (`runs/13-shadow-texture-trace.txt`, `runs/decogdb4.sh`), and
  `ComputeGenericShadowQuads()` returned on the empty texture without setting
  a shadow rect. In normal use nobody sees it: a window is focused when it
  maps, gets a rect from the active texture and keeps that stale rect when it
  loses focus. After a restart no window but one has been focused. Fixed in
  `+unity8`: with no shadow texture the frame is the shadow rect and no shadow
  quad is painted.
- **Elements set after the first paint were never used.** In one run
  (`runs/08-decorations-dprintf.txt`) the windows were painted before
  `Update()` had set their decoration elements; the shadow rect was cleared,
  `dirty_geo_` reset, and nothing set it again when the elements arrived.
  Fixed in `+unity7`: `Update()` redraws when the elements change. In the
  next run the order was the other way round and the empty texture was what
  was left; `+unity7` alone did not fix what the user sees
  (`runs/12-unity7-viewports-after-sighup.png`).

In `runs/08-decorations-dprintf.txt` dprintfs 2 and 3 were moved by gdb to
the next line with code (628, 874): their labels TEX-MISSING and
REDRAW-UNMAPPED are wrong, they mark the normal paths. Introspection lists
windows on other viewports with an empty shadow rect too, by design: their
decoration is computed when their viewport is shown - count only windows on
the current one.

## 4. gtk-nocsd's crash handler crashed itself

`unity-session` depends on `libgtk-nocsd0`, and
`/usr/lib/environment.d/50-gtk-nocsd.conf` preloads it into every process of
the session, compiz included (16 processes on target). On the first GTK window
the library forks a crash handler: `ld.so -- libgtk-nocsd.so.0 <program>`,
entered at `GTKNoCSDMain`, which waits for the program to exit and restarts it
without the library if it died of a signal.

When compiz died from (1), its handler segfaulted too
(`runs/06-gtk-nocsd-handler.txt`), and systemd could not restart compiz until
that was cleared: about a minute with no window manager the first time
(crash 16:48:52, the handler still in the unit at 16:49:22, new compiz
16:49:54). A later SIGSEGV with the old handler took 5.6 s, so the minute is
not a constant. The same happened with a plain GTK3 window killed with SIGSEGV
(`runs/nocsdcrash.sh`): gtk-nocsd's restart never worked on 26.04, and every
crash of any GTK application in the session brought a second crash with it.

Two causes, both fixed upstream on 2026-03-28, a week after the snapshot in
resolute:

- the library's constructor does not run when ld.so starts it as the program:
  `LD_DEBUG=libs` lists every dependency's init and not the library's, so
  `GTKNoCSDArguments` stayed NULL (`segfault at 10`). Upstream d851645,
  framed there as musl-only; glibc 2.43 does the same.
- entered as the ELF entry point, `GTKNoCSDMain` runs 8 bytes off the stack
  alignment the ABI promises; with arguments fixed alone it died at the next
  SSE instruction (`general protection fault`, `GTKNoCSDSaveArguments`,
  `GTK-NoCSD.c:51`). Upstream 664d8c6, `force_align_arg_pointer`.

With both backported the GTK3 window was restarted by the handler (new pid,
same argv) and nothing else crashed. For compiz (SIGSEGV sent by hand): the
handler exec'd compiz without the library at +2.2 s, systemd stopped the
unit's cgroup - that compiz included - and started its own at +6.6 s.

Not changed: whether gtk-nocsd belongs in compiz and the other session
services at all. Its restart and systemd's `Restart=` both act on the same
crash and systemd wins; harmless as measured, but a second compiz lives for
about a second and a half.
