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

## 3. First proposal (superseded by section 5)

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

## 4. Design review 1: REVISE

The Challenger found the layer and the mode structure right. What the modes
check was not:

- They tied chroots together, but not what ENGINEERING-PROCESS section 6
  protects: the artifacts tested on target are the gated build, or are
  equivalent to it.
- `this_build` was a free-form bypass.
- `same_chroot` trusted a tested manifest that may not be in the
  repository. It also ignored `--extra-package`, which changes
  Installed-Build-Depends while the chroot stays the same.
- P1 was wrong to say no pending publication is affected. About 12 package
  tasks sit in REVIEW behind aptly freeze #1, all built before -016:
  UNITY-20260927-012, -023, -026 to -029, -037 and -052, and
  UNITY-20260928-014, -019, -020 and -022. P1 blocks all of them. That is
  intended, but it has to be stated, with their way forward.
- P3 re-checked less than the gate.
- The shared code belongs in a new module. sbuild_chroot.py is the builder
  tool, with network fetch and tarball creation, and the gate and the
  publisher should not import it.

## 5. Proposal, revised

**R1. Manifests from before -016 are refused.** `create_release_gate.py`
refuses a gated manifest without `chroot`. This blocks the pending tasks
listed in section 4. Each of them needs a new gated build under -016, then
one of these:
- `buildinfo_identical` against its old tested build's `.buildinfo`, if the
  target test installed artifacts of a build whose `.buildinfo` is on
  record;
- or a new target test, with `this_build` or `same_chroot`.

The freeze already stops these tasks; nothing is lost now.

**R2. Every mode names what the target test installed.** The release record
gets:
- `target_test`: `{"record": <repo path of the target test record>,
  "debs": {<file name>: <sha256>, ...}}`, the packages the target test
  installed;
- `tested_build`: one of three modes.

The gate checks the mode as follows.

- **`this_build`**: every `target_test.debs` entry is an artifact of the
  gated manifest, with the same sha256.
- **`same_chroot`**: the record names `tested_manifest`, which must be a
  file committed in the repository.
  - Every `target_test.debs` entry is one of its artifacts, with the same
    sha256.
  - The gated manifest's `chroot.tested_with.manifest_sha256` equals the
    committed file's sha256. The re-hash is mandatory.
  - The two manifests have equal `chroot.sha256`, `source_commit`,
    `source_tree_hash` and `build_dependencies` (or both have none).
- **`buildinfo_identical`**: the record names `tested_buildinfo`, a
  committed file.
  - Every `target_test.debs` entry must come from the build of that
    `.buildinfo`: either `tested_manifest` is also given and lists both
    the debs and the `.buildinfo` with their sha256s, or, for a tested
    build without a manifest (before -016), the target test record lists
    them.
  - The gated build's `.buildinfo` (from its manifest's artifacts) must
    match on `Source`, `Version` and `Build-Architecture`, and its
    Installed-Build-Depends must be identical, with no exceptions. A
    difference in an extra package or in Build-Depends is real and means a
    new target test.
  - This mode also covers a tested build that has a `chroot` with another
    sha, for example after the tarball rotated.

Any other value, or a missing field, is refused. The gate writes the mode
and all checked hashes into `release-gate.json` as `tested_build`.

**R3. One function, in both scripts.** A new `scripts/tested_build.py`
reuses `build_dependencies.installed_build_depends`.
`tested_build_error(record_or_gate, manifest, root)` checks everything in R2
and returns the recomputed `tested_build` object.
- `create_release_gate.py` calls it with the record.
- `publish_aptly.py` calls it with the gate's recorded values and the
  committed files. It refuses if anything fails, if a named file is
  untracked, dirty or has changed since the gate, or if the recomputed
  object differs from the gate's `tested_build`.

**R4. Test builds are recorded too.** ENGINEERING-PROCESS section 6 says
a build that will be tested on target is made with `build_sbuild.py`, and
its manifest, `.buildinfo` and the target test record are committed. The
gated build then uses `--tested-with` and the `same_chroot` mode, or the
gated build is itself tested (`this_build`). The release-record fields get
the three modes.

**Tests.**
- Unit tests of `tested_build.py`:
  - each mode is accepted;
  - Installed-Build-Depends differing by one version, one extra entry, one
    missing entry, or the architecture qualifier is refused;
  - a `Source` or `Version` mismatch is refused;
  - a tested manifest that is missing, uncommitted or has the wrong hash is
    refused;
  - under the same chroot, a different source tree or different
    `build_dependencies` is refused;
  - a target-test deb hash mismatch is refused in each mode;
  - an unknown mode, or the field absent, is refused.
- In `test_build_dependencies_consumers.py` (fake aptly first on PATH):
  - the gate refuses a manifest without `chroot`;
  - the gate accepts each mode and writes `tested_build`;
  - publish refuses a gate without `tested_build`;
  - publish refuses when a committed tested `.buildinfo` or manifest
    changed after the gate;
  - publish refuses when the recorded `tested_build` differs from the
    recomputed one.

## 6. Design review 2: REVISE, and the changes

R1-R4 and the test list resolve every point from round 1. One change is
still needed. It also answers the open question: for a tested build without
a manifest, the link from `target_test.debs` to `tested_buildinfo` must not
rest on free text.

- A hash found by grep in free text only proves the string is there, not
  what role it plays.
- A hand-written JSON record, made now, is no more trustworthy than that
  text.

The link comes from the build tool itself: the tested build's own
`.changes`, written by sbuild at build time. Its `Checksums-Sha256` field
lists the sha256 of both the debs and the `.buildinfo`.

Changes to section 5:

1. **R2, `buildinfo_identical`.** For a tested build without a manifest, a
   committed `tested_changes` file is required. Its `Checksums-Sha256` must
   contain every `target_test.debs` hash and the `tested_buildinfo` hash.
   With `tested_manifest`, its artifacts list covers the link, as before.
2. **R2, every mode.** The gate also checks that `target_test.record` is a
   committed file that names each deb, by file name or sha256. This is a
   cross-check of the attestation in `target_test.debs`, not the proof.
   Where a legacy task's log names neither, the task needs a new target
   test.
3. **R3.** `tested_build.py` parses `Checksums-Sha256` from a `.changes`.
   `publish_aptly.py`'s `dsc_checksums` already parses the same field from
   a `.dsc`, and is reused or moved there.
4. **Tests added:**
   - `tested_changes` missing, uncommitted or changed after the gate;
   - a deb or `.buildinfo` hash missing from `Checksums-Sha256`;
   - a target test record that does not name a deb.

## 7. Design review 3: APPROVE

Round 3 on section 6: APPROVE. To watch in the implementation: match
(file name, sha256) pairs, not hashes alone, and refuse a `.changes` listing
a file name twice; in `this_build` compare only the manifest's artifacts of
kind `binary`; if `dsc_checksums` moves, publish_aptly's source check keeps
its behaviour (the existing publish tests show it).

## 8. Implementation and validation

Code `aed9ec3` (branch `a/UNITY-20260929-020`, on main `e9f83de`):

- `scripts/tested_build.py`:
  - `check(fields, manifest, manifest_dir, root)` implements sections 5-6
    and returns the object the gate records. Files are repository-relative
    and must be tracked, committed and unmodified. (file name, sha256)
    pairs are matched together.
  - `this_build` compares only artifacts of kind `binary`.
  - `checksum_pairs` refuses a malformed line or a name listed twice.
  - `fields_from_gate` and `publish_error` let the publisher recompute and
    compare.
  - `publish_aptly.py`'s `dsc_checksums` is left unchanged: it returns a
    dict, where a duplicated name silently overwrites, and `taskctl.py` uses
    it too. The pair-based parser is separate instead of moved, so the
    source check keeps its behaviour.
- `create_release_gate.py` calls `check` after the build-dependency check,
  refuses on error, and writes `tested_build` into `release-gate.json`.
- `publish_aptly.py` calls `publish_error` after the build-dependency check.
- `docs/ENGINEERING-PROCESS.md` section 6 describes the three modes and the
  refusal of manifests without `chroot`. `docs/RELEASE-RECORD-TEMPLATE.json`
  has the fields.

Tests:

- `test_tested_build.py` (11 tests):
  - each mode is accepted, and the publisher recomputes the same object;
  - in every mode, a missing chroot, an unknown mode, no or empty
    target_test, a deb hash mismatch, a deb that is not built, or a missing
    or outside record is refused;
  - a record that does not name a deb, or is uncommitted, is refused;
  - `this_build` accepts binary artifacts only;
  - `same_chroot` refuses: not `--tested-with` this manifest, no
    tested_with, another chroot, another source commit or tree, another or
    dropped extra package, and a tested manifest modified or re-committed;
  - `buildinfo_identical` refuses an Installed-Build-Depends differing by a
    version, an entry more or less, or the arch qualifier, and a Source,
    Version or Build-Architecture mismatch;
  - the `.changes` link is refused with a deb or the `.buildinfo` missing,
    a hash under another name, a name listed twice, or neither link;
  - the publisher refuses in every mode after a committed file changed, and
    refuses an altered gate record: mode changed, a hash changed, an extra
    key.
- `test_build_dependencies_consumers.py`, with the real scripts, a fake
  aptly first on PATH and a fake HOME:
  - the gate refuses no tested_build, a deb not of this build, and a
    manifest without chroot, and passes a good record;
  - the publisher refuses a gate without tested_build, a record changed
    after the gate, and a mode altered in the gate. Each stops before any
    aptly call.
  - The -014 test's "next step" is now the chroot refusal (its fixture has
    no chroot).
- On main `e9f83de` scripts, with the branch's `tested_build.py` next to
  them, the end-to-end tests fail 7 times: every tested-build case, since
  main's gate and publisher do not call it
  (`runs/new-tests-on-main-e9f83de.txt`). On the branch: full suite 229 OK
  (1 skipped).

Limit, stated: the recorded list of debs is the attestation of what was
tested. The tools check that it is consistent with the builds and with the
record's text, not that it is complete. A gate naming fewer debs is a
smaller claim, not a forgery, so the publisher accepts it when it is
consistent.
