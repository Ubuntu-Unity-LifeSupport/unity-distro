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
