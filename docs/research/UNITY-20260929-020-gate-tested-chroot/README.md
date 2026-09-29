# UNITY-20260929-020: the release gate checks that the gated build matches the tested build

Tool task, agent A. From UNITY-20260929-016, whose design review 3 noted:
`build_sbuild.py --tested-with <tested manifest>` makes the gated build
refuse a chroot other than the tested build's, but nothing requires the
flag, so "the tested and gated builds of one task use the same tarball"
(ENGINEERING-PROCESS section 6) is enforced only if the builder remembers
it.

## 1. What is there (main `e9f83de`)

- `build_sbuild.py` writes `manifest["chroot"]` for every build since
  UNITY-20260929-016: tarball, sha256, snapshot, sources, InRelease lines,
  sbuild config and `allow_old_chroot`. With `--tested-with` it also writes
  `chroot["tested_with"]`: the tested manifest's absolute path and sha256,
  and its `chroot_sha256`, which must equal this build's `chroot.sha256`.
- `create_release_gate.py` validates the release record and the build
  manifest: fields, verification, peer notice, source provenance, artifact
  hashes, build dependencies and version safety. It reads nothing of
  `chroot`. A manifest from before -016, without `chroot`, still passes.
- `publish_aptly.py` re-checks the gate, the manifest and the evidence
  manifest. It also reads nothing of `chroot`.
- In practice a task has one of three testing situations:
  1. A separate test build was tested on target, then a gated build was
     made. This was -019 and -040, and B's -014.
  2. The gated build itself was tested on target (a -040-style regression
     run on the gated debs).
  3. The tested build predates -016 and has no manifest `chroot`, like
     B's -014 test build on the old tarball. ENGINEERING-PROCESS section 6
     then says: compare the `.buildinfo` Installed-Build-Depends, and
     repeat the target test on any difference.

## 2. Existing fix

None: the gate scripts do not look at `chroot`, and nothing else checks the
link between the tested and gated builds. `NOT_FIXED`.

## 3. Proposal (for the Design Challenger)

P1. **A gated manifest must come from the -016 policy.**
`create_release_gate.py` refuses a manifest without `chroot`, and says to
rebuild with `build_sbuild.py`. This affects no pending publication: every
gate from now on needs a new gated build anyway, since builds from before
-016 ran on the old tarball or an on-demand chroot.

P2. **The link to the tested build is one of three recorded modes.** The
release record gets `tested_build` with one of these values:
- `"same_chroot"`: the manifest has `chroot.tested_with`, and its
  `chroot_sha256` equals `chroot.sha256`. build_sbuild already checked it.
  If the tested manifest still exists at its path, the gate re-hashes it
  against `manifest_sha256`.
- `"buildinfo_identical"`: the record names `tested_buildinfo`, a committed
  file in the repository holding the tested build's `.buildinfo`. The gate
  compares its Installed-Build-Depends with the gated build's own
  `.buildinfo`, taken from the manifest's artifacts, and requires them to be
  identical (`build_dependencies.installed_build_depends`).
- `"this_build"`: the target test ran on this gated build's artifacts. The
  record's evidence must name a `target_test_record`, which goes into the
  evidence manifest.

Anything else is refused. The gate writes `tested_build`, with the mode and
its data (the tested manifest sha256, or the buildinfo path and sha256, or
the record), into `release-gate.json`.

P3. **`publish_aptly.py`** refuses a gate without `tested_build`, and
re-checks it against the committed manifest and evidence:
- `same_chroot`: the manifest's `chroot.tested_with.chroot_sha256` equals
  `chroot.sha256`.
- `buildinfo_identical`: the named file is tracked, clean and matches its
  sha256, and the comparison is repeated.
- `this_build`: the record is in the evidence manifest.

The shared logic goes in one module that both scripts call, as
`build_dependencies.py` does.

P4. **Docs.** ENGINEERING-PROCESS section 6 and the release-record fields
get the three modes.

Rejected so far:
- **Only recording whether `tested_with` is present.** It does not enforce
  the rule; the coordinator's brief allows it, but a record that nobody
  checks repeats the gap.
- **Requiring `tested_with` always.** It excludes modes 2 and 3, which are
  legitimate (mode 3 is written into ENGINEERING-PROCESS).
- **Comparing payloads (debs) instead of Installed-Build-Depends.** Payloads
  differ legitimately (timestamps, build paths) and are not what the policy
  pins.

Tests: unit tests of the shared module; create_release_gate and
publish_aptly refusals and acceptances per mode, in the end-to-end fixture
of UNITY-20260929-014 (`test_build_dependencies_consumers.py`, fake aptly
first on PATH).
