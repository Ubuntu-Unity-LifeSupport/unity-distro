# UNITY-20260927-021: calamares-settings-ubuntu, restore debian/changelog and revalidate known issue #4

Owner: agent B; VMs `oem-test` (assigned) and `target-desktop-2`. Legacy item
B-L07 (`docs/research/legacy-migration-20260927/B.md`). The original
investigation of known issue #4 is `docs/research/calamares-oem/`.

```yaml
task_id: UNITY-20260927-021
package: calamares-settings-ubuntu
target_series: resolute
issue: >
  (a) packaging defect of ours: the published 1:26.04.12+unity1 replaced the
  whole debian/changelog (1491 lines of archive history) with an 11-line file;
  the calamares-settings-ubuntu-unity .deb ships a changelog with one entry.
  (b) known issue #4 of the 26.04 release notes ("the wallpaper has the
  tendency to appear over the Calamares (installer) window when performing
  OEM installation"): the +unity1 fix is carried unchanged and revalidated.
status: REPRODUCED
issue_search_result: NOT_FOUND  # no tracker report for #4; search/FINDINGS.md
source_version: 1:26.04.12+unity1 (published), base 1:26.04.12 (resolute)
binary_version: calamares-settings-ubuntu-unity 1:26.04.12+unity1 (aptly)
source_commit: b6b546b1726812d354bdd4ccb35e0c500add2624  # +unity1, base c6997017d2fe72221f91a22646acab3e8caab608
observed: >
  (a) git show --stat b6b546b: debian/changelog | 1496 +---; the file went from
  1491 lines (c699701) to 11. (b) With the archive basicwallpaper the
  wallpaper covers Calamares after Alt+Tab (3/3), when it maps 15 s after
  Calamares (3/3) and at session start in 1 of 3 (logs/01-rt-archive.txt).
expected: >
  (a) debian/changelog keeps the archive history with our entries on top.
  (b) The wallpaper never stacks above Calamares in the OEM end-user session.
reproduction: see Reproduction (rt.sh in the b-dev chroot; the cold-boot runs
  on oem-test in docs/research/calamares-oem/)
evidence: logs/, docs/research/calamares-oem/README.md
root_cause: >
  (a) commit b6b546b rewrote debian/changelog instead of prepending an entry.
  (b) common/basicwallpaper/main.cpp maps the wallpaper with
  setWindowFlags(Qt::WindowStaysOnBottomHint) + showFullScreen(): a NORMAL
  window with _NET_WM_STATE_FULLSCREEN that accepts focus; xfwm4 4.20 puts a
  focused fullscreen window into its fullscreen layer, above normal windows,
  so whenever the wallpaper has focus it covers Calamares.
root_cause_mechanism: >
  (b) xprop of the archive wallpaper: _NET_WM_WINDOW_TYPE_NORMAL,
  _NET_WM_STATE_FULLSCREEN (logs/01-rt-archive.txt); on the real cold first
  boot the wallpaper maps first and takes focus, Calamares maps ~13 s later
  without focus (calamares-oem/README.md "Cold first boot", 3/3 archive runs).
root_cause_evidence: docs/research/UNITY-20260927-021-calamares-oem-wallpaper/logs/01-rt-archive.txt
invariant: >
  (a) debian/changelog of our upload = the target-series archive changelog
  with our entries prepended. (b) In the OEM end-user session the wallpaper
  is below every application window and never takes focus; Calamares stays
  visible regardless of map order or Alt+Tab.
existing_fix_result: NOT_FIXED  # (a): nowhere; (b): only our b6b546b, see search/FINDINGS.md
candidate_approaches:
  - (a) new commit restoring the archive changelog under our entries - one
    file, no code change
  - (b1) keep b6b546b's window type change (desktop window, no focus, X11 only)
  - (b2) reorder/delay start-ubuntu-unity-oem-env - rejected in
    DECISIONS 2026-09-24 ("fix basicwallpaper, not the session script"):
    Alt+Tab still raises a focusable fullscreen window
  - (b3) configure xfwm4 in the OEM session - rejected: changes the window
    manager for the whole session to hide one program's wrong window type
chosen_approach: (a) restore debian/changelog; (b1) carry the fix unchanged
why_chosen: >
  (b1) the wallpaper is a desktop background; declaring it
  _NET_WM_WINDOW_TYPE_DESKTOP without focus is what the EWMH offers for it,
  and it fixes all three measured cases (logs/02-rt-unity1.txt).
alternatives_rejected:
  - (b2) and (b3) above
code_risks:
  ownership_lifetime: not_applicable
  callbacks_cancellation: not_applicable
  threading_reentrancy: not_applicable
  ABI_API_file_list: checked  # file lists compared after the build
design_challenger_required: false
design_review_result: NOT_REQUIRED
architectural_task: false
correct_layer: >
  The wallpaper program decides its own window type and focus policy; the
  defect is that it declares a focusable fullscreen application window. The
  session script and the window manager behave as specified.
defensive_workaround_rejected: >
  Ordering or delays in the session script only move the race; they do not
  remove a focusable fullscreen window from Alt+Tab.
unknowns:
  - Lubuntu (openbox, same binary) is plausibly affected; not measured
  - no keyboard focus in Calamares on a cold boot with the fix (xfwm4
    _NET_WM_USER_TIME hypothesis) - separate finding, not this patch
```

## Reproduction

`rt.sh DEB [ROUNDS]` runs in the builder's `b-dev` chroot
(`/var/tmp/sbuild-claude/b-dev`: Xvfb 21.1.22, xfwm4 4.20.0-1build1,
Calamares 3.3.14-0ubuntu25.26.04.1, ImageMagick, xdotool) through
`run-rt.sh`, which gives it its own mount and pid namespace. It unpacks the
`oemconfig.tar.gz` of the given `calamares-settings-ubuntu-unity` `.deb`,
builds the Calamares configuration the OEM session sees (installed
`/etc/calamares` with the oemconfig's `etc/calamares` over it, `qml` from
`/usr/share/calamares`), and runs the session in the order of
`start-ubuntu-unity-oem-env`. The pixel at 700,200 tells Calamares
(`#EFEFEF`) from the wallpaper (`#464625`); each round also checks that a
Calamares window is visible, so a Calamares that fails to start cannot pass.

A first version passed `-c` the bare oemconfig directory; Calamares refused
to start without `qml/`, and the pixel always showed the wallpaper. That
run is discarded; the fixed script records the visible Calamares window.

| deb | basicwallpaper sha256 | session start | Alt+Tab (1st, 2nd) | wallpaper 15 s late |
|---|---|---|---|---|
| archive 1:26.04.12 | `cdd40699dae079fb…` | wallpaper 1/3 | wallpaper 3/3, Calamares 3/3 | wallpaper 3/3 |
| +unity1 | `2cd8d1f514970e5e…` | Calamares 3/3 | Calamares 3/3, 3/3 | Calamares 3/3 |

(`logs/01-rt-archive.txt`, `logs/02-rt-unity1.txt`.)

## Implementation

Plan, recorded before the code change:

1. In `packages/calamares-settings-ubuntu` (worktree of the Launchpad clone,
   branch `b/UNITY-20260927-021` from `b6b546b`), one commit that sets
   `debian/changelog` to the archive's file at `c699701` with the existing
   `+unity1` entry and a new `1:26.04.12+unity2` entry on top. No code
   change: `common/basicwallpaper/main.cpp` stays as in `b6b546b`.
2. Check: `git diff c699701 HEAD --stat` touches exactly
   `common/basicwallpaper/main.cpp` and `debian/changelog`, and the changelog
   diff only adds the two entries at the top.
3. Build with `scripts/build_sbuild.py` in resolute; compare file lists
   against the archive and `+unity1`; check that the built `.deb`s' changelog
   carries the full history.
4. Regression: `rt.sh` on the `+unity2` `.deb` (must behave as `+unity1`;
   the archive `.deb` fails).
5. Independent review (`adversarial-verifier`), release gate, publication,
   then the target check on `oem-test` through the path the fix really takes
   (live ISO session → our aptly → vendor install → OEM preparation → cold
   first boot).

## Preliminary results (before the gated build)

Change: commit `c03daf4e` on `b/UNITY-20260927-021` (packages clone, not yet
pushed: the clone has no remote of ours). Against the archive (`c699701`) the
source differs in exactly `common/basicwallpaper/main.cpp` (the #4 fix,
unchanged since `b6b546b`) and 19 added lines at the top of
`debian/changelog`; no archive changelog line is removed (182 entries).

sbuild resolute: `Status: successful`, but `scripts/build_sbuild.py` exited
2 without a manifest. It matches artifacts against the version with its
epoch (`1:26.04.12+unity2`), which never appears in file names. The build
has to be repeated through the fixed script before the gate; the results
below are preliminary evidence from that sbuild output.

- Changelog shipped in `calamares-settings-ubuntu-unity`: +unity1 had 1
  entry; +unity2 has 95. `dh_installchangelogs` trims old entries by design
  ("Older entries have been removed from this changelog"); the archive's
  `-common` ships 93, so ours is the archive's 93 plus our two
  (`logs/04-changelog-entries.txt`).
- File list of `calamares-settings-ubuntu-unity` equals the archive's. One
  difference that +unity1 already had: in the archive
  `usr/share/doc/calamares-settings-ubuntu-unity/changelog.gz` is a symlink
  to `-common`'s, in our builds it is a file. Cause not established
  (debhelper version at build time is the likely one); harmless.
- Regression `rt.sh` on the +unity2 `.deb` (basicwallpaper `077f7c36…`):
  Calamares on top in 9 of 9 checks, wallpaper `DESKTOP` + `BELOW`
  (`logs/05-rt-unity2-prebuild.txt`); the archive `.deb` fails
  (`logs/01-rt-archive.txt`).

## Blocked

- `scripts/build_sbuild.py` does not handle epochs (and drops binaries whose
  names do not contain the source name) - May's script, reported via C.
- Publication needs the source commit in a remote-tracking ref of ours
  (none exists for this Launchpad clone) and an aptly snapshot publication
  (the current `./resolute` publishes the local repo directly) - reported
  via C.
- `version_safety.py` needs the apt candidate to be the new version, which
  only exists once the package is in a repository apt uses.

Resume at IMPLEMENTING (gated rebuild), then VERIFYING.

## Gated rebuild and verification (2026-09-29)

The two blockers above are resolved. `build_sbuild.py` handles epochs since
main 6596001. The source commit c03daf48 is on
`Ubuntu-Unity-LifeSupport/calamares-settings-ubuntu` as
`b/UNITY-20260927-021` (repository created in UNITY-20260927-046); the push
clone is `~/work/b/021-push`. The branch was merged with main (78933b4).

- Pre-build (gate/): the pocket view shows resolute 1:26.04.12 only;
  version_safety --pre-build gives UNKNOWN (expected before a build), and the
  ordering is newer.
- Gated sbuild: manifest PASS, source tree d4fb3f58. The binaries are
  -ubuntu-unity, -common, -common-data, -common-dbgsym (.ddeb), -kubuntu and
  -lubuntu.
- logs/06: rt.sh on the gated -ubuntu-unity deb, Calamares on top 3/3 in all
  three cases (basicwallpaper 077f7c36); the archive fails (logs/01).
- logs/07: the file lists of -ubuntu-unity/-common/-common-data equal
  +unity1; the changelog went from 1 to 95 entries.
- Verifier round 1: INCOMPLETE (REVIEWED), no finding values. (a) and (b)
  hold for the Ubuntu Unity binaries. The build also ships the patched
  basicwallpaper in calamares-settings-lubuntu and -kubuntu 1:26.04.12+unity2
  (their file lists equal the archive's; only basicwallpaper and the version
  pins differ). +unity1 never published those two packages. Their behaviour
  change is unmeasured:
  - Lubuntu: openbox on X11, so the new desktop-window path is active;
  - Kubuntu: depends on the Qt platform under kwin_wayland.

  Publishing them would move any system with our repo from the archive
  versions to ours and shadow later 1:26.04.12ubuntuN updates. Decision
  pending (May, via C): leave them out of the publication, or measure the
  Lubuntu/Kubuntu OEM sessions first.
