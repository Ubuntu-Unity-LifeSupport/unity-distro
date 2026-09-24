# grab-probe, grab-stress

Tools for known issue #3 (the pointer moves but clicks reach nothing).

- `grab-probe` tries to grab the pointer and the keyboard on the root window
  and lets go at once. `GRABBED` means another client holds an active grab.
  Checked on target: Unity's end-session dialog shows `GRABBED` while open and
  `free` after Escape; the Dash does not grab.
- `grab-stress.sh N [SEED]` drives Unity through N random actions (Dash, HUD,
  Alt+Tab, Spread, Expo, end-session dialog, session menu, window drag, and
  overlapping combinations) with xdotool, probing after each. A grab that
  survives two Escapes counts as stuck; the script then logs the X server's
  grab info (`XF86LogGrabInfo`) and takes a screenshot.

Build `grab-probe` in any chroot with `libx11-dev`:
`cc -O2 -Wall -o grab-probe grab-probe.c -lX11`. Copy both to target.
