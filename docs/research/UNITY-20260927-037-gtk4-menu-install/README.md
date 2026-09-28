# UNITY-20260927-037: libunity-gtk4-menu0 is never installed

Owner: agent B (target2). Migration finding: on target, after a full
upgrade from our aptly, `libunity-gtk4-menu0` is not installed, so on a
Unity installation GTK4 applications have no global menu. Assignment:
reproduce on a clean Clean-2 and find what should pull the package. Rule 0
and the correct layer apply. Fix up to what the pipeline allows: publishing
is impossible while 047 is stopped, so BLOCKED at publication is the
expected outcome. The Xsession snippet (UNITY-20260927-039) is a separate
task. Aptly freeze: no `aptly publish`.

```yaml
task_id: UNITY-20260927-037
package: unity-session (Recommends) - see chosen_approach
target_series: resolute
issue: local - our package libunity-gtk4-menu0 has no reverse dependency
status: REPRODUCED
issue_search_result: NOT_FOUND  # project-local package; DECISIONS/PATCHES/board searched
source_version: unity-session 49.4+unity1 (our aptly; archive 49.4 in resolute and stonking)
binary_version: libunity-gtk4-menu0 0.9 (our aptly)
observed: >
  logs/01: clean Clean-2 plus our repository, full-upgrade. It installs 79
  packages from our aptly, including new Recommends of upgraded packages
  (ayatana-indicator-messages from ubuntu-unity-desktop 0.29+unity1), but not
  libunity-gtk4-menu0 (candidate 0.9, "Reverse Depends:" empty). Its
  environment.d snippet is absent, so no GTK4 global menu in the session.
expected: >
  A Unity installation that uses our repository gets libunity-gtk4-menu0
  (and with it the GTK4 global menu), both as a new install and on a full
  upgrade of an existing one, while it remains removable.
reproduction: logs/01-clean2-full-upgrade.txt (repro.sh)
root_cause: >
  libunity-gtk4-menu0 is a new binary package of ours. It is not in the Ubuntu
  archive, and none of our packages Depends on, Recommends or Suggests it.
  apt installs a package on upgrade only when something newly requires or
  recommends it, so it stays uninstalled everywhere unless installed by hand.
root_cause_mechanism: missing reverse relationship; apt has no reason to install it
root_cause_evidence: >
  logs/01 (rdepends empty; the full-upgrade installs other new Recommends),
  logs/02 (who pulls the comparable components)
invariant: >
  Every component that the Unity session needs for its global menu is pulled
  by a package a Unity installation already has, as apt's Recommends (installed
  by default, removable), including on upgrade.
existing_fix_result: NOT_FIXED
candidate_approaches:
  - (A) unity-session +unity2 Recommends libunity-gtk4-menu0 - chosen
  - (B) ubuntu-unity-meta +unity2 desktop-recommends-* add libunity-gtk4-menu0
  - (C) carry indicator-appmenu +unity1 with Recommends libunity-gtk4-menu0
  - (D) libgtk-nocsd0 (our gtk-nocsd) Recommends libunity-gtk4-menu0
  - (E) Depends instead of Recommends anywhere
chosen_approach: A (subject to Design Challenger)
why_chosen: >
  libunity-gtk4-menu0 is a session-wide preload that acts only in a Unity
  session, installed through environment.d. That is the same class as
  libgtk-nocsd0, which Ubuntu itself puts in unity-session's Recommends (49.4,
  LP #2146557). unity-session is present on every Unity installation, whether
  it comes from the flavour meta or not. We already carry it (49.4+unity1), so
  the change adds no new carried package, and its upgrade to +unity2 makes apt
  install the new Recommends on existing systems.
alternatives_rejected:
  - B covers only installations with ubuntu-unity-desktop (flavour installs);
    a Unity session installed without the meta would still miss it. The meta
    is also the seed layer, one step removed from the component that needs it.
  - C mirrors appmenu-gtk3-module exactly (indicator-appmenu recommends it),
    but means carrying an additional archive package for one line, and
    indicator-appmenu is not specific to a session-wide preload.
  - D ties a Unity-only library to a desktop-neutral one (gtk-nocsd runs under
    Xfce and others, DECISIONS 2026-09-25).
  - E would make the menu library mandatory; Recommends keeps it removable,
    like libgtk-nocsd0.
  - both A and B - duplicates what libgtk-nocsd0 already shows, and adds a
    seed diff to carry for nothing (design review)
design_challenger_required: true
design_review_result: APPROVE  # round 1 REVISE on card completeness only, design unchanged
architectural_task: false
correct_layer: >
  the session package that already recommends the other session-wide
  preload of the Unity session
defensive_workaround_rejected: >
  installing the package by hand on test machines or in install instructions
  hides the gap for everyone else
code_risks:
  ownership_lifetime: not_applicable
  callbacks_cancellation: not_applicable
  threading_reentrancy: not_applicable
  ABI_API_file_list: checked  # unity-session file list unchanged; only Recommends
unknowns:
  - arm64/armhf/ppc64el - our aptly publishes amd64 only; unity-session is
    Architecture: all, so the Recommends is unsatisfiable elsewhere (apt
    ignores an unavailable Recommends)
  - interplay with 51gtk-nocsd / LD_PRELOAD ordering is UNITY-20260927-039,
    not changed here; the target check records what the session does
  - publication is blocked (047); the fix can reach READY_TO_PUBLISH at most
  - exit path: if the menu moves into gtk-nocsd (DECISIONS 2026-09-25, May's
    call), the same change must drop this Recommends from unity-session and
    gtk-nocsd must Breaks/Replaces libunity-gtk4-menu0
  - apt-get upgrade (not full-upgrade/apt upgrade/update-manager) never
    installs new packages: unity-session goes to +unity2 without the library,
    after which the Recommends is old and a later full-upgrade will not
    install it either. Accepted: that user still gets it with
    `apt install libunity-gtk4-menu0` or by reinstalling the recommends; the
    Ubuntu upgrade tools (update-manager, apt upgrade) install new Recommends
  - a user who removes the library after +unity2 keeps it removed (APT does
    not reinstall a removed Recommends); one who removed a hand-installed copy
    before +unity2 gets it again, because the Recommends is new - the empty
    environment.d override file still keeps it disabled
  - versions: 49.4+unity2 sorts above 49.4, 49.4build1 and
    49.4ubuntu0.26.04.1, so such an archive update would be shadowed by ours
    (checked by package-version-safety before publication); 49.4.1 or 49.5
    would win and drop the Recommends. On a release upgrade to 26.10
    (stonking, 49.4) our resolute package stays installed; once 26.10 ships a
    higher unity-session, nothing recommends the library and apt autoremoves
    it. This already applies to +unity1 and to every package we carry; it is
    the open question of a stonking suite in our repository, not specific to
    this task
  - libunity-gtk4-menu0 is Architecture: any, Multi-Arch: same, published for
    amd64 only
```

## Reproduction

`repro.sh` on target2 restored to Clean-2 (the `~/.dirty` marker was absent
before the run). The script adds our repository exactly as in
UNITY-20260927-047 (`http://192.168.56.10:8080/`, `Signed-By` the published
key), runs `apt-get update` and `full-upgrade`, and records the packages.
Result (`logs/01-clean2-full-upgrade.txt`):

- `libunity-gtk4-menu0`: candidate 0.9, not installed before or after the
  upgrade, and no reverse dependencies.
- `ubuntu-unity-desktop` 0.29 was upgraded to 0.29+unity1. Its new
  Recommends `ayatana-indicator-messages` was installed by the same upgrade.
  This is the mechanism a fix can use.
- `libgtk-nocsd0` came from 0.29/49.4's Recommends.

`logs/02-precedent.txt` shows who pulls the comparable components on this
machine:

- `appmenu-gtk3-module` comes from `indicator-appmenu`, `vala-panel-appmenu`
  and `appmenu-registrar` (Recommends).
- `libgtk-nocsd0` comes from `unity-session` and `ubuntu-unity-desktop`
  (Recommends).

## Design review

Round 1 (read-only subagent): REVISE, **no design change**. The layer (A,
unity-session Recommends, one place) and the form (Recommends, not Depends)
were confirmed, and 037 does not need to wait for 039. The reason: the
library is either loaded or, on the Xsession path of 039, simply not loaded,
exactly as today. The card was missing the exit path, the four upgrade
cases, the version notes and the proof plan. All are now in unknowns and
below. With these added the verdict is APPROVE, as stated in round 1.

## Plan

1. `packages/unity-session`: a +unity2 changelog entry (trailer from
   `date -u`) that adds `libunity-gtk4-menu0` to Recommends. Build with
   `scripts/build_sbuild.py`. Compare `debc` +unity1 against +unity2: the
   file list is unchanged and only the Recommends line differs.
2. target2, restored to Clean-2, with our repository and the locally built
   +unity2 from a local file repository (no aptly):
   - `full-upgrade` installs libunity-gtk4-menu0;
   - `apt-get upgrade` behaves as described in unknowns.
3. Target check: after login, `libunity-gtk4-menu.so.0` appears in a GTK4
   application's `LD_PRELOAD` and memory map, alongside gtk-nocsd, and the
   application's menu reaches the Unity panel (screenshot).
4. version_check through apt_view, then a release gate. Publication stays
   BLOCKED (047).

## Result

- **Package** (`packages/unity-session`, branch b/UNITY-20260927-037, commit
  7af2106; `patches/0001-...patch`): 49.4+unity2 adds `libunity-gtk4-menu0` to
  Recommends. The changelog trailer comes from `date -u`.
- **Build.** `scripts/build_sbuild.py` in a clean resolute sbuild
  (`logs/03-build.txt`, `build/…-build-manifest.json`). The manifest lists
  the .dsc, the source tarball, the .deb, the .buildinfo and the .changes.
- **+unity1 against +unity2** (`logs/04-debc-unity1-vs-unity2.txt`). The
  control files differ only in Version and Recommends, the file list only in
  the size of `changelog.gz`.
- **Clean-2 with our repository and +unity2 from a local file repository, no
  aptly** (`logs/05-after-full-upgrade.txt`):
  - the simulated full-upgrade installs `libunity-gtk4-menu0` and
    `unity-session` +unity2;
  - the real full-upgrade installs `libunity-gtk4-menu0` 0.9, marked auto,
    whose reverse dependency is now `unity-session`, and the environment.d
    snippet is present;
  - the `apt-get upgrade` simulation printed no `Inst` line for either
    package. The kept-back line could not be told apart, because the guest's
    locale is Russian and the filter matched English text. The apt-get
    upgrade case therefore rests on APT's documented behaviour (unknowns),
    not on this run.
- **Unity session after a reboot** (`logs/06-session-check.txt`). The
  systemd user manager and compiz have
  `LD_PRELOAD=libunity-gtk4-menu.so.0:libgtk-nocsd.so.0` and
  `XDG_CURRENT_DESKTOP=Unity:Unity7:ubuntu`. File Roller (GTK4) is started
  in the session:
  - both libraries are in its environment and its memory map;
  - its window carries `_GTK_MENUBAR_OBJECT_PATH=/org/gnome/FileRoller/menus/menubar`;
  - the Unity HUD finds "New Archive… (File Roller)", an item of the
    header bar menu.
- **Version** (`logs/07-version-prebuild.txt`). In pre-build mode
  49.4+unity2 is newer than resolute 49.4, and there is no updates,
  security or proposed version. The result is UNKNOWN by design: pre-build
  is never SAFE.
- **Not done: the gate.** It needs the package in an aptly snapshot, which
  means writing to the live aptly database (`repo add`, `snapshot create`).
  With publication stopped (047), that waits for the pipeline. Nothing was
  written to aptly.

## Status

VERIFYING -> independent review; then BLOCKED at the publication gate (047).
