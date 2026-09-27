# UNITY-20260927-001: is the +unity10 early return in `Edge::ButtonDownEvent` the right fix for #3?

Revalidation of legacy item A-L06 (`docs/research/legacy-migration-20260927/A.md`):
unity `+unity10` fixed known issue #3 with an early return. Under the current
process an early return needs its mechanism, invariant and layer shown, and a
Design Challenger review. This record re-measures the bug on the unpatched and
patched builds on 2026-09-27, traces the mechanism without perturbing it, and
weighs the layers. Agent A, target `target-desktop`.

## Evidence card

```yaml
task_id: UNITY-20260927-001
package: unity
target_series: resolute
issue: >-
  Ubuntu Unity 26.04 known issue #3 "pointer moves, clicks nothing";
  gitlab ubuntu-unity/issue-tracker #165; LP: #1885435, LP: #1644412
status: REPRODUCED
issue_search_result: FOUND
source_version: >-
  7.7.1+26.04.20260306-0ubuntu3+unity9 (unpatched), +unity10 (patch f2268bef),
  +unity11 (published, contains the patch)
binary_version: >-
  measured: unity/libunity-core-6.0-9/unity-schemas/unity-services/unity-uwidgets
  +unity9 and +unity10 from our aptly; target left on +unity11
source_commit: >-
  patch f2268bef33bb98b503f98dc1aab550d0a635c271 on unity/resolute;
  +unity9 = 8bb626d58fc11a08af70e13ef20bb6a190e32be5, +unity10 =
  fde810ec73a72f06ff24d323b75b2fe92a43244a (the two differ only by f2268bef);
  published branch head 2040279dadc253e76daad4ac2e1ffacc7a2d1e74 (+unity11)
observed: >-
  unity +unity9, compiz 1:0.9.14.2+25.10.20250930-0ubuntu3+unity2: during a
  left-button drag of a window's right border, another button pressed on the
  border (right, or the wheel) leaves the pointer so that the next real click
  on an inactive window's frame never arrives - the pointer moves, clicks go
  nowhere, the keyboard works - until `killall -1 compiz`. X server grab dump
  in every stuck case: active grab by compiz, "(from passive grab) (device
  frozen, state 6) passive grab type 4, detail 0x0".
expected: >-
  The border drag ends on the release of the button that started it, compiz
  holds no grab afterwards, and the next click reaches its window.
reproduction: >-
  tools/resize-series.sh VARIANT 10 on target (tools/resize-grab.sh plays the
  variant with real evdev devices: the USB tablet places the pointer on the
  xterm's right border, the PS/2 mouse presses/drags/adds buttons;
  tools/clickcheck.sh clicks a sensor window with the tablet). Deterministic
  variant: rmbslow = left down, move 20 px, 1.5 s, right down, 1.5 s, move
  80,30, right up, left up.
reproduction_result: PASS
evidence: >-
  runs/series-unity9.log, runs/series-unity10.log (same boot 2026-09-26
  20:26:39, same harness), runs/uprobe-rmbslow-unity9-stuck.*,
  runs/uprobe-rmbslow-unity10.*, runs/gdb-stuck-resize-state-unity9.txt,
  runs/uprobe-switcher-edge-unity9.*; published +unity11 check in
  runs/series-unity11.log
root_cause: >-
  unity decorations/DecorationsEdge.cpp Edge::ButtonDownEvent calls
  XUngrabPointer/XUngrabKeyboard and sends _NET_WM_MOVERESIZE for every button
  pressed on a border, also while compiz's resize (or move) plugin is already
  running and holds compiz's pointer grab.
root_cause_mechanism: >-
  (1) Left press on the border: Edge::ButtonDownEvent ungrabs (only the
  press's implicit grab exists) and sends _NET_WM_MOVERESIZE; the resize
  plugin's initiateResize pushes compiz grab "resize", which calls
  XGrabPointer because compiz's grab list was empty. (2) Second button on the
  border while resizing: compiz's active grab reports the press on compiz's
  own border input window, so it reaches Edge::ButtonDownEvent again, whose
  raw XUngrabPointer releases the X pointer grab that compiz core still lists
  as "resize". The second _NET_WM_MOVERESIZE is refused by initiateResize
  (this->w already set): no grab push, no XGrabPointer, releaseButton stays 1.
  (3) With no X grab, the left release goes to another client, so
  terminateResize never runs and "resize" stays in compiz's grab list.
  (4) compiz thaws the synchronous passive AnyButton grab on inactive frames
  (XAllowEvents AsyncPointer/ReplayPointer, src/event.cpp:1370, 1684) only
  when its grab list is empty, so the next click on such a frame freezes the
  pointer device.
root_cause_evidence: >-
  uprobes (bpftrace, no process stop) on +unity9 in a stuck run: EDGE-DOWN
  button=1 -> XUngrabPointer from HandleFrameEvent(Edge inlined) ->
  RESIZE-INITIATE -> PUSH-POINTER-GRAB resize -> XGrabPointer; 1.6 s later
  EDGE-DOWN button=3 -> XUngrabPointer from Edge -> RESIZE-INITIATE with no
  push and no XGrabPointer; no terminate, no removeGrab. gdb attached after
  the freeze: releaseButton=1, w set, grabIndex->name "resize". Same trace on
  +unity10: EDGE-DOWN button=3 with no XUngrabPointer and no initiate, then
  RESIZE-TERMINATE (StateTermButton) -> REMOVE-GRAB -> XUngrabPointer from
  compiz core.
invariant: >-
  While compiz core's grab list holds a pointer grab, the X pointer grab
  belongs to compiz core and is released only by CompScreen::removeGrab
  (src/screen.cpp pushGrabGeneric/removeGrab keep the two in step). A running
  move/resize therefore ends on its own button release.
existing_fix_result: FIXED_LOCAL
existing_fix_evidence: >-
  Only candidate anywhere is our unity f2268bef (+unity10, in aptly, +unity11
  published). Investigator sweep 2026-09-27T17:18Z: LP #1885435/#1644412 New,
  no branches or MPs; 4704 lp:unity + 1516 lp:compiz MPs, gitlab ubuntu-unity,
  GitHub commits, AUR, gentoo-unity7, arch-unity7: nothing; next series
  (stonking) carries the same unity and compiz versions; Debian has no unity
  and only compiz 0.8. Owner validation: +unity9 vs +unity10 A/B below.
candidate_approaches:
  - "A (current, +unity10): Edge::ButtonDownEvent returns while compiz holds a
    'resize' or 'move' grab. Measured: stuck 0/60 vs 31/60 on +unity9, resize
    10/10 in every variant."
  - "A2: same place, condition 'compiz holds any grab' (screen->grabbed()).
    Not built; would also cover grabs of other plugins, none of which was shown
    to reach this path."
  - "B: drop the raw XUngrabPointer/XUngrabKeyboard from Edge::ButtonDownEvent
    (compiz is the same process). Not built."
  - "C: compiz resize ignores a _NET_WM_MOVERESIZE while resizing. Already
    compiz's behaviour (initiateResize returns while this->w is set), measured."
  - "D: compiz core thaws frames' synchronous grabs even with a grab listed.
    Not built."
  - "E: filter ButtonPress for all decoration widgets in
    Manager::Impl::HandleFrameEvent while a move/resize runs. Not built."
chosen_approach: >-
  A - keep the published +unity10 change unchanged; no new package change.
why_chosen: >-
  The code that breaks the invariant is the raw XUngrabPointer in
  Edge::ButtonDownEvent, reached only because Unity's decorations live inside
  compiz and receive events under compiz's own grab. A stops exactly that call
  in exactly the state where it is wrong, by asking compiz's own grab list,
  which is the idiom the move and resize plugins use before initiating
  (move.cpp:57, resize-logic.cpp:1281 otherGrabExist). It leaves the first
  press, the title bar and every other widget untouched. Measured fail before
  and pass after with the same harness on the same boot.
alternatives_rejected:
  - "A2: broadens the change to every compiz grab. The one other grab measured
    (Unity's Alt+Tab 'unity-switcher') never reaches Edge::ButtonDownEvent
    (runs/uprobe-switcher-edge-unity9.*); scale is filtered in
    HandleFrameEvent. No evidence that another grab reaches this path, so the
    wider condition is unproven."
  - "B: changes every first press on every border (the ungrab mimics the EWMH
    client protocol before _NET_WM_MOVERESIZE; INFERENCE, not measured: the first
    press can arrive under compiz's frozen passive frame grab). It would also still send a
    refused second request. Larger and unmeasured on the main path."
  - "C: already true in compiz and not sufficient: the second request is
    refused, the leak comes from the X grab removed before it."
  - "D: masks any leaked plugin grab instead of preventing it and changes how
    clicks on frames behave during every compiz grab (scale, expo, switcher).
    Kept as possible hardening only, not as the fix."
  - "E: also suppresses window buttons, menus and the title bar's
    right-button window menu during a move/resize; the title path was measured
    unaffected on 2026-09-26 (research/recheck-2026-09-26, A-2), so this is
    wider than the defect."
code_risks:
  ownership_lifetime: not_applicable
  callbacks_cancellation: checked
  threading_reentrancy: checked
  ABI_API_file_list: not_applicable
unknowns:
  - "Grabs of other compiz plugins than move, resize, unity-switcher and scale
    (e.g. expo) were not measured on this path."
  - "A mouse click on a border during a keyboard-initiated resize or move
    (Alt+F8/Alt+F7) is covered by the same condition by construction; not
    measured."
  - "The middle button during a border drag did not reproduce on +unity9
    (0/10); why was not traced."
  - "unity-shared XWindowManager::StartMove (panel drag of a maximized window)
    also ungrabs raw before _NET_WM_MOVERESIZE; outside #3, not examined."
  - "Real hardware not tested; VirtualBox evdev devices only."
design_challenger_required: true
design_review_result: PENDING
architectural_task: true
correct_layer: >-
  Unity's decorations (DecorationsEdge.cpp) are the component that violates
  compiz core's grab ownership: they run inside compiz, receive the second
  press through compiz's own active grab, and release that grab with a raw
  Xlib call that bypasses compiz's grab list. compiz core keeps its invariant
  on every path it owns (pushGrabGeneric/removeGrab), and the resize plugin
  already refuses the duplicate request as metacity, marco, mutter, openbox and
  xfwm4 do. So the owner of the broken invariant is the Edge code path, and
  compiz's grab list is the authority it must ask.
defensive_workaround_rejected: >-
  Not a guard at a convenient call site: the early return is at the only place
  that performs the invariant-breaking ungrab, and its condition is the
  invariant's own state (compiz holds a move/resize grab). The convenient
  guards elsewhere - compiz thawing frames regardless (D), filtering all
  decoration input (E) - would hide the leaked grab or suppress unrelated input
  instead of preventing the ungrab.
```

## Measurements (2026-09-27, target-desktop, boot 2026-09-26 20:26:39)

Same harness, same boot, compiz `+unity2` restarted with `SIGHUP` after each
package switch; the mapped `libunityshell.so` inode was checked against the
installed file each time (`LOADED-OK`).

| Variant during a left-button border drag | +unity9 stuck | +unity10 stuck | resized (both) |
|---|---|---|---|
| `rmbslow` (right button, paced) | **10/10** | 0/10 | 10/10 |
| `rmb` (right released before left) | **8/10** | 0/10 | 10/10 |
| `rmb2` (right released after left) | **8/10** | 0/10 | 10/10 |
| `wheel` | **5/10** | 0/10 | 10/10 |
| `mid` | 0/10 | 0/10 | 10/10 |
| `plain` | 0/10 | 0/10 | 10/10 |

Regression scenario: `rmbslow` - fails 10/10 on the unmodified +unity9, passes
10/10 on +unity10.

Published `+unity11` (target's installed version, restored afterwards): `rmbslow`
0/10 stuck, 10/10 resized (`runs/series-unity11.log`).

### Invalid runs, kept for honesty

- gdb breakpoints on `Edge::ButtonDownEvent`, `initiateResize` and
  `XUngrabPointer` (`tools/grabtrace.sh`) stopped compiz long enough that the
  resize never started or the second press missed the border; no stuck run
  could be traced that way. Replaced by uprobes (`tools/uprobetrace.sh`).
- The first +unity10 series ran with GNOME Characters on top of the xterm:
  the Alt+Tab of the switcher test had raised it, and every "drag" landed on
  Characters (xterm stayed 400 px wide, no `EDGE-DOWN` in the trace).
  Discarded; `tools/resize-grab.sh` now activates the xterm before each run
  and the whole series was repeated.

### Correction to the earlier record

`research/cursor-stops/README.md` said the resize plugin accepts the second
request "without grabbing again". It refuses it (`resize-logic.cpp:1281`,
`this->w` set; no second grab push in the trace; `releaseButton` still 1 in the
stuck state). The fix is unaffected: the grab is lost to Unity's ungrab, not
to compiz's acceptance. Corrected in place with a pointer here.

## Tools

`tools/resize-grab.sh`, `tools/resize-series.sh`, `tools/clickcheck.sh`,
`tools/clicksensor.py`, `tools/evclick.py`, `tools/evseq.py`, `tools/envt.sh`
- the #3 harness from `research/cursor-stops/` as used on target (adds
`rmbslow` and the activation of the xterm). `tools/uprobetrace.sh` - bpftrace
uprobes in compiz. `tools/grabtrace.sh` - the gdb variant (perturbs, see
above). `tools/switcher-edge.sh`, `tools/evkeys.py` - border click during
Alt+Tab.
