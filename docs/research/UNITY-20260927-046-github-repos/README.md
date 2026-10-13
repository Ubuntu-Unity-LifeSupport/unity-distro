# UNITY-20260927-046: our GitHub remote for every package we publish

Goal: every package in our aptly (or going through the publish gate) has a
repository in `github.com/Ubuntu-Unity-LifeSupport` from which
`scripts/publish_aptly.py` can check `source_commit`. Agent A, 2026-09-28.

**Authorization.** May approved the task through the coordinator
(`~/coordinator/PENDING-MAY.md`, 2026-09-28 08:25Z) and then confirmed it to
A directly, in A's session, before anything was created:
- 13 repositories for the packages that already have git history, pushing
  `unity/resolute` as is (no rewrite, no force), plus nux's `b/fbo`;
- the packages without git history go to a separate task (below).

## Inventory (FACT, 2026-09-28)

- aptly `unity-resolute`: **38 source packages** by the `Source` of its binaries
  (`aptly-sources-38.txt`; only 27 of them have a source package in aptly -
  `aptly repo search '$Architecture (source)'`).
- Organisation before: 13 repositories (`org-repos-before.txt`), 12 of them
  packages plus `unity-distro`.
- Missing: 26 packages.

| Group | Packages | Local git history | Done here |
|---|---|---|---|
| A - history exists | appmenu-gtk-module, calamares-settings-ubuntu, indicator-bluetooth, indicator-datetime, indicator-keyboard, indicator-messages, indicator-power, indicator-printers, indicator-session, indicator-sound, libindicator, libunity, nux | clones in `~/unity-distro/packages/` (git-ubuntu imports; nux from gitlab ubuntu-unity), branch `unity/resolute` | **repository created, pushed** |
| B - no history | hud, ayatana-indicator-messages, unity-lens-files, unity-scope-calculator, -devhelp, -gnote, -manpages, -tomboy, -virtualbox, -zotero, overlay-scrollbar, ubuntu-unity-meta, xorg-server | none: debdiffs in `docs/package-patches-b/debdiff/` or nothing; overlay-scrollbar and ubuntu-unity-meta only as one-commit test sources in `~/work/b/t045/src/` (task 045), xorg-server from the Ubuntu `.dsc` plus `research/xorg-versioning/patches/` | **not created** - needs new history (import of the archive `.dsc` and ours), May chose a separate task |

## How it was pushed

B's clones were not touched: no `git remote add`, no checkout, no config
change. B was told the list and branches beforehand and had no objection.
For each package A made its own clone
`~/work/a/046/<pkg>` (`git clone -b unity/resolute <B's clone>`), pointed that
clone's `origin` at `git@github.com:Ubuntu-Unity-LifeSupport/<pkg>.git`, and
pushed with `scripts/safe_git.py push --branch unity/resolute` (non-forced,
current branch only). nux: `b/fbo` fetched into A's clone and pushed the same
way. Repositories are public like the rest, description
"`<pkg>` for Ubuntu Unity 26.04 with our fixes; branch unity/resolute.
Imported from `<origin URL>`", default branch `unity/resolute`
(`org-repos-after.txt`: 26 repositories).

Not pushed: tags; calamares `b/UNITY-20260927-021`/`-041` (B's unpublished
`+unity2` `c03daf4` and `+unity3` `221c691`, going through B's gate); nux
`b/ubuntu15`, `b/vidmode`.

## Verification (`verify-github-reachability.txt`)

For all 25 packages that now have a repository: the commit that introduced
the published (highest aptly) version into `debian/changelog`
(`git log -S"(<version>)"`), and whether it is an ancestor of a branch tip
read from GitHub itself (`git ls-remote`).

The check would have fetched a GitHub tip missing locally into the clone; none
was missing (no `FETCH_HEAD` in `~/unity-distro/packages/` newer than
08:30Z), so B's clones were not written to.

- 24 reachable from `unity/resolute` (unity-gtk4-menu from `main`).
- **nux**: the published `0ubuntu15+unity2` (`9793c23`) is reachable only from
  `b/fbo`; `unity/resolute` is at `0ubuntu13`. Merging `b/fbo` into
  `unity/resolute` is B's/the coordinator's decision.

Limits (UNVERIFIED): "the commit that introduced the version" is the
changelog commit, not a proof of the tree the binary was built from - the
legacy builds had no manifest (`research/legacy-migration-20260927/`). Where a
version has two changelog commits (cinnamon-session `+unity3`:
`c38715c`, `fadd8c6`) the oldest was taken; both are on `unity/resolute`.
unity-lens-files (regenerated source, per the coordinator) is in group B and
has no repository.

## Separate task proposed

Group B: build repositories by importing the archive `.dsc` and our published
`.dsc` (`gbp import-dsc`) - new history, one decision per package on which
upstream to import; xorg-server may rather stay a dsc-plus-patches package.
