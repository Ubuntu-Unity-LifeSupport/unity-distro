# Agent B's package changes that exist only on builder

The `packages/*` trees below are git-ubuntu clones whose only remote is
Launchpad (`origin`), which we do not push to. Their `unity/resolute`
commits therefore lived only on builder. They are exported here with
`git format-patch <base>..unity/resolute`, so they survive the builder.
Restore with `git am` onto the base.

| package | base | patches | what |
|---|---|---|---|
| appmenu-gtk-module | `origin/ubuntu/resolute` 025b498 | 1 | +unity1: module resident (a783b01c, LP #2166410) |
| indicator-bluetooth | `origin/ubuntu/resolute` 3540ba2 | 1 | +unity1: systemd-dev, user unit back |
| indicator-datetime | `origin/ubuntu/resolute` 4fb6fd8 | 2 | +unity1 CMake 4 / libnotify 0.8; +unity2 tasks with only DUE (LP #1848969, #2099742) |
| indicator-keyboard | `origin/ubuntu/resolute` 134e195 | 4 | +unity1/2 build and tests; +unity3 NULL InputSources (LP #2166139) |
| indicator-power, -session, -sound | `origin/ubuntu/resolute` | 1 each | +unity1 FTBFS fixes |
| indicator-printers | `origin/ubuntu/resolute` c5e42e6 | 1 | +unity1: systemd-dev, user unit back |
| libindicator | `origin/ubuntu/resolute` 56a2331 | 2 | +unity1: systemd-dev, `indicators-pre.target` kept; +unity2: Ayatana indicators on Unity's panel |
| libunity | `origin/ubuntu/resolute` fc47c88 | 1 | +unity1: scope runner without `imp` |
| nux | 2c1878a (branch `b/fbo`) | 2 | +unity2: rebase onto 0ubuntu15, FBO attachment fix (LP #2160298) |
| indicator-messages | `origin/ubuntu/stonking` 78d9113 | 1 | 0ubuntu8~26.04.1: no-change backport of 26.10 (LP #2166912); the base is the 26.10 branch, not resolute _(row added 2026-09-27, UNITY-20260927-036)_ |
| calamares-settings-ubuntu | `origin/ubuntu/resolute` c699701 | 1 (+2 unpublished) | +unity1: basicwallpaper desktop window (known issue #4) - export in `research/calamares-oem/`, not here; +unity2 (changelog restored) and +unity3 (sudoers.oem 0440) are exported in `research/UNITY-20260927-021-calamares-oem-wallpaper/patches/` and `research/UNITY-20260927-041-calamares-oem-sudoers/patches/` on the unmerged task branches `b/UNITY-20260927-021` and `b/UNITY-20260927-041` _(row added 2026-09-27, UNITY-20260927-036)_ |

`debdiff/` holds sources without a git tree:
- `unity-lens-files_+unity1.debdiff`: in aptly.
- `session-migration_+unity1.debdiff`: in aptly (published by agent A).
- `hud_+unity1.debdiff`: in aptly; CMake 4, systemd-dev and C++17 for the
  tests (`research/hud/`).
- `ayatana-indicator-messages_+unity1.debdiff`: in aptly.
- `overlay-scrollbar_+unity1.debdiff`: in aptly; the dead GTK2 module is
  no longer built, and `81overlay-scrollbar` is removed on upgrade.
- `ubuntu-unity-meta_0.29+unity1.debdiff`: in aptly; recommends
  ayatana-indicator-messages instead of overlay-scrollbar-gtk2.

The seven `unity-scope-*` debdiffs are in `research/unity-scopes/debdiff/`
and in aptly.
