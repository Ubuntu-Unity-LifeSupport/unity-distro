# UNITY-20260928-007: build_sbuild.py and format 1.0 sources from git

Found in UNITY-20260927-052. Agent A, 2026-09-28.

## Evidence card

```yaml
task_id: UNITY-20260928-007
package: infra (scripts/build_sbuild.py, from UNITY-20260927-045)
target_series: resolute
issue: >-
  build_sbuild.py cannot build a format 1.0 source from a git clone, and
  from a git worktree it silently puts the .git file into the source package
status: REPRODUCED
issue_search_result: FOUND   # local: UNITY-20260927-005 found the stray .git in our published u-s-d +unity2..+unity5 sources; C recorded it as 054
source_version: scripts/build_sbuild.py at origin/main (last change 860df32)
binary_version: not_applicable
source_commit: scripts/build_sbuild.py as of origin/main ba514fe (branch a/UNITY-20260928-007 starts there)
observed: >-
  1. u-s-d (format 1.0) from a git clone: sbuild's dpkg-source -b stops with
     "dpkg-source: error: cannot represent change to .git/index: binary file
     contents changed" (UNITY-20260927-052, ~/work/a/052/out-1/).
  2. From a git worktree the build passes and the .diff.gz contains
     unity-settings-daemon-.../.git ("gitdir: .../worktrees/usd") - present in
     our u-s-d +unity2..+unity5 source packages (UNITY-20260927-005).
expected: >-
  the source package holds the package's files only, from a clone or a
  worktree, in every source format
reproduction: tools/format-matrix.sh (dpkg-source -b as sbuild runs it, tiny package per case)
reproduction_result: PASS   # runs/format-matrix.txt
evidence: runs/format-matrix.txt; ~/work/a/052/out-1/*-sbuild.log; UNITY-20260927-005 README "Other findings"
root_cause: >-
  build_sbuild.py runs `sbuild -d SERIES --no-clean-source --verbose` in the
  git checkout. sbuild builds the source package from that directory with
  `dpkg-source -b` (/usr/bin/sbuild:294) and no ignore options. Format 3.0
  applies dpkg-source's default ignores by itself; format 1.0 does not: a
  1.0 non-native build diffs every file against the orig tarball (.git
  included), a 1.0 native build tars every file (.git included).
root_cause_mechanism: >-
  Measured with the real dpkg-source (runs/format-matrix.txt), 4 formats x
  {clone (.git dir), worktree (.git file)} x options {none, -i, -I, -i -I}:
  1.0 non-native - clone FAILS with "cannot represent change to .git/index",
  worktree passes with 1 .git entry in the .diff.gz; -i fixes both, -I alone
  does not. 1.0 native - clone puts 49 .git entries into the tarball,
  worktree 1; -I fixes both, -i alone does not. 3.0 (quilt) and 3.0
  (native) - 0 .git entries with every option set.
invariant: >-
  the source package built by build_sbuild.py never contains version-control
  metadata, whatever the source format and checkout kind
existing_fix_result: NOT_FIXED   # local tool; no other copy of it exists
candidate_approaches:
  - "O1: pass --dpkg-source-opt=-i --dpkg-source-opt=-I to sbuild (applied by
    /usr/bin/sbuild to dpkg-source --before-build, -b and --after-build,
    lines 269-309). Measured on the tiny matrix: 0 .git entries and success
    in all 16 cases."
  - "O2: only -i. Measured: leaves 1.0 native tarballs with .git (49 and 1)."
  - "O3: build from an export (git archive HEAD) instead of the checkout.
    Not built."
  - "O4: after the build, before writing the manifest, scan the produced
    source files the .dsc names - every '+++' path of a .diff.gz (tab and
    timestamp stripped) and every member of each tarball that is not an orig
    tarball (native tarball, debian.tar.*) - and fail if any path component
    is a VCS name: .git, .svn, .hg, .bzr, CVS, _darcs, _MTN, RCS (as file or
    directory, any depth). Orig tarballs are exempt: they are upstream's,
    identical to the archive's (checked in UNITY-20260928-003 for the 13
    rebuilt packages) and pinned by sha256 in the .dsc and the manifest; a
    VCS file inside one is upstream content, not our leak."
  - "O5: a sbuild setting in ~/.sbuildrc ($dpkg_source_opts)."
  - "O6: debian/source/options in each package repository."
  - "O7: make publish_aptly.py reject such source packages."
chosen_approach: O1 + O4
why_chosen: >-
  O1 is the smallest change that makes dpkg-source itself exclude VCS
  metadata for every format, as 3.0 already does by default; measured in all
  16 cases. O4 makes the tool refuse to emit a manifest for a source package
  that still contains VCS metadata by any other path, so the invariant is
  checked on the artifact the manifest records rather than assumed.
alternatives_rejected:
  - "O2: measured insufficient for 1.0 native (runs/format-matrix.txt)."
  - "O5: per-host and invisible in the manifest; build_sbuild.py records its
    command in build_command, so the option belongs there."
  - "O6: changes 25 package repositories and still depends on each one
    following the convention (dpkg-source does read debian/source/options
    for 1.0 as well, /usr/bin/dpkg-source ~140-151, so it would work, but per
    repository)."
  - "O7: catches the leak only after a build, a manifest and a gate exist;
    build_sbuild.py should not produce a manifest for such a source."
  - "O3: stronger (the source would equal the commit tree exactly, and
    git-ignored untracked files could not leak), but it changes where sbuild
    runs and where its results land (build_sbuild.py searches repo.parent),
    needs the orig tarball placed next to the export, and duplicates what
    O1+O4 already guarantee for .git. INFERENCE - not built. Moved to a
    separate task together with the ignored-files gap (see unknowns)."
side_effects: >-
  The default ignore lists (runs/dpkg-default-ignores.txt) also drop
  editor/VCS files (*~, .#*, .*.sw?, .gitignore, .gitattributes, .mailmap,
  .bzr*, .hg*, .svn, CVS, ...) from 1.0 diffs (-i) and additionally
  *.a *.la *.o *.so from 1.0 full tarballs (-I). Measured on every package
  tree of ours (tools/side-effect-check.sh, runs/side-effects.txt): the
  source built with -i -I from a clone has exactly the same paths as the
  source built without options from `git archive` of the same commit for all
  23 format-1.0 packages we publish (plus unity-scope-home, which is in our
  trees but not in aptly) and all 8 3.0 (native) packages. No tracked file of
  the 1.0 packages matches the ignore lists. Two 3.0 (native) packages,
  calamares-settings-ubuntu and unity-gtk4-menu, track a .gitignore that
  matches both lists; their path sets are still identical because format 3.0
  already drops it without the options.
  One exception: unity-indicators (1.0 native, not in aptly) tracks a
  .gitignore, which -I drops from its tarball. Note: nux and
  unity-control-center are 1.0 with a Debian revision but no orig (full
  tarball), so -I, not -i, is what applies to them; they were compared by
  the member lists of that full tarball (no orig given). The 7 3.0 (quilt)
  packages are not in runs/side-effects.txt; the real sbuild before/after of
  gtk-nocsd (3.0 quilt) in the test plan covers that format.
code_risks:
  ownership_lifetime: not_applicable
  callbacks_cancellation: not_applicable
  threading_reentrancy: not_applicable
  ABI_API_file_list: >-
    build command recorded in the manifest changes (build_command); manifest
    schema unchanged
unknowns:
  - "Git-ignored untracked files pass the 'repository must be clean' check
    (git status --porcelain hides them) and would enter a 1.0 source unless
    the ignore lists match them. Measured now: none in our 41 git checkouts (all 40 package trees of the
    format inventory plus the 052 clone)
    (git status --porcelain --ignored, runs/ignored-untracked.txt). A
    different defect: proposed as a separate task (with O3 as one option)."
  - "Only .git was measured in the matrix; O4 extends the check to the other
    VCS names the invariant promises."
  - "Already-published u-s-d +unity2..+unity5 sources keep their stray .git;
    that is task 054, not repaired here."
design_challenger_required: true
design_review_result: APPROVE
architectural_task: true
correct_layer: >-
  build_sbuild.py is the one place that invokes sbuild for gated builds and
  writes the manifest the gate trusts; dpkg-source's own ignore options are
  the mechanism dpkg provides for exactly this, and 3.0 already uses it.
defensive_workaround_rejected: >-
  Building only from clones (never worktrees) would still fail for 1.0;
  cleaning .git out by hand before a build would destroy the checkout the
  manifest points at.
```

## Format inventory (our package trees, 2026-09-28)

`debian/source/format` and whether the version has a Debian revision:

| Format | Count | Packages |
|---|---|---|
| 1.0, non-native | 24 | hud, indicator-bluetooth, -datetime, -keyboard, -messages, -power, -printers, -session, -sound, libindicator, nux, overlay-scrollbar, unity-control-center, unity-lens-files, unity-scope-calculator, -devhelp, -gnote, -home, -manpages, -tomboy, -virtualbox, -zotero, unity-settings-daemon, xorg-server |
| 1.0, native | 1 | unity-indicators (not in aptly) |
| 3.0 (quilt) | 7 | appmenu-gtk-module, ayatana-indicator-messages, cinnamon-session, gtk-nocsd, libunity, light-locker, lightdm |
| 3.0 (native) | 8 | calamares-settings-ubuntu, compiz, session-migration, ubuntu-unity-meta, unity, unity-greeter, unity-gtk4-menu, unity-session |

## Test plan (after Design Challenger review 1)

- Unit tests (`scripts/tests/test_build_sbuild.py`): the stub sbuild runs the
  real `dpkg-source --before-build` / `-b` in the tree with exactly the
  `--dpkg-source-opt` values it receives, as /usr/bin/sbuild does, on tiny
  packages: 1.0 non-native from a clone (before: fails) and from a worktree
  (before: .git in the .diff.gz), 1.0 native from a clone (before: .git in
  the tarball), 3.0 (quilt) and 3.0 (native) (unchanged).
- O4 negative tests: a produced .diff.gz with a `.git` file entry, a native
  tarball with a `.git/` directory, a nested `sub/.git`, `.svn` in a native
  tarball - all rejected, no manifest written. Positive: an orig tarball
  containing `.gitignore` and `.git` passes.
- Real builds with sbuild: u-s-d (1.0) from a clone and from a worktree, and
  gtk-nocsd (3.0 quilt) from a clone - before with the current script, after
  with the fixed one; 3.0 compared by the file and member lists of its
  source files.
- B reviews the diff as the author of UNITY-20260927-045; Verifier.

## Design review

1. **REVISE** (2026-09-28): layer and root cause supported; asked for the
   alternatives the task names (~/.sbuildrc, debian/source/options,
   publish_aptly.py) to be rejected with reasons, a precise source_commit, the
   054 note, a deterministic proof of O1's side effects on all our 1.0
   packages, a precise O4 scope and orig exemption, O3 and ignored files as a
   separate task, and end-to-end tests instead of "the command contains the
   options". Addressed above.
2. **REVISE** (2026-09-28, same reviewer, on the revised card): design O1+O4
   supported and the first review's points resolved; two statements
   contradicted the evidence - side_effects said no tracked file matched for
   the 3.0 packages (calamares-settings-ubuntu and unity-gtk4-menu track a
   .gitignore; unchanged because 3.0 drops it anyway), and O6's rejection
   said only 3.0 reads debian/source/options (dpkg-source reads it for 1.0
   too). Both reworded; unity-scope-home marked as not in aptly;
   runs/ignored-untracked.txt lists every checkout.
3. **APPROVE** (2026-09-28, same reviewer): both points of review 2 fixed;
   the design is supported. The approval covers the design only; the patch
   is checked against the test plan and by the Verifier.

