# Agent A - running state

Test desktop: `target` (192.168.56.20, VM `target-desktop`, snapshot `Clean-updated-2026-09-23`)
Build directory: `~/work/a`

## Now (2026-09-29, end of session - May recreates the sessions)

Nothing in flight; no new work to start. My open tasks on the board
(`~/coordinator/TASKS.md`, evidence in `~/coordinator/evidence/<id>.json`):

- **UNITY-20260928-022** (u-s-d power: registrations outliving `stop()`) -
  BLOCKED on the aptly freeze, resume_state REVIEW. Verifier round 2 PASS on
  `0ubuntu7+unity9` (round 1 FAIL on +unity8, fixed). Card:
  `docs/research/UNITY-20260928-022-usd-power-registrations/README.md`
  (branch `a/UNITY-20260928-022` of this repo, not merged yet). Package:
  Ubuntu-Unity-LifeSupport/unity-settings-daemon branch
  `a/UNITY-20260928-022` at `57945f5` = +unity7 `b570a22` + `27e75f4` +
  `df68430` (+unity8 `41fd7eb` superseded, never published). +unity9 debs:
  `docs/research/UNITY-20260928-022-usd-power-registrations/build-unity9/`
  in worktree `~/work/a/unity-distro` (gitignored; manifest committed).
  Package source worktree: `~/work/a/022-usd/pkg`; GitHub clone used for
  pushes: `~/work/a/012-usd/gh`.
- **UNITY-20260927-012** (u-s-d libcolor/power shared-proxy UAF) and
  **UNITY-20260927-052** (u-s-d xsync UAF) - BLOCKED on the freeze, resume
  REVIEW. Coordinator's order: one publication of u-s-d `+unity7`
  (`b570a22`, contains 052 and 012) closes both. +unity9 contains +unity7
  plus 022; whether +unity9 is published instead is the coordinator's call.
  +unity7 debs: `docs/research/UNITY-20260927-012-usd-color-restart-crash/build/`
  in worktree `~/work/a/unity-distro` (untracked files).
- **UNITY-20260928-008** (unity-gtk4-menu security check) - BLOCKED, stays as
  it is; do not reproduce its analysis.

Follow-ups proposed to the coordinator from 022 (not on the board by me):
idle handling (dim/blank/sleep on inactivity) never runs under
cinnamon-session because it does not export `SessionIsActive` - and making it
run requires removing the idle watches in `stop()` in the same change;
disconnect the logind `g-signal` handler before dropping `logind_proxy` (R1,
not reproduced); `stop()` before `on_bus_gotten` leaves Power unregistered
until restart.

## State of `target` (2026-09-29 04:24Z boot)

u-s-d back to aptly after 022: `unity-settings-daemon`,
`libunity-settings-daemon1`, `-schemas` `0ubuntu7+unity5` from our aptly; no
dbgsym packages installed (`dpkg -l | grep -c dbgsym` = 0); the test drop-in
`zz-u012-perturb.conf`, the test scripts in `~` and `/var/crash` cleared;
rebooted, fresh u-s-d (no deleted maps). Not a snapshot restore: `~/.dirty`
is still present (it was before 022 too). Archive updates pending
(`software-properties` 0.120.1), not ours, left alone. The rest as recorded
below.

## Earlier record of `target` (2026-09-26/27, kept as written)


Since 2026-09-24 13:11 boot (full upgrade from our aptly), plus by `dpkg -i`
then matched by aptly: unity `+unity10` (2026-09-26), compiz `+unity2`, gtk-nocsd `4.8-1+unity1`
(dbgsyms for them installed too); xorg-server `2:21.1.22-1ubuntu1.3+unity1` (matched by aptly); unity-settings-daemon `0ubuntu7+unity4` (dpkg -i, matched by aptly; dbgsym removed, test divert removed); `~/evinject.py`, `~/evabs.py`, `~/steal-idle.py`, `~/repro1.sh`, `~/cursor-loop.sh` and results in `~/cur/`, rebooted 2026-09-25 ~20:30Z; see `research/xorg-versioning/`. Workspaces 2x2, six terminals spread over
them. Also installed: libxpathselect1.4v5 (Unity introspection),
libunity-gtk4-menu0 0.8, gnome-characters, gnome-text-editor,
gnome-sound-recorder, google-chrome-stable 154 (adds `google-chrome.sources`); xdotool, gdb,
test scripts in `~`; unity-session `49.4+unity1`. Clock was 1 h 07 min behind, set from builder at 17:26Z
- not synchronised, check after a host sleep. `~/.dirty` present.

Correction 2026-09-27 (UNITY-20260927-036): `libunity-gtk4-menu0 0.8` in the
list above is no longer installed on target -
`ssh target dpkg-query -W libunity-gtk4-menu0` on 2026-09-27 reports no such
package (checked again today). The line above is kept as written.

## Mine in `packages/`

- `packages/unity` - branches `unity/resolute` (released `+unity9`),
  `mr/stale-pending-action` (worktree `/var/tmp/sbuild-claude/unity-mr`),
  `exp/option-b-request-shutdown` (rejected experiment).
- `packages/cinnamon-session` - gbp repository, branch `unity/resolute`
  (`6.4.2-1+unity3`), https://github.com/Ubuntu-Unity-LifeSupport/cinnamon-session.
- `packages/unity` branch `wip/confirm-inhibitors` (worktree `~/work/a/unity`),
  `+unity3` (not published) and `+unity4`.
- `packages/compiz` - branch `unity/resolute` (`+unity2`), https://github.com/Ubuntu-Unity-LifeSupport/compiz.
- `packages/unity` - `unity/resolute` at `+unity8` (tag), built from worktree
  `~/work/a/unity` branch `fix/compiz-teardown` (merged).
- `packages/lightdm` - gbp, branch `unity/resolute` (`1.32.0-6ubuntu4+unity1`), https://github.com/Ubuntu-Unity-LifeSupport/lightdm.
- `packages/unity-session` - branch `unity/resolute` (`49.4+unity1`), https://github.com/Ubuntu-Unity-LifeSupport/unity-session.
- (`packages/gtk-nocsd` handed to agent B, 2026-09-26.)
- `packages/unity-settings-daemon` - branch `unity/resolute` (`0ubuntu7+unity4`, worktree `~/work/a/usd`, based on the unreleased git head 216f054), https://github.com/Ubuntu-Unity-LifeSupport/unity-settings-daemon. Its `origin` is upstream GitLab: push task branches from `~/work/a/012-usd/gh` (origin = GitHub). Task branches there: `a/UNITY-20260927-052` (`f674b6b`, 052's fix), `a/UNITY-20260927-012` (+unity7 `b570a22`), `a/UNITY-20260928-022` (+unity9 `57945f5`).
- `packages/unity-greeter` - branch `unity/resolute` (`25.04.1-0ubuntu1+unity1`, native), https://github.com/Ubuntu-Unity-LifeSupport/unity-greeter.
- `packages/unity-control-center` - branch `unity/resolute` (`0ubuntu13+unity2`), https://github.com/Ubuntu-Unity-LifeSupport/unity-control-center.
- `packages/session-migration` - branch `unity/resolute` (`0.3.9build2+unity1`), https://github.com/Ubuntu-Unity-LifeSupport/session-migration.
