# UNITY-20260927-048: version safety before publication, without a circular apt check

Owner: agent B (builder; the board lists `target-desktop-2`). Scope from the
coordinator: the version check must run before publication and must not
require the candidate to be in the published repository already; no
temporary gate exceptions; it must still prove that the candidate is newer
than every version in the target series and its update pockets and that apt
will select it; handle binNMUs (UNITY-20260927-050, gap 3); align with how
`publish_aptly.py` rechecks apt right before the switch. The live
`/srv/aptly` publication is not touched (UNITY-20260927-047); experiments use
scratch state only.

```yaml
task_id: UNITY-20260927-048
package: unity-distro scripts/version_safety.py, scripts/publish_aptly.py
target_series: resolute
issue: local - the version gate cannot pass honestly before publication
status: REPRODUCED
issue_search_result: NOT_FOUND  # project-local scripts
source_version: origin/main 7a77757
binary_version: n/a
source_commit: 7a77757
observed: >
  logs/01-circularity.txt: (a) version_safety.py requires
  apt_candidate_binary_version == candidate_binary_version; measured before
  publication (calamares +unity2) apt's candidate is the archive's 1:26.04.12,
  so the honest record is UNSAFE, and the same record with the new version
  typed in as "apt candidate" is SAFE - the apt fields are unverified claims.
  (b) publish_aptly.py rechecks `apt-cache policy` on builder right before the
  switch and requires the candidate; builder's apt has no source for our
  repository at all (only the Ubuntu archive), so the check cannot pass for
  any of our packages, before or after a switch. (c) publish_aptly.py:340
  requires candidate_binary_version == the source version, so a binNMU
  candidate cannot pass.
expected: >
  Before publication, a measured (not typed) apt view of a target system with
  the candidate added shows apt selecting the candidate's binaries; the
  source version is newer than every target-series and update-pocket version,
  measured from the archive; the publisher repeats the same measurement right
  before the switch; binNMU binaries are judged by their own versions.
reproduction: logs/01-circularity.txt
root_cause: >
  (a) version_safety.py only compares numbers it is given; nothing produces
  the apt fields, so the only apt source is a person's reading of
  `apt-cache policy` on some machine. (b) publish_aptly.py's apt_candidate()
  asks the builder's own apt configuration, which is not a target system's.
  (c) candidate_binary_version is equated with the source version.
root_cause_mechanism: >
  the gate measures apt on the wrong system (builder) at the wrong time
  (before the candidate exists in any source apt reads), and trusts
  hand-entered apt data.
root_cause_evidence: docs/research/UNITY-20260927-048-version-safety/logs/01-circularity.txt
invariant: >
  A publication is allowed only if (1) the candidate source version is newer
  than the highest version of that source in each of resolute, -updates,
  -security, -backports and -proposed, as measured from the archive (a source
  in none of them passes this part as "not in archive"); and (2) a target
  system's apt, with the archive pockets it uses and our repository as the
  gated snapshot will publish it, selects every binary of the build at that
  binary's own version. Both measured, not typed, and
  measured again right before the switch.
existing_fix_result: NOT_FIXED
design_challenger_required: true
architectural_task: false
design_review_result: APPROVE  # second round, with conditions; see "Design review"
candidate_approaches:
  - (A, revised after Design Challenger REVISE, see "Design review") new
    scripts/apt_view.py measures; version_safety.py stays a pure comparator of
    that measurement; publish_aptly.py runs both again right before the switch.
    apt_view.py refuses to run as root and builds an isolated apt state in a
    temporary directory (Dir::State/Cache/Etc; status /dev/null; nothing of the
    host's apt configuration is read or changed) from:
      * docs/apt/target.sources - the Ubuntu archive pockets exactly as target2
        (Clean-2) has them (resolute, -updates, -backports, -security; main,
        universe, restricted, multiverse; logs/02), plus deb-src lines for the
        same pockets and resolute-proposed, used only to measure source
        versions. Our repository is NOT in target2's list (users add it by our
        install instructions); it is represented by the snapshot model below;
      * docs/apt/preferences.d/ - target2's preferences files (Ubuntu Pro ESM
        pins, which match only ESM origins);
      * the gated aptly snapshot, read-only (`aptly snapshot show
        -with-packages`), turned into minimal Package/Version/Architecture
        stanzas in a local `file:` repository with a Release whose Origin,
        Label and Suite equal our publication's (". resolute", "resolute"), so
        apt sees what it will see after the switch and origin pins apply
        (logs/04). `Trusted: yes` only for that directory, created by the tool.
    It runs apt-get update, fails on any fetch error (no cache fallback), and
    writes JSON (schema, tool version, timestamp, snapshot name and sha256 of
    its package list, sha256 of the sources and preferences files, for each
    fetched InRelease its sha256, Date and Valid-Until) with: for every binary
    of the build manifest, apt's candidate and version table; for the source
    package (by source name, `apt-cache madison`), the highest version in each
    pocket and which pocket it came from, or "not in archive".
    version_safety.py reads only that JSON (plus the manifest) - the typed apt
    fields and booleans are dropped - and decides: every manifest binary
    (.deb/.ddeb, Architecture any or all) is apt's candidate at its own
    Version (binNMU included; its source is checked by dpkg's Source rule
    against the candidate source version); the candidate source version is
    newer (gt) than the highest version in resolute and in -backports (else
    UNSAFE), in -updates and -security (else REPLACES_SECURITY_UPDATE), and in
    -proposed (else BLOCKS_FUTURE_UPDATE - the policy's fixed label; here it
    means: a version pending in -proposed is not older than ours, so when it
    migrates Ubuntu's version supersedes ours and our change is lost); a source that is
    in no pocket is recorded "not in archive" and passes the ordering part.
    publish_aptly.py drops apt_candidate() and the source-version comparison
    at line 340, runs apt_view.py with the gate's snapshot right before the
    switch, reruns version_safety.py on that fresh view, refuses unless SAFE,
    refuses if any InRelease Date is older than in the gate-time view or a
    Valid-Until has passed, and stores the fresh view in the write-once
    publication record. create_release_gate.py, the package-version-safety
    skill and ENGINEERING-PROCESS section 6 change with it.
    Measured: logs/03 (overlay model, first version), logs/04 (snapshot model
    with minimal stanzas: apt picks demo-binnmu 1:1.0+b1; local Release
    o=. resolute; per-pocket `Sources` via madison; Ubuntu InRelease files
    carry no Valid-Until).
  - (B) keep typed records, add "apt_policy_mode: PRE_PUBLICATION" that skips
    the apt comparison - rejected: a temporary exception, and it drops the
    "apt will select it" proof
  - (C) publish the candidate snapshot to a scratch aptly prefix and point a
    real target VM at it - rejected for the gate: needs `aptly publish`
    (blocked by the guard, and live publication work is 047) and a VM per
    check; kept as a possible target-verification method
  - (D) configure builder's own apt with our repository and the candidate -
    rejected: changes the build host's package configuration and still is not
    a target system's view
chosen_approach: (A) as revised, with the second review's conditions
why_chosen: >
  It measures exactly the target system's apt decision, with nothing
  published and no host configuration changed, and the same code runs before
  the build is gated and right before the switch.
code_risks:
  ownership_lifetime: not_applicable
  callbacks_cancellation: not_applicable
  threading_reentrancy: not_applicable
  ABI_API_file_list: checked  # version-check JSON and gate inputs change; create_release_gate.py and publish_aptly.py updated together
correct_layer: >
  version_safety.py owns the version verdict; publish_aptly.py owns the last
  check before the switch; neither owns apt measurement today, which is why a
  small shared measurement tool is proposed rather than logic duplicated in
  both.
defensive_workaround_rejected: >
  Relaxing the apt comparison before publication (B) would pass the gate
  without the proof it exists for.
unknowns:
  - gate-time measurement needs the snapshot to exist before the version
    check; creating snapshots is UNITY-20260927-047 - until then the tool is
    exercised against scratch aptly snapshots only
  - target systems with other repositories or pins than target2 (the
    measurement is for our reference target)
  - mirror lag between the gate-time and switch-time views (guarded by the
    InRelease Date rule)
  - "apt selects it" means apt's candidate with an empty dpkg status;
    whether the package installs (dependencies) stays with target
    verification
  - residual risk outside the gate: a SAFE version of ours can shadow a later
    Ubuntu update whose version sorts below ours; that is monitoring (as the
    xorg-watch timer does), not a gate check
```

## Reproduction

`logs/01-circularity.txt`: builder's apt sources (Ubuntu archive only; our
repository absent; `apt-cache policy calamares-settings-ubuntu-unity` gives
the archive's `1:26.04.12`); `version_safety.py` on an honest pre-publication
record for calamares +unity2 → `UNSAFE`; the same record with the new version
typed in as apt's candidate → `SAFE`; `publish_aptly.py:340` compares the
binary candidate version with the source version.

`logs/02-target2-sources.txt`: the target's own apt sources (Clean-2).

`logs/03-feasibility.txt`: the isolated apt state described in approach (A),
with the calamares +unity3 binaries from UNITY-20260927-045 as the overlay.

## Design review

First Design Challenger (2026-09-27): **REVISE**. Layer confirmed (a separate
measuring tool; version_safety.py a pure comparator; publisher calls both).
Required changes, all taken into approach (A): (1) model the repository after
the switch by the gated snapshot's own list, not "current publication +
candidate"; (2) say that target2 has no source for our repository, commit its
preferences.d, give the model repository a Release with our publication's
Origin/Label/Suite; `Trusted: yes` only for the tool's own `file:` directory,
refuse root; (3) source versions by source name, per pocket, one explicit
proposed rule, explicit "not in archive"; (4) every manifest binary against
its own version, drop line 340 and the single candidate field; (5) the
switch-time measurement is authoritative, its raw output goes into the
write-once record, InRelease Date must not go backwards, Valid-Until must not
have passed, fetch failures refuse; drop the typed booleans; (6) update the
skill and ENGINEERING-PROCESS in the same change.

Second Design Challenger (2026-09-27): **APPROVE**, with conditions carried
into implementation: word BLOCKS_FUTURE_UPDATE accurately and record the
shadowing residual risk; the model Release also carries `Codename: resolute`;
udeb entries stay out of the model; a fixture with `Architecture: all`;
Multi-Arch/Provides may stay omitted (single-arch amd64 target, concrete
package names) and the docs say so; madison: keep only `Sources` rows,
confirm them by source name (`apt-cache showsrc --only-source`), group by the
suite part across components; snapshot identity: the version check's
snapshot must equal the gate's, and the list sha256 at the switch must equal
the gate-time one; the pre-build check is ordering-only and never SAFE; "apt
selects it" is apt's candidate with an empty dpkg status.

## Implementation

Plan (after the second review):
1. `docs/apt/target.sources` (target2's pockets, plus deb-src incl.
   resolute-proposed) and `docs/apt/preferences.d/` (copied from target2).
2. `scripts/apt_view.py`: two modes - with `--snapshot` and `--manifest`
   (full view) or with `--source-package` only (pocket versions, for the
   pre-build check). Refuses root; isolated apt state; the snapshot list
   turned into a model repository (no `_source`, no udeb; Release with
   Origin/Label/Suite/Codename of our publication); `apt-get update` with
   `APT::Update::Error-Mode=any`; JSON output as in approach (A).
3. `scripts/version_safety.py`: reads only apt_view JSON (typed records are
   rejected as UNKNOWN); `--pre-build` gives an ordering-only verdict that is
   never SAFE; full mode checks every manifest binary and the pocket rules.
4. `scripts/publish_aptly.py`: drop apt_candidate() and the line-340 check;
   re-run apt_view.py and version_safety.py before the switch; snapshot name
   and list sha256 must equal the gate-time check; InRelease Dates must not go
   backwards; Valid-Until must not have passed; the fresh view goes into the
   write-once publication record.
5. `scripts/create_release_gate.py`: the version check must be SAFE and name
   the gate's snapshot.
6. `.claude/skills/package-version-safety/SKILL.md` and
   `docs/ENGINEERING-PROCESS.md` section 6 describe the measured flow.
7. Tests: comparator cases (binNMU, Architecture all, pockets, proposed,
   not in archive, candidate mismatch, typed record rejected, pre-build never
   SAFE), apt_view.py against a scratch aptly snapshot and local `file:`
   archive fixtures (including a fetch failure), and the publisher's
   switch-time comparison helpers.

## Result

- `scripts/apt_view.py` (new): the isolated target apt view (pocket view or
  full view with the gated snapshot as our repository).
- `scripts/version_safety.py`: rewritten as a pure comparator of that view;
  typed records are rejected; `--pre-build` is ordering-only and never SAFE.
- `scripts/publish_aptly.py`: `apt_candidate()` and the source-version
  comparison for binaries removed; the gate-time view is re-judged, must
  measure the gate's snapshot and be at most four hours old; right before the
  switch `apt_view.py` and `version_safety.py` run again and
  `compare_views()` refuses another snapshot content, an archive Release that
  went backwards or disappeared, or a passed Valid-Until; the switch-time
  view and verdict go into the write-once publication record.
- `scripts/create_release_gate.py`: computes the verdict from the
  `version_check` view instead of trusting a typed `version_safety: SAFE`, and
  requires that the view measured the gate's snapshot.
- `docs/apt/target.sources`, `docs/apt/preferences.d/` (from target2);
  `docs/ENGINEERING-PROCESS.md` section 6 and the `package-version-safety`
  skill describe the measured flow.
- Tests: 26 of 26 (`logs/05-tests-after.txt`); 18 new in
  `scripts/tests/test_version_safety.py` - comparator rules (binNMU,
  `Architecture: all`, every pocket rule, not in archive, apt selecting
  another version, typed record, pre-build never SAFE), `compare_views()`,
  and `apt_view.py` against a scratch aptly and local fixture archives (no
  network): snapshot binaries selected; a snapshot older than -updates gives
  REPLACES_SECURITY_UPDATE; a fetch failure refuses; two measurements of the
  same state compare cleanly.
- Real measurement (`logs/06-real-measurement.txt`): calamares-settings-ubuntu
  1:26.04.12+unity3 against the real archive pockets and a scratch snapshot of
  its files - all six binaries apt's candidates at +unity3, verdict SAFE; two
  runs compare cleanly (resolute-security moved forward between them); the
  pre-build check for a planned +unity4 is UNKNOWN (ordering only).

Found during implementation: the model repository's Release was not
recognised as such (apt names the list file with a leading `_`), so its
per-run name would have made every switch-time comparison fail. The first
real measurement showed it; fixed, and the integration test now checks it
(it fails with the old detection).

Not measured: a real `publish_aptly.py` run end to end (needs 046/047) and a
gate generated by `create_release_gate.py` (needs a task in REVIEW with a
pushed package source).

## First verification: FAIL, and the fixes

The independent verifier (INDEPENDENTLY_REPRODUCED for the verdict logic)
returned **FAIL, FIX_PARTIAL**:
1. `scripts/taskctl.py:231-235` (at `f415a56`) still required
   `record.fresh_apt_policy`, which the patched publisher no longer writes;
   since the publication record is write-once, every publication would have
   been unable to reach PUBLISHED. No test covered the publisher-taskctl
   contract.
2. The switch-time measurement read `docs/apt/target.sources` and
   `preferences.d` from the working tree without requiring them to be
   committed, and `compare_views()` did not compare their hashes, so an
   uncommitted edit could weaken the authoritative check silently.
3. Minor: the model Release identity was fixed to `. resolute` instead of
   following the gate's prefix and distribution.

Fixes (IMPLEMENTING again):
1. `publish_aptly.publication_evidence()` builds the switch-time part of the
   record; `taskctl.check_switch_time_evidence()` requires a SAFE switch-time
   check for the record's package and version and the apt view of the
   published snapshot. `PublicationRecordContractTest`: the publisher's record
   passes taskctl; an old-style record and an UNSAFE one are refused (against
   the old taskctl the test cannot even run: the check did not exist).
2. The publisher requires `docs/apt/` to be tracked and clean;
   `compare_views()` refuses different `sources_sha256`, `preferences` or model
   Release identity than at gate time (new tests).
3. The publisher passes `--release "<prefix> <distribution>|...|<distribution>|<distribution>"`.

Tests: 30 of 30. ENGINEERING-PROCESS section 6 mentions both new refusals.

## Verification

Round 1 FAIL (fixed), round 2 **PASS**, REVIEWED - `verification.md`. The
section 6 example now passes `--release` explicitly; test log refreshed (30
of 30).
