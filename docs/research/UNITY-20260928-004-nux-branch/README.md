# UNITY-20260928-004: nux unity/resolute lags behind the published package

Owner: agent B (nux is B's package). Found in UNITY-20260927-046. The
published nux 0ubuntu15+unity2 (9793c23) exists only on the branch
`b/fbo`, while `unity/resolute` stays at 0ubuntu13, both in the local clone
and on GitHub (the repository A created in 046). The task is to bring
`unity/resolute` to the published history without rewriting it
(fast-forward or merge, no force), and to check that its tree is what the
published package was built from. No code change; aptly is read only.

```yaml
task_id: UNITY-20260928-004
package: nux (repository branch, no package change)
issue: local - branch bookkeeping
status: REPRODUCED
observed: >
  Clone ~/unity-distro/packages/nux: unity/resolute = 3c56e89
  (0ubuntu13), b/fbo = 9793c23 (0ubuntu15+unity2). GitHub
  Ubuntu-Unity-LifeSupport/nux (git ls-remote): unity/resolute 3c56e89,
  b/fbo 9793c23.
expected: >
  unity/resolute points at the commit the published package was built from,
  reached without rewriting history
existing_fix_result: NOT_FIXED
chosen_approach: >
  fast-forward: 3c56e89 is an ancestor of 9793c23 (git merge-base
  --is-ancestor), so no merge commit is needed
verification: >
  logs/01: the 4 published .debs in /srv/aptly/pool are byte-identical
  (sha256) to the build in ~/work/b/nux/outu2 (its .changes). aptly holds no
  nux source package, so the source is taken from that build.
  logs/02: the build's source (format 1.0, one tarball, sha256 a701a354...)
  equals `git archive 9793c23` exactly (`diff -r` empty).
  logs/03: the local ref was moved with `git fetch . b/fbo:unity/resolute`,
  which refuses anything that is not a fast-forward.
design_challenger_required: false
design_review_result: NOT_REQUIRED
architectural_task: false
package_change: false
unknowns: []
```

## Steps

1. Measure the branches (above) and the ancestry: 3c56e89 is an ancestor
   of 9793c23. Between them are four commits: 0ubuntu14; Ubuntu's
   "Remove libboost-system-dev"; our rebase onto 0ubuntu15 with
   fix-missing-vidmode.patch; our FBO fix, LP #2160298.
2. Prove what was published (logs/01, logs/02).
3. Fast-forward the local `unity/resolute` (logs/03). The `b/*` branches
   are not touched.
4. Push `unity/resolute` to GitHub, fast-forward only. The repository was
   created by A in 046, so the push waits for A's agreement.

## Result

A agreed. `safe_git.py` pushes only to a remote named origin, so a
temporary clone with origin on GitHub was used. There `unity/resolute` was
moved with `git update-ref` from the expected old value 3c56e89 to 9793c23,
after an ancestry check. The push was `3c56e89..9793c23 HEAD ->
unity/resolute`: a fast-forward, with no force. On GitHub, unity/resolute
and b/fbo now both point at 9793c23 (logs/04). The local clone
~/unity-distro/packages/nux has unity/resolute = 9793c23 as well. Its remote
configuration is unchanged (origin: Launchpad).

## Status

DONE after independent check.
