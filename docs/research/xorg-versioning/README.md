# xorg-server: a version that does not block Ubuntu's own updates (2026-09-25)

Task from May (via the coordinator): with `2:21.1.24-1ubuntu1~26.04.1` in our
aptly, Ubuntu's security updates built on 21.1.22 would not install. Find a
scheme that neither blocks Ubuntu's updates nor moves people back to a
vulnerable build. Agent A.

## What Ubuntu has (2026-09-25)

- resolute: `2:21.1.22-1ubuntu1`; -updates `1ubuntu1.2` (boot_display, 2026-09-23);
  **-proposed `1ubuntu1.3` published 2026-09-25 19:22Z** - DisplayLink/evdi hotplug
  crashes (LP #2160643), **no CVE fixes**. No resolute-security upload at all.
- Ubuntu CVE tracker: all 11 CVEs (CVE-2026-50256..50264, 55999, 56000)
  needs-triage for xorg-server and xwayland in resolute and noble; no USN in
  2026. So **none of the 11 is closed in resolute; all are closed only in ours**.
- Debian fixed xorg-server in trixie (DSA-6371-1, DSA-6497-1), xwayland left
  `<ignored>` ("shouldn't be running as root").
- How Ubuntu fixes xorg-server in a stable release: patches on the existing
  version, never a new point release (noble: USN-7299-1 `21.1.12-1ubuntu1.2`,
  USN-7573-1 `.4`, USN-7846-1 `.5`). So the next resolute security update will
  be `2:21.1.22-1ubuntu1.N`.
- xwayland (resolute 24.1.10, affected by all 11; fixed in 24.1.12/24.1.13,
  26.10 has 24.1.13): **not installed on target**, not part of our X11 session.
  Not touched.

## Candidates built and run

| Version | What it is | Build (clean resolute) | On target |
|---|---|---|---|
| `2:21.1.24-1ubuntu1~26.04.1` | published now; 26.10-proposed rebuilt | ok, 314 s | ok (DECISIONS 2026-09-25) |
| `2:21.1.22-1ubuntu1.2+unity1` | -updates + 29 upstream commits 21.1.22..21.1.24 (release and XQuartz commits left out) | ok, 292 s | reboot, smoke test clean |
| `2:21.1.22-1ubuntu1.3+unity1` | -proposed 1.3 + the same 29 commits | ok, 265 s | reboot, smoke test, 3 logout/login cycles, no crash files |

The 29 commits apply in order with no fuzz on both bases
(`debian/patches/upstream-21.1.24/`). The CVE fixes among them are the ones
listed in `research/release-recheck-a/`. Smoke test: `~/xorg-smoke.sh` on
target (Dash, HUD, spread, workspaces, xkb switch, GLX, window move).

## What apt picks - measured

`apt-candidate.sh` on target: real Ubuntu lists, our repo replaced by a
metadata-only repo per scenario, phased updates included, isolated apt state.
`u13` = the real 1ubuntu1.3 version; `u14` = a hypothetical next upload;
`u24` = a hypothetical `2:21.1.24-0ubuntu0.26.04.1`.

| Installed | Our aptly offers | Ubuntu offers | apt picks |
|---|---|---|---|
| stock 1ubuntu1 | 21.1.24~26.04.1 | 1.2 / +1.3 / +21.1.24-0ubuntu0 | **ours, always** - even over a 21.1.24-based Ubuntu fix |
| stock | 1.2+unity1 | 1.2 | ours |
| stock | 1.2+unity1 | **1.3 (real, no CVE fixes)** | **1.3 - back to vulnerable** |
| stock | 1.3+unity1 | 1.3 | ours |
| stock | 1.3+unity1 | 1.4 | 1.4 (Ubuntu's) |
| stock | 1.3+unity1 | 21.1.24-0ubuntu0 | Ubuntu's |
| 21.1.24~26.04.1 | any 21.1.22+unity | any 21.1.22-based | **stays on 21.1.24~** - apt never downgrades |

## Conclusion (recommendation, not applied: aptly unchanged)

- **Current scheme blocks every Ubuntu upload**, including a hypothetical
  21.1.24-based security fix. Its failure mode is *worse than stock Ubuntu*.
- **Pinning cannot fix it** from our side: apt (priority < 1000) never replaces
  an installed higher version with a lower one, whatever the pin.
- **Rebasing our patches onto Ubuntu's version and suffixing `+unity1`** makes
  any later Ubuntu upload win. Its failure mode is *stock Ubuntu*: a later
  Ubuntu upload without the CVE fixes takes them away. That is exactly what
  `1.2+unity1` would do this week (1.3 is in -proposed now), so the base must
  be the **newest resolute upload, proposed included: `1ubuntu1.3+unity1`**.
- The price is a watch: every new resolute xorg-server (`watch.sh` prints it)
  means rebasing the 29 commits and publishing `…N+unity1` before it leaves
  -proposed (about a week for SRUs; security uploads skip -proposed, but
  those would be the ones carrying the fixes).
- Migration: machines that already have `21.1.24~26.04.1` need an explicit
  downgrade once (done on target with `dpkg -i`; apt:
  `apt install xserver-xorg-core=2:21.1.22-1ubuntu1.3+unity1 xserver-common=… xserver-xorg-legacy=…`),
  then a reboot. Our aptly users are target and possibly target2.
