# Known issue #3: the cursor stops responding

Release-note workaround: `killall -1 compiz` (SIGHUP - compiz restarts).

## What is known

- Symptom, from the release notes (host session, 2026-09-24): the pointer
  **moves but does not click anything**; the notes call it a compiz problem.
  After the workaround, windows from every workspace may land on the first one
  - a separate bug in itself.
- No user reports from 2024-2026 anywhere (forums, Reddit, Ask Ubuntu,
  Discourse, Launchpad). The only compiz bug on Launchpad since 2024 is
  #2059368 "Dota2", empty.
- LP #760769 (Unity, 11.04, Critical, last comment 2015): same symptom, with
  Alt+Tab, screen blanking/lid, LibreOffice, memory pressure and some compiz
  plugins named as preceding it, on Intel, NVIDIA and ATI alike. Same symptom
  is not the same cause - a list of places to look, nothing more.

## Working hypothesis

A pointer that moves but whose clicks reach nothing is what an **active
pointer grab** that nobody releases looks like: every button event goes to the
grabbing client. A compiz restart drops its grabs, which fits the workaround.

To test it we need a sensor - see `grab-probe` below - and a way to make the
grab stick.

## Measured 2026-09-24 - not reproduced

On `target` with unity `+unity5`, compiz `+unity1`, cinnamon-session `+unity2`,
unity-settings-daemon `0ubuntu7+unity1`, archive nux `0ubuntu12`:

- `grab-stress.sh 400 7` ([`runs/grab-stress-400.log`](runs/grab-stress-400.log)):
  400 random actions - Dash, HUD, Alt+Tab, Spread, Expo, end-session dialog,
  session menu, window drag, and overlapping pairs - **no stuck grab**. The
  43 grabs the probe saw were an open menu or dialog that our Escape had
  arrived too early for; the next Escape released each.
- `lock-stress.sh 60` ([`runs/lock-stress-60.log`](runs/lock-stress-60.log)):
  60 lock/unlock cycles - by keys, by logind, from an open Dash, from an open
  HUD - unlocked through `loginctl unlock-session`. Locked: grabbed, as it
  should be. Unlocked: free, every time.

Limits of this: xdotool drives input through XTEST, not a real device;
unlocking went through logind, not the password path; no suspend, no screen
blanking, no memory pressure, no LibreOffice (all named in LP #760769). #3
stays open. `grab-probe` is the sensor to run the moment someone sees it:
`GRABBED` with nothing on screen would confirm a stuck grab, and
`setxkbmap -option grab:debug` then `XF86LogGrabInfo` names the client.

**Side bug from the release notes, not tested:** windows landing on the first
workspace after `killall -1 compiz`. Workspaces are 1x1 by default (`hsize`,
`vsize` = 1, `_NET_DESKTOP_GEOMETRY` 1280x800); setting `hsize` to 2 through
gsettings did not change the desktop geometry live, and the attempt was
time-boxed. Needs workspaces enabled the way a user enables them (Settings).

## Reproduced and fixed (2026-09-26, agent A)

**Status: reproduced (right button during a border resize: 8 of 10 on unity
+unity9), cause found, fixed in unity `+unity10` (0 of 50), in aptly.**

### Rule 0

gitlab ubuntu-unity/issue-tracker #165 "Cursor sometimes stops responding"
(2026-04-09, 26.04 + Regression, open, no comments, no trigger given); its
workaround implies the keyboard still works. Launchpad has the trigger, never
diagnosed: **LP #1885435** (compiz+unity, 16.04, "100% reproducible": drag a
border, press and hold the right button, release both, click elsewhere -
buttons dead, keyboard fine) and **LP #1644412** (unity 16.04: wheel during a
corner resize, then clicks dead, Super dead). No fix anywhere (lp:compiz master
unchanged since 2025-09-30, gitlab unity, AUR, Gentoo overlay).

### How it was measured

Real devices only, as for #1: the USB tablet's evdev node places the pointer
(absolute), the PS/2 mouse's node presses, drags, adds buttons and the wheel
(`tools/evclick.py`, `tools/evseq.py`), nodes found by name. `tools/clicksensor.py`
is a window that logs every press it receives; `tools/clickcheck.sh` clicks it
with the tablet and runs `grab-probe`. `tools/resize-grab.sh VARIANT` puts the
pointer on an xterm's right border and plays the variant; `tools/resize-series.sh`
repeats it from a clean state, dumps `XF86LogGrabInfo` when stuck and recovers
with the release notes' `killall -1 compiz`.

### Numbers (`runs/resize-unity9.log`, `runs/resize-unity10.log`)

| Variant during a left-button border drag | unity +unity9 stuck | +unity10 stuck | +unity10 resized |
|---|---|---|---|
| plain drag | 0/10 | 0/10 | 10/10 |
| right button, released before the left (`rmb`) | **8/10** | 0/10 | 10/10 |
| right button, released after the left (`rmb2`) | **7/10** | 0/10 | 10/10 |
| wheel up/down (`wheel`) | **1/10** | 0/10 | 10/10 |
| middle button (`mid`) | 0/10 | 0/10 | 10/10 |

"Stuck" = the next real click on the sensor never arrives, pointer grabbed,
keyboard free - the release notes' symptom; all 16 stuck states were cleared by
`killall -1 compiz`. Every one looked the same in the server's grab dump:
`Active grab ... client pid <compiz> ... (from passive grab) (device frozen,
state 6) passive grab type 4, detail 0x0`.

### Cause

1. A left-button press on a window edge reaches Unity's decorations
   (`DecorationsEdge.cpp`, `Edge::ButtonDownEvent`), which ungrabs the pointer
   and sends `_NET_WM_MOVERESIZE`; compiz's resize plugin starts and pushes its
   grab `"resize"`.
2. **Any other button pressed on the edge meanwhile goes through
   `Edge::ButtonDownEvent` again**: `XUngrabPointer` takes the X grab away from
   the running resize and a second `_NET_WM_MOVERESIZE` arrives, which the
   plugin (already resizing) accepts without grabbing again. The button
   releases no longer reach compiz, `terminateResize` never runs, and `"resize"`
   stays in compiz's grab list - with the X pointer free. Measured with gdb on
   compiz right after `rmb`: grab list `{"resize"}`, `grab-probe` free; after a
   plain drag: empty.
3. Window frames of inactive windows carry compiz's synchronous passive
   AnyButton grab (click-to-focus); compiz thaws it with `XAllowEvents` only
   when its grab list is empty (`src/event.cpp`). With `"resize"` leaked, the
   **next click on such a frame freezes the pointer** for good: it moves, clicks
   go nowhere, the keyboard works. `killall -1 compiz` empties the list.

### Fix - unity `7.7.1+26.04.20260306-0ubuntu3+unity10`

`DecorationsEdge: don't start a move or resize while one is running` - return
from `Edge::ButtonDownEvent` while compiz holds a `"resize"` or `"move"` grab.
The running resize keeps its grab and ends on its own button, as for a plain
drag. Not done, possible hardening in compiz: thaw a frame's synchronous grab
(`AsyncPointer`) even when the grab list is not empty, so that no leaked
plugin grab can freeze clicks.

### The #1-related hypothesis (coordinator): not confirmed

`runs/midsession-unity9.log`, 3 rounds, each followed by a real click: restart of
unity-settings-daemon, org.gnome.Mutter.IdleMonitor taken away and returned,
DPMS off woken by real motion, lock + unlock (logind; grabbed while locked,
free after). Plus once each: switch user to a second account and back (clicks
reach after the VT returns), suspend (s2idle) and resume. Clicks reached every
time. The idle monitor only drives idle watches, not event delivery.

Not tested / not shown: a move by the title bar with a second button - the
driver's title-bar position did not move the window (`runs/title-unity9.log`),
so that path is untested, not clean; real hardware.
