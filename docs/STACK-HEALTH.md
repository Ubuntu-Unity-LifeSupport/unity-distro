# Stack health

What our Unity 7 session on Ubuntu 26.04 stands on, and how healthy each piece
is outside this project: is upstream alive, what is open against it, did 26.04
break it, are there unfixed CVEs. It exists so May can decide where effort
goes; a dead upstream with nothing open is a useful, low-risk row.

Rules for this file:

- One row per component. A negative result is written like a positive one.
- Every claim has a source (link, or the command that shows it). What was not
  checked is written as "not checked", never guessed.
- Versions are what target runs (host session, 2026-09-24), unless a row says
  otherwise.
- Agent A owns section A, agent B owns section B; each writes only its own.

Columns:

| Column | Meaning |
|---|---|
| Component | source package, and the upstream project if it differs |
| Ours | version on target; `+unityN` = ours from aptly |
| Upstream | last commit and last release, with dates; "dead" if nothing in years |
| Open, important | Launchpad (Ubuntu package): High/Critical, and anything filed since the 26.04 release; upstream tracker if there is one |
| 26.04 regressions | known breakage from the move to 26.04 |
| CVEs | unfixed in 26.04 |
| Risk for us | low / medium / high, one line why |
| Not checked | what is missing from this row |

Checked on: A - pending; B - pending.

## Cross-cutting

| Question | Finding | Source |
|---|---|---|
| Python 3.14 (26.04 moved from 3.12; the ISO ships python3 3.14.3-0ubuntu2) - what of our Python code breaks (unity-tweak-tool, lenses/scopes, indicators in Python) | pending (B) | |
| sudo-rs as `sudo`, password echo on by default - what expects the old behaviour | pending (A) | |
| Xorg in 26.04 - who besides us still ships an X11 session and tests it | pending (A) | |

## A - session core

| Component | Ours | Upstream | Open, important | 26.04 regressions | CVEs | Risk for us | Not checked |
|---|---|---|---|---|---|---|---|

## B - toolkit, indicators, menus, lenses

| Component | Ours | Upstream | Open, important | 26.04 regressions | CVEs | Risk for us | Not checked |
|---|---|---|---|---|---|---|---|
