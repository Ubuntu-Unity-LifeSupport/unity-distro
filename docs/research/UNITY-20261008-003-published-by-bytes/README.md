# UNITY-20261008-003: published_by compares bytes, not names

Task kind: tool. Owner: A. Parent: UNITY-20260929-009.

## 1. Problem

A covered task can close as `PUBLISHED` through another task's publication,
using `published_by: {task_id, record_sha256}`.
`taskctl.check_own_build` accepts it when all of the following hold:
- the task's own `build_sbuild.py` manifest has the same package and
  version as the publish record;
- its commit equals the published commit or is an ancestor of it;
- its source and binary artifacts have the same names (file, package,
  version, architecture) as the record's.

The bytes are never compared. So a build of other content, with the same
names, proves nothing about what was published. A build from an ancestor
commit always has other bytes.

## 2. Measurement on the three past closures

`tools/probe.py` follows this chain:
1. the publish record;
2. its `gate_file`, whose sha256 equals the record's `gate_sha256`;
3. the gate's `build_manifest`, whose sha256 equals the gate's;
4. the published build.

It compares that build with the covered task's own manifest
(`runs/01-probe-past.txt`). The `.buildinfo` files are not committed, so the
probe used the copies in the agents' worktrees, each with the sha256 named
by its manifest.

| Covered task / publisher | Commit | Bytes | `buildinfo_identical` | Verdict |
|---|---|---|---|---|
| UNITY-20260927-052 / -012 | same | 8/8 equal | - | PASS (bytes) |
| UNITY-20261002-011 / -003 | same | 2/8 (only the ddebs) | yes | PASS (buildinfo) |
| UNITY-20260928-020 / UNITY-20260927-027 | same | 2/7 | no: `Installed-Build-Depends` differ (about 100 packages) | FAIL |

UNITY-20260928-020 stays `DONE` by C's decision; see `docs/DECISIONS.md`,
2026-10-08. Its change is test patches only. The published gated build of
-027 ran those suites on the snapshot chroot and passed them.

## 3. Decisions (C, 2026-10-08)

A covered task is accepted in exactly two cases:
1. **Bytes.** Every `source` and `binary` artifact of its own manifest
   equals the publish record by file name and sha256, as the same set.
2. **`buildinfo_identical` against the published build.** The published
   build is found through the record's `gate_file` and `gate_sha256`, then
   the gate's `build_manifest` file and sha256. Both builds must have:
   - the same source commit and tree;
   - the same extra build dependencies;
   - the same `.buildinfo` identity fields;
   - the same `Installed-Build-Depends`.

   Both `.buildinfo` files must be committed, as with
   `tested_build.committed`: tracked, committed, unmodified, no symlink,
   no `..`. Each must match the sha256 its manifest records.

A commit that is only an ancestor of the published one is no longer
accepted, because no byte link exists.

So that future publications carry the files, the `.buildinfo` must be
committed together with the manifest.

## 4. Change

1. **`scripts/tested_build.py`.**
   - New `buildinfo_identity_error(a_text, b_text, a_label, b_label)`. It
     holds the `.buildinfo` comparison that `check()` makes today, in the
     same order:
     1. the identity fields;
     2. a package listed twice (first `a`, then `b`);
     3. `Installed-Build-Depends`.

     `check()` calls it with `("tested", "gated")`. Its messages stay the
     same, and `test_tested_build.py` is not changed.
   - New `manifest_buildinfo(root, manifest, manifest_dir, label)`. It
     requires the manifest to list exactly one `.buildinfo`. The file must
     be committed (`committed()`) and must match the recorded sha256.
2. **`scripts/taskctl.py` `check_own_build`.**
   - The package and candidate version must match, as before.
   - **Rule 1.** The `source`/`binary` set of the task's own manifest
     must equal the record's, compared by (file, sha256).
     - `source_file` is not compared, because the `.dsc` hash covers it.
     - `buildinfo` and `changes` are ignored.
     - The `PUBLISHED` path already checks that the record's artifacts
       equal the gated manifest's.
   - **Rule 2.** Otherwise, the published build is read the way the
     `PUBLISHED` code reads it:
     - the record's `gate_file` through `committed()`, with its sha256
       equal to `gate_sha256` and `gate.task_id == record.task_id`;
     - the gate's `build_manifest` through `committed()`, with its sha256
       equal to the gate's.

     Then the following must be equal in both builds: source commit, tree,
     and `dependency_identity`. Next, `manifest_buildinfo` is called for
     both builds, and then `buildinfo_identity_error(own, published)`.
   - The ancestor and `source_repo` git code is removed. A refusal names
     the rule that failed.
   - The `check_own_build` docstring and the comment at the `PUBLISHED`
     call ("proved its commit is in ...") are rewritten to the two rules.
3. **Future publications.**
   - `.gitignore` gets the exception `!docs/research/*/*/*.buildinfo`.
     A git check confirmed that `docs/research/X/build*/Y.buildinfo` is
     un-ignored, while other depths and other paths stay ignored. All
     committed manifests are at that depth.
   - `create_release_gate.py` calls `manifest_buildinfo` on the gated
     build. The call comes before the snapshot/distribution checks, so
     that it is reached.
   - `publish_aptly.py` calls it too, so it catches a `.buildinfo` that
     was edited or removed after the gate.
   - The fixture in `test_build_dependencies_consumers.py` gets a
     committed `.buildinfo` artifact.
4. **Evidence for UNITY-20261002-011.**
   - Commit the copy of `build-011/` and the published `build-gate/`
     `.buildinfo`, sha256 `d022f62b...` and `4aaffa92...`, each where its
     manifest names it.
   - The tested `build/` copy (`2bfb0ebd...`) is already committed.
5. **`docs/ENGINEERING-PROCESS.md` section 6.**
   - Step 8 lists the build manifest and its `.buildinfo` among the files
     committed before the gate. The gate and the publisher refuse an
     uncommitted one.
   - In rule B, `git add -f` is needed only for files outside the
     `build*/` layout.
   - Rule P is rewritten to the two cases.
6. **Tests.**
   - `scripts/tests/test_taskctl_published_by.py`: the record fixture gets
     a real committed gate and published manifest with `.buildinfo`. The
     tests that relied on the old rule are rewritten:
     - `test_ancestor_commit_accepted` becomes "refused";
     - `test_different_hashes_are_fine` is replaced by "bytes differ,
       buildinfo identical: accepted" and "bytes differ, IBD differ:
       refused";
     - the git `source_repo` tests go;
     - the name-set test becomes a (file, sha256) set test.

     New tests:
     - an uncommitted `.buildinfo`: refused;
     - a gate or manifest sha256 mismatch: refused;
     - a gate with another `task_id`: refused;
     - a manifest with two `.buildinfo` files: refused.
   - Gate and publisher: an uncommitted `.buildinfo` is refused.
   - `docs/research/UNITY-20260929-023-published-by/real-020.py` is a
     historical tool of the old rule. It is left as it is and noted in
     this card.

## 5. Verification plan

- `tools/probe.py`, rerun with the new `taskctl.check_own_build` on the
  three past closures:
  - -052: PASS;
  - -011: PASS;
  - -020: FAIL with the `Installed-Build-Depends` reason.
- The whole `scripts/tests` suite passes.
- Mutations:
  - accept name equality again;
  - skip the `Installed-Build-Depends` comparison;
  - accept an uncommitted `.buildinfo`.

## 6. Design review

The Design Challenger, a temporary subagent, reviewed the design in two
rounds.
- **Round 1: REVISE.** It required six changes:
  - put the evidence files where their manifests name them;
  - read the gate the same way the `PUBLISHED` code does;
  - place the gate check before the snapshot checks and add one to the
    publisher;
  - update section 6;
  - remove the stale comments;
  - rewrite the tests of the old rule.
- **Round 2: APPROVE.**

## 7. Results (branch `a/UNITY-20261008-003`)

- **`runs/02-past-closures-new-code.txt`.** The real `covering_record`
  and `check_own_build` of this branch ran on the real evidence and the
  write-once publish records:
  - UNITY-20260927-052 through -012: **accepted**, by bytes.
  - UNITY-20261002-011 through -003: **accepted**, by
    `buildinfo_identical`. Its two `.buildinfo` files are now committed.
  - UNITY-20260928-020 through UNITY-20260927-027: **refused**. Its
    `.buildinfo` is not committed.
- **`runs/01-probe-past.txt`.** With the on-disk copy of that file, -020
  still fails, because `Installed-Build-Depends` differ. It stays `DONE`
  by C's decision (`docs/DECISIONS.md`, 2026-10-08). The new code does not
  re-check a past `DONE`.
- **`runs/03-suite.txt`.** `scripts/tests` gives 325 passed, 1 skipped and
  682 subtests passed. `test_tested_build.py` is unchanged.
- **`runs/04-mutations.txt`.** Each mutation was run in a scratch copy of
  `scripts/`, and each was caught:

  | Mutation | Tests that fail |
  |---|---|
  | rule 1 by names | 15 |
  | `Installed-Build-Depends` comparison skipped | the -020 case, plus subtests in `test_tested_build.py` |
  | uncommitted `.buildinfo` accepted | 4: published_by both sides, the gate and the publisher |
  | gate sha check skipped | its test |
  | gate `task_id` check skipped | its test |
  | commit comparison skipped | the ancestor and tree tests |
  | gate `.buildinfo` check removed | the gate test |

- `docs/research/UNITY-20260929-023-published-by/real-020.py` is a tool of
  the old rule. It is left unchanged as a historical record and would now
  refuse.
