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
