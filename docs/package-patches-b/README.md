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
| libindicator | `origin/ubuntu/resolute` 56a2331 | 1 | +unity1: systemd-dev, `indicators-pre.target` kept |
| libunity | `origin/ubuntu/resolute` fc47c88 | 1 | +unity1: scope runner without `imp` |
| nux | 2c1878a (branch `b/fbo`) | 2 | +unity2: rebase onto 0ubuntu15, FBO attachment fix (LP #2160298) |

`debdiff/` holds sources without a git tree:
- `unity-lens-files_+unity1.debdiff`: built, not in aptly yet; it waits for
  target2.
- `session-migration_+unity1.debdiff`: built, 9 of 9 tests pass, not in
  aptly.
- `hud_+unity1-WIP.debdiff`: work in progress; still FTBFS on the
  googletest C++17 requirement.

The seven `unity-scope-*` debdiffs are in `research/unity-scopes/debdiff/`
and in aptly.
