# UNITY-20260927-040: Edge::ButtonDownEvent still releases compiz's grab during expo

Follow-up of UNITY-20260927-001 (`research/UNITY-20260927-001-edge-resize-grab/`
on branch `a/UNITY-20260927-001`), which kept unity `+unity10`'s early return
in `Edge::ButtonDownEvent` - it returns while compiz holds a `resize` or `move`
grab - and left open whether the wider condition "any compiz grab"
(`screen->otherGrabExist(nullptr)`, option A2) is needed, and three unknowns:
unityshell's gesture grab `unity`, expo, and keyboard-initiated move/resize.
Agent A, target `target-desktop`, 2026-09-29.

Target: snapshot `Clean-updated-2026-09-23` restored and confirmed from the
guest (fresh boot, no `~/.dirty`, stock unity), our repository added,
`full-upgrade`: unity `7.7.1+26.04.20260306-0ubuntu3+unity11` (published,
contains `+unity10`), compiz `1:0.9.14.2+25.10.20250930-0ubuntu3+unity2`.
Workspaces switched on (2x2, `/org/compiz/profiles/unity/plugins/core/hsize`
and `vsize` = 2, what "Enable workspaces" sets) - with one viewport expo does
not open. Real evdev devices only (USB tablet places the pointer, PS/2 mouse
clicks, AT keyboard types), no XTEST; xdotool only to arrange windows and read
state.

## 1. Tools

`tools/grab-edge.sh VARIANT` - one left click on an xterm's right border
(at its real position, 901,377) while a compiz grab other than a mouse-driven
move/resize runs, then the grab state (`tools/grab-probe/`), and a real click
on a sensor window (`tools/clickcheck.sh`, `tools/clicksensor.py`: does a
click reach an application?). `tools/uprobetrace-040.sh` wraps it in bpftrace
uprobes in compiz (UNITY-20260927-001's `uprobetrace.sh` extended): `EDGE-DOWN`,
compiz grab push/remove, resize initiate/terminate, X pointer/keyboard
grab/ungrab with callers, and the button events `UnityScreen::handleEvent` and
`ExpoScreen::handleEvent` receive. `tools/grab-series.sh VARIANT N` runs a
series; a run is STUCK when the final click does not reach the sensor or a
grab is still held, and then logs the X server's grab list
(`XF86LogGrabInfo`) and recovers (`SIGHUP` to compiz, as for #3).
`tools/replay-stuck1.sh` replays the first stuck sequence (section 3).

## 2. Keyboard-initiated move and resize: covered by +unity10

Alt+F8 / Alt+F7 (`runs/s9`, 5 runs each, trace in every run):

| Variant | Edge reached | Edge ungrab | stuck |
|---|---|---|---|
| `kbdresize`, `kbdresize-esc`, `kbdmove` (click where the pointer is) | 0/15 | 0/15 | 0/15 |
| `kbdresize-drag` (tablet back to the border, click) | 5/5 | 0/5 | 0/5 |
| `kbdmove-drag` | 3/5 | 0/5 | 0/5 |

FACT: compiz warps the pointer into the window for a keyboard move/resize
(700,377 = the xterm's centre); a click there ends the operation
(`RESIZE-TERMINATE`, `REMOVE-GRAB`) and never reaches a decoration. When the
pointer is brought back onto the border, the press does reach
`Edge::ButtonDownEvent`, which returns before its `XUngrabPointer` /
`XUngrabKeyboard` - the `resize`/`move` grab is listed - and the operation ends
normally. UNITY-20260927-001's unknown "+unity10 returns first by
construction" is now measured.

## 3. Expo: Edge releases expo's grab; in a reachable state the pointer freezes

Every press on the border position while expo runs reaches
`Edge::ButtonDownEvent` and calls `XUngrabPointer` and `XUngrabKeyboard` from
`Manager::Impl::HandleFrameEvent` (FACT, 28 of 28 runs that pressed there:
`runs/s1`, `s2`, `s3`, `s7`, `s10`, `s6`/`s8` orig, `t-expo-1`,
`t-kbdresize-drag-1`). `Manager::Impl::HandleFrameEvent`
filters only scale (`IsScaleActive()`); nothing filters expo, and +unity10's
condition names only `resize` and `move`.

Most of the time that is harmless by luck: the button release still reaches
compiz (on the border's input window, `runs/s10`), expo ends on it and removes
its grab (`ExpoScreen::donePaint` -> `removeGrab`), 22 of 22 in `s1`, `s2`,
`s3`, `s7`, `s10`.

The first run that combined the variants froze the pointer
(`runs/t-expo-1*`, `runs/t-kbdresize-drag-1*`, X grab list
`runs/stuck1-xorg-grabinfo.txt`): expo stayed on screen, Escape did nothing,
clicks reached nothing, and the X server showed the signature of known issue
#3 - "Active grab ... client /usr/bin/compiz ... (from passive grab) (device
frozen, state 6) passive grab type 4, detail 0x0". `tools/replay-stuck1.sh`
replays that sequence: expo; click on the border (expo leaves to viewport
(1,0)); Super+S again (expo re-entered); a check click at 0,207, i.e. on the
launcher (LibreOffice Calc starts); then, inside that expo, window
arrangement, Alt+F8 (refused), the tablet to the border, one PS/2 click.

| Replay (`runs/s6`, `runs/s8`) | Edge ungrab | expo removes its grab | X grab list afterwards | stuck |
|---|---|---|---|---|
| `orig` - last click on the border | 4/4 | 0/4 | compiz passive grab, device frozen | **4/4** |
| `noborder` - same sequence, last click 80 px right (no decoration) | 0/4 | 4/4 | none | 0/4 |

Mechanism (FACT from `runs/s8`, button events seen by compiz): in `orig`,
compiz receives the press on the xterm's border input window (Unity, then
expo), `Edge::ButtonDownEvent` calls `XUngrabPointer`, and **no ButtonRelease
reaches compiz at all**; expo acts on the release, so it never ends, stays in
compiz's grab list with no X grab behind it, and compiz stops thawing the
synchronous passive button grabs on window frames (UNITY-20260927-001
mechanism step 4) - the next click on a frame freezes the pointer. In
`noborder`, compiz receives press and release, expo ends 260 ms later. In the
harmless runs (`s10`) the release still arrives on the border's input window.
Which window the release goes to once Edge has dropped the grab depends on
the window arrangement under the pointer (INFERENCE: the replay's state - Calc
started on the current viewport, the xterm re-arranged inside expo - is what
sends it elsewhere; not traced further). The defect does not depend on that
detail: without Edge's ungrab, compiz's expo grab would receive the release in
every arrangement.

So the unknown "expo" is reproduced on the published build; it is the same
defect as #3 (a raw ungrab in `Edge::ButtonDownEvent` under a live compiz grab;
the grab's owner never sees its release), in a grab +unity10 does not name.

Invalid runs, kept: the STUCK verdicts of `runs/s1` (all 5 false: the sensor
window had been left on another viewport, the check click went off screen;
`clickcheck.sh` now moves it into view - their traces are valid);
`runs/t-kbdmove-drag-1`, `t-expo-esc-1` ran inside the stuck state left by
`t-kbdresize-drag-1`; `runs/s4` `expo-twice`: the second click never reached a
decoration (the xterm was not on the current viewport) - not a test of the
border; the first `expo-dnd` series (xdotool picked the cover window, "no
windows in the stack"), repeated as `runs/s7`.

## 4. Gesture grab `unity`: not measurable here

unityshell pushes `unity` for a window drag by touch gesture
(`WindowGestureTarget.cpp:140`). target has no touch device (VirtualBox USB
tablet and PS/2 mouse only) and the vbox tools cannot add one; not measured.
Code reading: the press path to `Edge::ButtonDownEvent` is the same as for
expo; A2 covers it by construction.

## 5. Existing fix and candidate grabs

Investigator subagent, 2026-09-29 (sources in the evidence card):
Launchpad #1393523 (2014, New in unity, compiz and unity (Ubuntu)) reports
decoration controls reacting in expo and "clicking anywhere on the screen
does nothing ... needing to press Super+S", once needing a lightdm restart -
the same symptom. No fix anywhere: upstream unity (gitlab ubuntu-unity/unity;
`DecorationsEdge.cpp` last changed 2014, `DecorationsManager.cpp` 2016), all
4704 lp:unity and 1516 lp:compiz merge proposals, Ubuntu devel (same
`0ubuntu3`, native), Debian (no unity), AUR, gentoo-unity7. Our f2268bef is
the only change to `Edge::ButtonDownEvent`; it covers move and resize only.

compiz 0.9.14.2 (`src/screen.cpp:3443`): `otherGrabExist(first, ...)` returns
true on the first listed grab whose name is not in the NULL-terminated list;
with `nullptr` first it is true exactly when any grab is listed
(`!grabsEmpty()`). unityshell already uses `otherGrabExist(nullptr)`
(`unityshell.cpp:1059`). move and resize refuse `_NET_WM_MOVERESIZE` while any
other grab is listed (`move.cpp:57`, `resize-logic.cpp:1281`), so while such a
grab exists Edge's only effect is the ungrab.

Grabs of a default Unity session (`data/compiz/unity.ini` plugins; code
reading, INFERENCE unless measured): `move`, `resize` (covered by +unity10),
`expo` (measured, section 3), `wall` (viewport slide 0.3 s / switcher
preview; ends on a timer, so an ungrab there probably heals), `unity-switcher`
(measured not reaching Edge in -001), `unity` (touch gesture drag, not
measurable here), `ezoom` (zoom box, no default binding), `scale` (already
filtered in `HandleFrameEvent`). None is held permanently; each ends through
`removeGrab`.

## 6. A simpler reproduction: a title drag in expo

Found while taking the +unity11 baselines of the test plan (`runs/b11`,
`runs/b11s`): in expo, press on the xterm's title bar at its real position
and move - `GrabEdge` passes it to `Edge::ButtonDownEvent` (motion path),
which ungrabs; compiz then sees the press but no release, expo never ends,
and the next click freezes on a frame. **+unity11: 5/5 stuck**, X grab list
"device frozen" 5/5, no expo `REMOVE-GRAB`. This is LP #1393523's "when
dragging a window, the drag fails midway and then clicking anywhere on the
screen does nothing". It needs no special state, so it is the regression test.

## 7. Fix: unity +unity12 (A2) - test build, verified on target

Ubuntu-Unity-LifeSupport/unity branch `a/UNITY-20260927-040`: `78153782`
(`decorations/DecorationsEdge.cpp`, the condition `screen->grabExist("resize")
|| screen->grabExist("move")` replaced by `screen->otherGrabExist(nullptr)`,
comment rewritten; 10+/8-) and changelog `7b0eca27`
(`7.7.1+26.04.20260306-0ubuntu3+unity12`), on `unity/resolute` `2040279d`.

**Build.** `scripts/build_sbuild.py` fails for unity (`build/build_sbuild-failed-nux.log.xz`:
`nux-4.0` not found - the archive's nux 0ubuntu12 `.pc` requires `libpcre`,
known since 2026-09-22, DECISIONS "nux -0ubuntu13"), and the tool has no way
to add our nux. Test build: plain `sbuild -d resolute --extra-package` with
our published `libnux-4.0-0`/`-common`/`-dev` `0ubuntu15+unity2` (what target
runs): `Status: successful`, 503 s, no warning in `DecorationsEdge.cpp`
(`build/test-build-extra-package-nux.log.xz`, artifact hashes in
`build/test-build-sha256.txt`, debs in `~/work/a/040-build/test/`; pre-build
version order `build/version-prebuild.json`). **No approved build manifest
exists** - the task stops here for that (Outcome).

**On target** (one boot 2026-09-29 16:55 EEST, unity/libunity-core
`+unity12` from that build, compiz restarted, no deleted library mapped;
`runs/u12` first part, `runs/u12r` after the pause for UNITY-20260927-047
phase L, same boot, `runs/u12r2`):

| Test | +unity11 | +unity12 |
|---|---|---|
| (1) title drag in expo (regression) | 5/5 stuck (`b11s`) | 0/5: Edge reached, no ungrab from the decorations, release reaches expo, expo removes its grab, the sensor click arrives |
| (1b) replay of the first stuck run | 4/4 stuck (`s6`, `s8`) | orig 0/3 (Edge reached, expo removes its grab, no frozen grab), noborder 0/1 |
| (2) expo-border, expo-altf8-border, expo-dnd-border | ungrab 20/20 (harmless) | 0/9 stuck, 0 ungrabs, expo ends on the click (`u12/expo`) |
| (2) expo-control | 0 ungrabs | 0/3 (`u12r/expo`) |
| (3) title bar: immediate (fixedwin, not maximizable), hold (timer), motion; double-click | moves / maximizes (`b11`) | 2/2 each: moves by the drag, double-click maximizes and restores (`u12r`) |
| (4) first border press after a wall slide / after expo closed | resizes (`b11`) | after-expo 3/3, after-wall 5/6 resize +42 px (`u12r2`) |
| (5) keyboard move/resize (kbdresize, kbdmove, -drag) | 0/25 stuck (`s9`) | 0/12 stuck, 0 ungrabs (`u12r/kbd`) |
| (6) UNITY-20260927-001 #3 set: rmbslow, rmb, rmb2, wheel, mid, plain, 7 title variants | fixed since +unity10 | 0/65 stuck, resize/move working (`u12r/rg-*.log`) |

Notes on the runs: the first two after-wall/after-expo runs in `u12r` are
invalid (the xterm had been moved onto the viewport being left, the press hit
nothing; the script now waits for viewport (0,0) - `u12r2`). after-wall run 1
of `u12r2`: a move was already in progress when the press came (MoveScreen
ended it on the press; the preceding manual `titlemovermb2` trace had left the
xterm iconified and the script re-activated it) - not the border path.
`titlermb2`/`titlemovermb2` in `u12r` ended at x=1040, where -001's +unity10
logs had 595,276 Iconic; a traced single run on +unity12 (`u12r2/tm2-u12.*`)
gives 595,275 Iconic - right press during a title move goes to `GrabEdge`
button 3 -> `PerformWMAction`, not to Edge; A2 does not change it. The
aborted first test pass on this build ended the session once:
cinnamon-session crashed in `IceProcessMessages` after a compiz `SIGHUP`
restart (`runs/u12-cinnamon-session-crash.txt`) - not the Edge path;
follow-up proposed.

## 8. Release build and its check on target

**Build.** `scripts/build_sbuild.py` (main with UNITY-20260929-013) from
`packages/unity` at `7b0eca27` (origin our GitHub), `--extra-package` our
published `libnux-4.0-0`/`-common`/`-dev` `0ubuntu15+unity2` from
`/srv/aptly/public/pool/main/n/nux/`: `Status: successful`, 553 s, manifest
`build-gated/UNITY-20260927-040-unity-build-manifest.json` (result PASS,
source tree `e204f809`, 14 artifacts, `build_dependencies`: three entries,
each `in_our_repository_pool`, checked against the `.buildinfo`;
`build_dependencies.manifest_error` returns none).

**Compared with the test build** (`tools/compare-builds.sh`,
`build/release-vs-test.txt`): all seven binary packages have the same file
list, the same control Version/Depends and identical `DEBIAN/md5sums` - the
installed content does not differ from what section 7 tested.

**On target** (one boot 2026-09-29 20:38 EEST, unity, libunity-core,
unity-schemas, -services, -uwidgets from the gated build, rebooted; no deleted
library mapped in compiz, only memfd/SysV; workspaces 2x2;
`tools/release-sample.sh`, `runs/rel`, summary
`build/release-sample-summary.txt`):

| Test | gated +unity12 |
|---|---|
| (1) title drag in expo (regression) | 0/5 stuck; each run: Edge reached, no ungrab from the decorations, expo removes its grab |
| (1b) replay of the first stuck run | orig 0/2, noborder 0/1; no active or frozen grab |
| (2) expo-border | 0/2 stuck, no ungrab from the decorations |
| (3) title bar immediate, motion | moves; pointer and keyboard free |
| (4) first border press after expo | resizes +42 px; no grab before the press |
| (5) keyboard resize reaching the border | 0/2 stuck, no ungrab from the decorations |
| (6) UNITY-20260927-001 #3: rmbslow, titlemovermb | 0/3 each |

## Evidence card

```yaml
task_id: UNITY-20260927-040
package: unity
target_series: resolute
issue: >-
  follow-up of UNITY-20260927-001 (A2 and its unknowns); LP #1393523 (expo:
  clicks stop working); gitlab ubuntu-unity/issue-tracker #165 (cursor stops
  responding, cause not given)
status: REPRODUCED
issue_search_result: FOUND   # LP #1393523, open, no fix
source_version: 7.7.1+26.04.20260306-0ubuntu3+unity11 (published; contains +unity10 f2268bef)
binary_version: unity/libunity-core-6.0-9 etc. 7.7.1+26.04.20260306-0ubuntu3+unity11 from our repository on target
source_commit: Ubuntu-Unity-LifeSupport/unity unity/resolute 2040279dadc253e76daad4ac2e1ffacc7a2d1e74
observed: >-
  While compiz's expo runs, every press on a window border position reaches
  Edge::ButtonDownEvent, which calls XUngrabPointer/XUngrabKeyboard and so
  releases expo's X grabs (28/28 runs). Usually the release still reaches
  compiz and expo ends (22/22); in the replayed state of the first stuck run
  no ButtonRelease reaches compiz, expo stays in compiz's grab list, and the
  pointer freezes on the next frame click - X server: compiz passive frame
  grab, device frozen (4/4, plus the original run); the same sequence with
  the last click beside the border: 0/4. Keyboard-initiated move/resize:
  Edge returns early by +unity10 (0 ungrabs in 8 presses that reached it).
expected: >-
  A press on a decoration border while a compiz grab runs leaves that grab
  and its X grab alone; the grab ends on its own terms, clicks keep working.
reproduction: >-
  SCEN=after-tests.sh tools/grab-series.sh expo-title N (title drag in expo:
  5/5 stuck on +unity11, section 6 - the regression test);
  tools/replay-stuck1.sh OUTDIR N orig (4/4 stuck on +unity11) and ...
  noborder (control, 0/4); series: tools/grab-series.sh VARIANT N
evidence: runs/s1-s11, runs/t-*, runs/stuck1-xorg-grabinfo.txt
root_cause: >-
  decorations/DecorationsEdge.cpp Edge::ButtonDownEvent releases the X
  pointer and keyboard grab with raw Xlib calls whenever it is pressed, and
  +unity10 stops that only for compiz's resize and move grabs; expo (and any
  other compiz grab) is still ungrabbed behind compiz's back.
root_cause_mechanism: >-
  compiz grabs with owner_events so a press on its own border input window is
  still reported there; UnityScreen::handleEvent passes it to
  HandleFrameEvent (no expo filter) -> Edge::ButtonDownEvent -> XUngrabPointer
  / XUngrabKeyboard (traced) while expo stays listed. Expo ends on the button
  release; once Edge has dropped the grab, where the release goes depends on
  the window arrangement, and in the replayed state compiz receives none
  (traced: press seen by Unity and expo, no release). Expo then stays listed
  without an X grab; compiz thaws the frames' synchronous passive grabs only
  with an empty grab list (event.cpp:1369, 1683), so the next frame click
  freezes the pointer.
root_cause_evidence: >-
  runs/s6 (orig 3/3: Edge ungrab, no expo REMOVE-GRAB, X grab list frozen;
  noborder 3/3 clean - these traces have no button-event probes), runs/s8
  (n=1 per variant with button probes: in orig the press is seen by
  UnityScreen::handleEvent and ExpoScreen::handleEvent and no ButtonRelease
  by either; in noborder both see press and release - "no release" means not
  seen by those two handlers), runs/s10 (harmless case: release seen on the
  border's input window), runs/s11 (nolauncher 0/2: without the launcher
  click the check click on the sensor ends the second expo, so the border
  click happens outside expo - the launcher click's role is only to leave
  expo open), runs/stuck1-xorg-grabinfo.txt, runs/s6/*.grabinfo. The control
  changes where the press lands (compiz's grab window instead of the border's
  input window), so it shows Edge's ungrab is necessary; the A2 build on the
  same replay is the causal test.
invariant: >-
  No in-process component releases an X grab while compiz lists any grab:
  compiz core keeps its grab list and its X grab in step
  (pushGrabGeneric/removeGrab), and each grab ends through removeGrab on its
  owner's terms. (UNITY-20260927-001's general invariant; +unity10 enforced it
  for move/resize only.)
existing_fix_result: NOT_FIXED
existing_fix_evidence: >-
  Investigator subagent 2026-09-29: LP searchTasks on unity, compiz,
  ubuntu/+source/unity, ubuntu/+source/compiz (expo stuck/freeze/pointer/
  click/grab/mouse, workspace switcher, clicks not working, pointer frozen,
  DecorationsEdge, XUngrabPointer; broad expo queries partly listed); LP
  #1393523 open with no branch; all 4704 lp:unity + 1516 lp:compiz MPs;
  gitlab ubuntu-unity/unity (DecorationsEdge.cpp last 997e91d1, 2014;
  DecorationsManager.cpp last 2b3c217c, 2016) and issue-tracker; rmadison
  (resolute = stonking 0ubuntu3, native; Debian no unity); GitHub commit and
  code search; AUR; gentoo-unity7 9aad80df. Only change anywhere: our
  f2268bef (move/resize).
candidate_approaches:
  - "A2: Edge::ButtonDownEvent returns while compiz lists any grab
    (screen->otherGrabExist(nullptr)), replacing the grabExist(resize) ||
    grabExist(move) condition of +unity10. One line changed plus comment."
  - "F: HandleFrameEvent ignores decoration input during expo
    (IsExpoActive, as for scale). Also stops title-bar buttons and menus in
    expo (the other half of LP #1393523) - a behaviour change beyond this
    defect; covers expo only, not wall/unity/ezoom."
  - "B: drop Edge's raw XUngrabPointer/XUngrabKeyboard (rejected in -001:
    changes every first press on every border, unmeasured)."
  - "D: compiz thaws frames' passive grabs regardless of its grab list
    (rejected in -001: hides leaked grabs, changes clicks on frames during
    every grab)."
chosen_approach: A2 - Edge::ButtonDownEvent returns while compiz lists any grab (screen->otherGrabExist(nullptr))
why_chosen: >-
  It is -001's general invariant enforced at the only place that breaks it:
  while any grab is listed, move and resize refuse Edge's
  _NET_WM_MOVERESIZE anyway, so the ungrab is the only effect left and it is
  only harmful. The first border press (no grab listed) is unchanged. The
  title bar's drag-to-move also goes through Edge::ButtonDownEvent - GrabEdge
  calls it on all three paths (DecorationsGrabEdge.cpp:48 immediate, :73
  grab-wait timer, :89 motion) - so a title drag while a grab is listed now
  does nothing either; harmless for the same reason (move refuses while
  another grab is listed, move.cpp:57), and tested. Title-bar buttons and
  menus are not Edge and are unchanged. Covers expo (measured) and wall,
  unity-switcher, unity, ezoom by construction, without naming them.
correct_layer: >-
  Same as UNITY-20260927-001: the decoration Edge runs inside compiz and
  releases compiz's X grab with raw Xlib behind compiz's grab list; compiz's
  own grab list is the authority it must consult. compiz core and expo keep
  their invariants on their own paths.
defensive_workaround_rejected: >-
  F filters by one plugin's state in the event dispatcher and suppresses
  unrelated widget input; D hides leaks in compiz core. A2 changes the
  condition of the existing guard at the violating call.
design_challenger_required: true
architectural_task: true
design_review_result: APPROVE   # review 1: REVISE (card: GrabEdge, n=1 trace, short windows, follow-ups, test plan), review 2: APPROVE
code_risks:
  ownership_lifetime: not_applicable
  callbacks_cancellation: >-
    checked - a border or title-bar (GrabEdge) press during any grab no longer
    ungrabs or sends _NET_WM_MOVERESIZE; move/resize refused it anyway.
    Short windows in which a user's border/title press is now ignored: wall
    while its slide runs (~0.3 s, removed in donePaint) and while Ctrl+Alt is
    still held after a keyboard viewport switch with the switcher shown
    (showPreview cleared in terminate, wall.cpp:757/769); expo during its
    zoom-out after leaving (REMOVE-GRAB 260 ms after the release, runs/s8);
    unity-switcher while Alt+Tab is open; ezoom while a zoom box is drawn;
    unity while a touch drag runs. A leaked grab would now leave borders dead
    instead of freezing the pointer - input is broken either way.
  threading_reentrancy: not_applicable - compiz main thread only
  ABI_API_file_list: not_applicable - one condition in a .cpp
unknowns:
  - "Gesture grab 'unity' not measurable on target (no touch device); covered by construction."
  - "Where exactly the release goes after Edge's ungrab in the replayed state (which window) - not traced; the fix removes the dependency."
  - "wall, ezoom: not measured."
  - "Title-bar buttons and menus still react in expo (rest of LP #1393523; option F) - out of scope, follow-up proposed (ID from C)."
  - "unity-shared XWindowManager::UnGrabMousePointer (raw ungrab; PanelIndicatorEntryView.cpp:151, PanelMenuView.cpp:1478, StartMove): nux gets events only when no grab other than deco/move/switcher/resize is listed (unityshell.cpp:2119), so not during expo/wall/ezoom, but possibly during move/resize - unmeasured, follow-up proposed (ID from C)."
  - "Real hardware not tested."
test_plan: >-
  One boot; compiz restarted after installing the build and checked for no
  "(deleted)" in /proc/PID/maps; versions recorded. (1) replay orig
  (regression): pass = EDGE-DOWN present with no XUngrabPointer/Keyboard from
  HandleFrameEvent, expo REMOVE-GRAB in both phases, X grab list empty with
  nothing frozen, then a click on the sensor that reaches it (the 0,207
  launcher click proves nothing either way); noborder unchanged. (2) expo
  series expo-border, expo-altf8-border, expo-dnd-border and the s10 variant:
  0 ungrabs, expo still ends on the click, Escape still leaves expo after a
  border press. (3) title bar: non-maximizable window immediate drag moves;
  maximizable window press-and-hold (timer) and press-and-move (motion) move;
  double-click still maximizes; title drag in expo: no ungrab. (4) first
  border press right after a wall slide ends and right after expo closes
  (after the traced REMOVE-GRAB) resizes. (5) keyboard move/resize series
  (s9) unchanged. (6) UNITY-20260927-001's #3 regression set: rmbslow, rmb,
  rmb2, wheel, mid, plain and the title variants - 0 stuck, resize/move still
  working.
```

## Design review

Temporary Design Challenger, separate read-only subagent.

1. **REVISE**: design and layer supported, card and tests not. The control
   changes where the press lands as well, so it shows necessity, and the A2
   build on the same replay is the causal test; the release trace is n=1;
   `GrabEdge` (title-bar drag) also goes through `Edge::ButtonDownEvent` and
   was missing; the short windows in which A2 ignores a press were not
   listed; follow-ups for the rest of LP #1393523 and for the panel's
   `UnGrabMousePointer` needed; test plan (launcher-independent pass
   criteria, title bar paths, first press after a grab ends, one boot) was
   missing. Led to `runs/s11` and the card fields above.
2. **APPROVE**.

## Outcome (so far)

`VERIFYING`: the fix (A2, unity `+unity12`, `7b0eca27`) has an approved
build manifest from the gated release build, which is content-identical to
the tested build and passes the regression test and the plan sample on
target (section 8). Next: the independent Verifier, then the publication gate.

Follow-ups proposed (IDs from C): the rest of LP #1393523 (title-bar buttons
and menus react in expo, option F); `XWindowManager::UnGrabMousePointer`
(panel) under move/resize; cinnamon-session SEGV in `IceProcessMessages`
after a compiz restart.
