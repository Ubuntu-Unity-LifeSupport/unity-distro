# Engineering process

This document is the single policy for investigating, fixing, verifying, and
publishing a package issue. `CLAUDE.md` gives the session entry points;
`docs/TWO-AGENTS.md` and `docs/COORDINATOR.md` define the roles. The current
task board is private at `~/coordinator/TASKS.md`; `scripts/taskctl.py` is the
only supported writer and enforces the transition graph, owner checks, lease
updates, locking, and required evidence fields. Direct edits bypass the state
checks and are prohibited. `AGENTS-LOG.md` is an
append-only activity history, not the current task state. `docs/STATUS.md` is
a dated project summary, not an assignment board.

## 1. One task, one owner

Every assigned task has a permanent ID in this format:

```text
UNITY-YYYYMMDD-NNN
```

Use `python3 scripts/taskctl.py create <title> --actor C` to allocate a unique
ID; `taskctl` derives it from the UTC date and scans active and closed rows.
The ID is never reused, including after cancellation or discovery that the
issue is already fixed. The coordinator or May records the task and owner on
the private task board before work starts. Only that owner changes its state.
Allocate IDs in UTC date order starting at `001`; use the highest number
already allocated for that date plus one, including closed tasks.
The assignment lease is eight hours, renewed at state changes and before long
operations; expiration does not reassign a task automatically. The coordinator
may reassign it only after confirming the previous owner is idle. Do not use
peer messages as a task lock.

The allowed task states are:

```text
BACKLOG
CLAIMED
INVESTIGATING
READY_FOR_FIX
IMPLEMENTING
VERIFYING
REVIEW
READY_TO_PUBLISH
PUBLISHED
DONE
```

Side states are `ALREADY_FIXED`, `NOT_REPRODUCED`, `NOT_APPLICABLE`,
`DEFERRED`, `BLOCKED`, `REJECTED`, and `DUPLICATE`. `BLOCKED` records the
state to resume from. The other side states are closed outcomes; reopening
work gets a new task ID. `taskctl` moves closed rows into the Closed tasks
section.

Normal transitions:

```text
BACKLOG → CLAIMED → INVESTIGATING → READY_FOR_FIX → IMPLEMENTING
         → VERIFYING → REVIEW → READY_TO_PUBLISH → PUBLISHED → DONE
```

An investigation can close as `ALREADY_FIXED`, `NOT_REPRODUCED`, `DEFERRED`,
`NOT_APPLICABLE`, `BLOCKED`, `REJECTED`, or `DUPLICATE`. During `VERIFYING`,
the physical task owner completes and records the regression test, relevant
tests, build, and live check on their assigned VM. `REVIEW` is a separate,
ephemeral Verifier subagent reading that evidence and the diff. For a package,
`PASS` advances to `READY_TO_PUBLISH`; `FAIL` returns to `IMPLEMENTING`; `INCOMPLETE` moves to
`BLOCKED` with resume state `REVIEW` until the evidence is supplied. A strictly
mechanical packaging-only change may skip independent review only under the
`NOT_APPLICABLE` exception in section 6; that path advances from `VERIFYING`
to `READY_TO_PUBLISH` after the release gate is complete.

Every task has a kind, recorded as `task_kind` in its evidence; it decides the
path to `DONE`. A task that changes several things takes the first kind that
applies in this order:

| Kind | What it changes | `READY_FOR_FIX` needs | `VERIFYING` needs | `DONE` |
|---|---|---|---|---|
| `package` | a source package we build or publish | the section 2 defect card | `regression_test`, `build_manifest` | only from `PUBLISHED` |
| `tool` | code that changes behaviour and is not a package (`scripts/*.py`, hooks) | the section 2 defect card | `regression_test`, `validation_record` | only from `REVIEW`, with the Verifier's `PASS` |
| `operation` | shared infrastructure: repositories, VMs, archive state | `scope`, `chosen_approach`, `existing_state_check` (what is already there), `authorization` {`approved_by`: May or C, `reference` to where the approval is recorded, `scope`} | `validation_record` | from `VERIFYING`, or `REVIEW` with `PASS` |
| `documentation` | documentation and research records | `scope`, `chosen_approach` | `validation_record` | from `VERIFYING`, or `REVIEW` with `PASS` |

Every kind records `architectural_task`, `design_challenger_required` and
`correct_layer` at `READY_FOR_FIX`, and needs the Design Challenger's
`APPROVE` when required. `READY_FOR_FIX` means "approach recorded, ready to
implement" for every kind. Only package tasks enter `READY_TO_PUBLISH` or
`PUBLISHED`. A legacy task whose evidence has `package_change: true` and no
`task_kind` is a package; evidence carrying `build_manifest`, `release_gate`,
`candidate_version` or `version_safety` is always a package. From
`READY_FOR_FIX` on, `taskctl` refuses a transition whose kind it cannot
resolve, and it records the kind in `<task-id>.kind` beside the evidence at
the first transition that resolves it; later evidence must keep that kind.
`taskctl`
requires a machine-readable evidence JSON at
`~/coordinator/evidence/<task-id>.json` (or an explicit `--evidence` path) for
transitions; it validates stage-required keys before changing the board. A package
change may reach `DONE` only after `PUBLISHED`. A task is never marked done
just because the agent finished editing.

## 2. Evidence card before code

Before changing package code, create or update the task's record in
`docs/research/<task-id>-<topic>/README.md`. Use these fixed fields; write
`UNKNOWN` when a fact has not been established, and label each statement
`FACT`, `INFERENCE`, or `HYPOTHESIS` where that distinction matters.

```yaml
task_id: UNITY-YYYYMMDD-NNN
package: source-package-name
target_series: resolute
issue: LP-or-upstream-id-or-local-description
status: REPRODUCED | NOT_REPRODUCED | UNKNOWN
issue_search_result: FOUND | NOT_FOUND | UNKNOWN
source_version: exact-source-version
binary_version: exact-installed-version
source_commit: full-commit-or-UNKNOWN
observed: exact behavior and conditions
expected: exact expected behavior
reproduction: command or numbered steps
evidence: paths to logs, screenshots, test output, and boot identity
root_cause: code path and evidence, or UNKNOWN
invariant: behavior the code must preserve
existing_fix_result: one fixed value from section 3
candidate_approaches:
  - approach and measured cost
chosen_approach: exact approach or NONE
why_chosen: evidence-based reason
alternatives_rejected:
  - alternative and measured reason
code_risks:
  ownership_lifetime: checked | not_applicable | UNKNOWN
  callbacks_cancellation: checked | not_applicable | UNKNOWN
  threading_reentrancy: checked | not_applicable | UNKNOWN
  ABI_API_file_list: checked | not_applicable | UNKNOWN
unknowns:
  - unanswered checks; use [] when none
```

For `package` and `tool` tasks (section 1): do not enter `READY_FOR_FIX`
until the issue is reproduced or the task is an
explicit build/packaging failure with a captured failing build, the
`existing_fix_result` is `NOT_FIXED`, and `issue_search_result` is `FOUND` or
`NOT_FOUND` with evidence. If a fix or patch already exists, verify its scope
and package state and close as `ALREADY_FIXED`, or create a new maintenance
task; do not write a duplicate patch. Record root-cause evidence and the
invariant before choosing a code change. A plausible root cause is not a
proven one. Add these evidence-card fields when applicable:

```yaml
design_challenger_required: true | false
design_review_result: APPROVE | REVISE | INCOMPLETE | NOT_REQUIRED
architectural_task: true | false
root_cause_mechanism: exact mechanism, not just symptom
correct_layer: why this code location owns the invariant
defensive_workaround_rejected: why a convenient guard elsewhere is wrong
```

The evidence must explain the mechanism, the affected invariant, and why the
changed location is the correct layer. Mark both architecture fields
explicitly; `architectural_task: true` requires a Design Challenger and an
`APPROVE` result before implementation. A null check or early return is not
accepted merely because the crash disappears. A defensive workaround is valid
only when the evidence shows that boundary owns the failure. For material
architecture, shared-library, lifetime, ABI/API, component-boundary, package
version, or new-module choices, run the temporary Design Challenger before
implementation and record its result; typos and local mechanical changes skip it.

## 3. Fixed outcomes for finding an existing fix

Search in this order and record the exact version, commit, bug, or patch found:

1. Installed package and source identity: `apt-cache policy`, `apt-cache
   showsrc`, `dpkg -S`, package metadata, and the installed system's actual
   session/component use.
2. This repository: package branches, all relevant refs and tags, patch queues,
   `docs/research/`, `docs/DECISIONS.md`, and `docs/PATCHES.md`.
3. Other work: `~/coordinator/TASKS.md`, `~/AGENTS-LOG.md`, closed/deferred task
   evidence, and records from the other builder. Check whether an equivalent
   task is active, finished, rejected, or waiting on a decision.
4. The target Ubuntu series, its updates and proposed pockets, then the current
   development series and Debian.
5. Upstream history, releases, issue tracker, and merge requests. Search by
   symptom and exact error as well as by the suspected cause.

Discovery and validation are separate. An investigator reports a
`CANDIDATE_FIX` with commit/version and scope; the task owner checks that the
change fixes this exact reproduction and applies to the target package before
recording one of the final outcomes below. A candidate found by search is not
an `EXISTING_FIX` until the owner validates its scope.

The result must be exactly one of:

```text
FIXED_LOCAL
FIXED_IN_TARGET_UBUNTU
FIXED_IN_NEWER_UBUNTU
FIXED_IN_DEBIAN
FIXED_UPSTREAM
PATCH_ALREADY_EXISTS
NOT_FIXED
UNKNOWN
```

`NOT_FIXED` requires a dated search record covering the applicable sources.
The twenty-minute search budget in `CLAUDE.md` is a time limit, not evidence:
if the search is incomplete when time is up, record `UNKNOWN`, not
`NOT_FIXED`. `UNKNOWN` does not support a claim that no fix exists and blocks
package implementation and publication. The coordinator asks May whether to
extend the search or defer the task. `NOT_FOUND` under `issue_search_result`
means no matching issue was found in the named trackers; it does not prove no
one has reported the problem elsewhere.

When a fix exists in a newer release, record one decision:

```text
BACKPORT_PATCH
CARRY_NEWER_RELEASE
NO_CHANGE_ALREADY_FIXED
DEFER
```

If considering a newer source release, build it in the target-series chroot and
measure its build dependencies and unrelated changes. A versioned build
dependency is a claim to check against the build system, not by itself proof
that the release cannot be carried.

## 4. Implementation rules

- One task and one underlying defect per patch. Do not bundle cleanup,
  renaming, formatting, refactoring, or unrelated warning fixes.
- Keep the patch as small as the proven root cause permits. Do not add a
  defensive check at a convenient call site if the evidence places the defect
  in ownership, lifecycle, ordering, or a lower shared layer.
- Add a focused regression test when the project has a test seam. Demonstrate
  that it fails on the unmodified package, then passes with the fix. Modify an
  existing test only when the bug is in that test or the test change is
  essential to express the corrected behavior; explain that choice in the
  evidence card. If a regression test cannot be added, say why and provide the
  strongest available reproduction instead of claiming one.
- Where applicable, inspect ownership/lifetime, callback and cancellation
  paths, threading/reentrancy, error handling, and ABI/API/file-list effects.
- Run the package's relevant existing tests and a clean `sbuild` for the
  target series. Record exact commands, source commit, environment, and
  results. Do not infer ABI/API stability, file-list stability, or behavior
  outside the measured cases.
- Preserve the exact source diff and explain every changed line. Update
  `docs/PATCHES.md` for carried patches and append a decision to
  `docs/DECISIONS.md` when choosing among materially different approaches.

## 5. Independent verification

For every behavior fix, and every build fix with more than a mechanical
packaging change, a verifier other than the implementer checks the evidence and
diff. Use the `bugfix-verification` skill. The verifier does not edit the
patch. It tries to disprove the result by checking:

- the original scenario still fails on the unmodified version;
- the patched version fixes that exact scenario;
- a nearby counterexample or lifecycle path remains correct;
- the patch addresses the proven root cause and preserves the invariant;
- the diff is no broader than needed;
- relevant tests, build result, packaging contents, and stated limitations
  match the evidence.

The verifier records `REVIEWED` when it has inspected the implementation and
evidence. For a complex behavioral bug, it separately records
`INDEPENDENTLY_REPRODUCED` only when it personally reproduces the original
failure and patched result; reading the implementer's log is not reproduction.
Small changes need not require an independent second VM. The verifier returns
exactly `PASS`, `FAIL`, or `INCOMPLETE`, with evidence,
and classifies any failure using one or more fixed finding values:

```text
FIX_INVALID
FIX_PARTIAL
TEST_INVALID
ROOT_CAUSE_UNPROVEN
PATCH_TOO_BROAD
```

`PASS` corresponds to `PATCH_CORRECT`.
Only `PASS` advances a behavior fix to `READY_TO_PUBLISH`. A `PASS` review
without an independently reproduced result must say `REVIEWED`; it must not
claim independent reproduction. `INCOMPLETE` names
the missing proof; it is not a pass. Run the verifier in a separate, ephemeral
subagent context using `.claude/agents/adversarial-verifier.md`. A and B remain
focused on their own assigned tasks; do not interrupt one to review the
other's task. The implementer alone operates its assigned VM and supplies the
runtime evidence. The verifier does not edit the patch, own the task, or
operate a VM. If it cannot establish a verdict from the diff and evidence, it
returns `INCOMPLETE` and the publish gate stays closed. Do not add another
permanent team role. Skills define repeatable procedures; they do not execute
automatically or own tasks. Physical agents A and B retain their assigned
VMs, coordinator C assigns and tracks tasks, and temporary Investigator and
Verifier subagents do bounded research or read-only review without persistent
task or VM ownership.

## 6. Version and publish gates

Before building and again immediately before publishing, record the result of
the `package-version-safety` skill. The allowed results are:

```text
SAFE
UNSAFE
REPLACES_SECURITY_UPDATE
BLOCKS_FUTURE_UPDATE
UNKNOWN
```

Version safety is decided from a measurement, never from typed values.
`scripts/apt_view.py` builds an isolated apt state (the host's apt
configuration is not used) from `docs/apt/target.sources` and
`docs/apt/preferences.d/` - the Ubuntu archive pockets and pins of the
reference target system - and, for a full view, our repository as the gated
aptly snapshot will publish it: the snapshot's `.deb`/`.ddeb` list becomes a
local repository whose Release has our publication's Origin, Label, Suite and
Codename (pass `--release` for the gate's prefix and distribution; the
publisher passes the same, and refuses a different model identity). It records the source package's highest version per pocket
(`Sources` indices), apt's candidate for every binary of the build manifest
(with an empty dpkg status), the snapshot's name and package-list hash, and
each fetched Release's hash and Date; any fetch failure refuses.
Multi-Arch and Provides are not modelled: the target is single-arch amd64 and
only concrete package names are checked.

`scripts/version_safety.py --view <view.json> --manifest <manifest.json>`
then decides: `SAFE` only if the candidate source version is newer than the
highest version in resolute and -backports (otherwise `UNSAFE`), -updates and
-security (otherwise `REPLACES_SECURITY_UPDATE`) and -proposed (otherwise
`BLOCKS_FUTURE_UPDATE`: a pending Ubuntu version not older than ours would
supersede ours when it migrates), and every built binary, a binNMU included,
is apt's candidate at its own version. A source in no pocket is "not in
archive" and passes the ordering part. Before a build, `apt_view.py
--source-package <name>` and `version_safety.py --view <pockets.json>
--pre-build --candidate-version <v> --source-commit <c>` check the ordering
only; that result is never `SAFE`. Only `SAFE` is publishable; `UNKNOWN`
stops publication until the missing measurement exists. A `SAFE` version of
ours can still shadow a later Ubuntu update that sorts below it; watching for
that is monitoring, not this gate. Newer-series versions are optional context
and do not decide safety for the target series.

`READY_TO_PUBLISH` requires all of the following:

```text
task_state: READY_TO_PUBLISH
source_tree: CLEAN
source_provenance: PUSHED
source_commit: PRESENT_IN_REMOTE_REF
build_manifest: PASS + SHA256
source_tree_hash: EXACT_MATCH
artifact_sha256: VERIFIED
target_series_build: PASS
version_safety: SAFE
verification_result: PASS | NOT_APPLICABLE
patch_and_decision_docs: COMPLETE
peer_notice: ACK | COORDINATOR_CONFIRMED_NO_CONFLICT
tested_build: this_build | same_chroot | buildinfo_identical (+ target_test)
```

For a strictly mechanical packaging-only change, `verification_result` may be
`NOT_APPLICABLE` only when the evidence record states
`verification_scope: MECHANICAL_PACKAGING_ONLY` and explains why there is no
behavioral claim to verify. Use `docs/TASK-EVIDENCE-TEMPLATE.json` for the
private taskctl record and `docs/RELEASE-RECORD-TEMPLATE.json` for the gate
generator input. Generate the gate with `scripts/create_release_gate.py`; do
not hand-author it. Build with `scripts/build_sbuild.py`, which records the clean source commit and
tree hash, exact `sbuild` command, timestamps, log hash, and source/binary
artifact hashes. The gate and evidence manifest must be pushed before
publication, along with the source package commit. `scripts/publish_aptly.py --gate FILE` accepts no aptly
arguments: it reads distribution, prefix, and snapshot only from the gate,
checks the manifest and artifact hashes, confirms the exact source and binary
versions appear in the named snapshot, requires the gate-time apt view (the
release record's `version_check`) to be no older than four hours, to measure
the gate's snapshot and to be `SAFE`, and immediately before the switch runs
`apt_view.py` and `version_safety.py` again. It refuses unless that
switch-time view is `SAFE`, has the same snapshot package-list hash, no
archive Release older than at gate time or past its Valid-Until, or
other apt inputs (`docs/apt/`, which must be committed and clean) than at gate
time; the switch-time view goes into the publication record. It executes the fixed `publish switch`, checks `aptly
publish show`, and writes a write-once record at
`~/coordinator/publish-records/<task-id>.json`. `taskctl` requires that record,
checks its gate hash and publication details, requires its switch-time
version check to be `SAFE` for the published snapshot, and confirms the live Aptly
snapshot before allowing `PUBLISHED`. The target check remains separate and
must point to an existing target-verification record. The gate and manifests are
traceability evidence; they do not cryptographically prove that a human
assertion is true. Direct `aptly publish` forms are also blocked by the Bash
hook as a best-effort safety net.

Aptly freeze. A freeze protects the live publication state and
/srv/aptly.

- **Lifecycle.** Only May declares and lifts a freeze. C records the fact,
  the start and end times and the scope in the coordinator log. Agents and
  subagents never treat a freeze as lifted and never widen its exceptions.
- **Default.** While a freeze is in force, an agent or subagent must not
  call `aptly publish` directly in any form, including `show` and `list`,
  except as allowed by the exceptions below.
- **taskctl exception.** The internal `aptly publish show` that
  `scripts/taskctl.py` runs as part of an authorized publication workflow,
  after the corresponding gate has passed. It covers only `taskctl.py` and
  only `aptly publish show`, never manual or direct calls by agents or
  subagents.
- **Rehearsal exception.** Direct `aptly publish` commands are allowed only
  for the rehearsal phase of a specific task that May has explicitly
  authorized, and only on an isolated aptly state. For such a command the
  command guard checks:
  - every place aptly writes lies inside the authorized rehearsal root:
    rootDir, publish endpoint roots, package pool storage, the database
    and its dbPath;
  - remote (S3, Swift, Azure) endpoints are absent;
  - no link leads out of the root (UNITY-20260927-057).

  The authorization takes effect only through a dated marker that C writes
  after May's approval (task, rehearsal root, validity window, reference to
  the approval). The guard checks it and logs every rehearsal command it
  allows. The exception gives no right to /srv/aptly or to any other live
  aptly state. It ends automatically when the rehearsal ends: C removes the
  marker, or it expires.
- **Live-phase exception.** Applies to the live phase of a task that May has
  explicitly authorized. The first is UNITY-20260927-047 phase L, allowance
  UNITY-20260929-008.
  - The command guard admits only the exact command strings in the reviewed
    list `.claude/hooks/live-commands.json`, byte for byte, each run as one
    foreground Bash call.
  - The guard checks that the pinned aptly config is unchanged.
  - The exception takes effect only through C's dated marker
    `~/coordinator/live-authorization.json`. The marker records May's GO,
    one session, a window of at most 6 hours, the list's sha256, and a
    reference to the task's backup and preflight record.
  - Every admitted command is logged to `~/coordinator/live-log.jsonl`.
  - It covers nothing else.
  - Known limit: a shell function, or a dynamic-loader variable such as
    `LD_PRELOAD`, in the agent's own profile or environment could stand in
    for the binary or run code inside it. The guard refuses only when it
    finds one in the profile files, the shell snapshots or its own
    environment.
  - It ends when the live phase ends: C removes the marker, and removes the
    list at the task's DONE.

Build manifest artifacts. `scripts/build_sbuild.py` records the `.dsc` and
every file of the build's `.changes`; `scripts/publish_aptly.py` applies one
rule per kind and rejects anything else:

- `source` (`.dsc`): must be in the snapshot as `<source>_<version>_source`.
- `binary` `.deb` and `.ddeb`: Package, Version and Architecture are read
  from the file and must match the manifest record. The binary must belong
  to this source and version by dpkg's rule, read from the file's Source
  field (`Source: name` or `Source: name (version)`; missing parts default to
  the binary's own), so a binNMU or a `-dbgsym` with its own version is
  accepted. It must be in the
  snapshot as `<Package>_<Version>_<Architecture>`, exactly once, with the
  manifest's sha256 in aptly's `SHA256` field (UNITY-20261008-002).
- `source_file`: a file the `.dsc` names (`.orig.tar.*`, `.debian.tar.*`, a
  native `.tar.*`, `.diff.gz`), recorded with the `.dsc`'s sha256. The set must
  be exactly the `.dsc`'s list, and the snapshot's source package (aptly keeps
  it as one record with all its files) must consist of exactly the `.dsc` and
  these files with these hashes, read with `aptly snapshot search -format
  '{{index . "Checksums-Sha256"}}'`. A regenerated source with the same name
  and version is refused.
- `binary` `.udeb`: rejected. The publication has no debian-installer index,
  so a udeb would reach the snapshot but not the published repository.
- `buildinfo`, `changes`: provenance only. They are hashed with the other
  artifacts and never expected in a snapshot.
- Any other kind: rejected until a rule for it is added here.

Extra build dependencies (UNITY-20260929-013). A package that needs a build
dependency the target series' archive does not provide in a usable form
(unity: the archive's nux breaks its configure step) is built with
`build_sbuild.py --extra-package DEB` (repeatable). Each `.deb` is checked
before sbuild starts (a readable regular `*.deb`, not a udeb, architecture
`all` or the build architecture, valid Debian name and version fields, no
second file of the same name, the same file twice, or a second file of the
same package in any architecture), copied
to `OUTPUT/build-dependencies/`, and the copy is given to sbuild. After the
build the copies must be unchanged and each package must appear at its
version in the `.buildinfo`'s `Installed-Build-Depends` - sbuild adds them to
apt without a pin, so one not newer than the archive's is not used and the
build is refused. The manifest then carries an optional
`build_dependencies` list (file, sha256, size, package, version,
architecture, source, the path given, the resolved path, whether the same
bytes are in our published pool, and where). `artifacts` is unchanged.
`create_release_gate.py` and `publish_aptly.py` check that list when it is
present (`scripts/build_dependencies.py`): the name and version fields are
valid Debian fields (so none can steer the pool path), each copy is in the
manifest's `build-dependencies/` and matches its sha256, and the same bytes
are in our published
pool (`/srv/aptly/public/pool`, at the package's own pool location; the
unpublished `candidate/` staging does not count). A publishable build
depends only on extra packages we publish. Without the option nothing
changes.

The build chroot (UNITY-20260929-016, May's decision 2026-09-29).

- **What the builds use.** Every build runs in a chroot tarball made from a
  pinned snapshot of the Ubuntu archive:
  `https://snapshot.ubuntu.com/ubuntu/<T>`, with the target series' release,
  `-updates` and `-security` pockets and the components main, universe and
  restricted (no multiverse, no -backports, no -proposed).
- **Why the snapshot.** The tarball's `/etc/apt/sources.list` keeps exactly
  those three lines. sbuild's `apt-get update`/`dist-upgrade` in each build
  therefore sees the same archive state as the tarball ("0 upgraded"). The
  same tarball gives the same build dependencies, now and later.
- **Creating a tarball.** `python3 scripts/sbuild_chroot.py create
  [--snapshot <T>]`, where `<T>` defaults to now. It writes
  `~/.cache/sbuild/chroots/<series>-<arch>-<T>.tar.zst` and a sidecar
  `.json`: the sources, each pocket's InRelease Date, the mmdebstrap argv,
  the package list and the sha256. It never overwrites.
- **What `build_sbuild.py` does.**
  - It takes `--chroot-tarball PATH`; the default is the newest tarball
    with a sidecar.
  - Before sbuild it refuses a symlink, a tarball without a matching
    sidecar, one whose sources are not exactly the snapshot pockets, and a
    snapshot more than 7 days old. `--allow-old-chroot` overrides the age
    limit, and the manifest records it.
  - It passes `--chroot-mode=unshare --chroot=<path>` and
    `SBUILD_CONFIG=build/sbuild-config.pl`. That file is read after the
    user's own sbuild config and resets what could add apt sources, packages
    or change the chroot: extra repositories and keys, extra packages (only
    the command line's `--extra-package` copies remain), external and setup
    commands, unauthenticated packages, the apt-get command, the build
    environment command and bind mounts; it keeps apt update and
    dist-upgrade on.
  - After sbuild it refuses, with no manifest, a tarball that changed, a
    log without `I: Unpacking <path> to`, a chroot sbuild built on its own
    ("Creating chroot on-demand"), a log without the InRelease of each of
    the three pockets from the snapshot, and any apt fetch from elsewhere -
    another mirror, another snapshot, or a local repository other than
    sbuild's own resolver archives
    (`file:`/`copy:/build/reproducible-path/resolver-*/apt_archive`), and any
    package sbuild copies into that archive other than this build's
    `build-dependencies/` copies. This guards against ordinary settings in
    the user's sbuild config; the config is executable Perl, and a
    deliberately hostile one is out of scope.
  - The manifest's `chroot` key records the tarball, its sha256, `<T>`, the
    sources and the InRelease lines.
- **Refresh.** Create a new tarball when the current snapshot is more than
  7 days old, or when a task needs a newer archive state.
- **Test build and gated build** (UNITY-20260929-020). A build that will
  be tested on target is made with `build_sbuild.py`, and its manifest,
  `.buildinfo`, `.changes` and the target test record are committed. The
  release record says what the target test installed and how it is tied to
  the gated build, and `create_release_gate.py` refuses otherwise:
  - `target_test`: `{"record": <committed record>, "debs": {<file>:
    <sha256>}}`. These are the debs the target test installed. The record
    must name each one by its exact file name. Record paths are
    repository-relative, without `..` or symlinks.
  - `tested_build: "this_build"`. The debs are binaries of the gated build,
    matched by name and sha256.
  - `tested_build: "same_chroot"`, with `tested_manifest` (committed). The
    debs are binaries of the tested build. The gated build was made with
    `--tested-with` that manifest. Both builds have the same chroot sha256,
    source commit and tree, and extra build dependencies. A gated build on
    the tested tarball may use `--allow-old-chroot`.
  - `tested_build: "buildinfo_identical"`, with `tested_manifest` and
    `tested_buildinfo` (both committed). For a tested build on another
    tarball, or from before UNITY-20260929-016:
    - the tested manifest must be a `build_sbuild.py` manifest (schema 1,
      with its source commit and tree; `chroot` is not needed) listing the
      debs and that `.buildinfo`;
    - both builds must have the same source commit and tree and the same
      extra build dependencies (package, version, architecture, sha256);
    - the gated build's `.buildinfo` must match on Source, Binary,
      Architecture, Version and Build-Architecture, with identical
      Installed-Build-Depends and no package listed twice.

    Any difference means a new target test. A tested build made without a
    `build_sbuild.py` manifest (plain sbuild) cannot use this mode: nothing
    else ties a binary build to its source. It needs a new target test.
  - A gated manifest without `chroot` (built before UNITY-20260929-016) is
    refused.

  The gate records the mode and every hash as `tested_build`.
  `publish_aptly.py` recomputes it from the committed files and refuses on
  any difference. The recorded list of debs is the attestation of what was
  tested; the tools check that it is consistent with the builds, not that
  it is complete.
- **Retention.** Keep every tarball named by a committed manifest; others
  may be deleted by hand. `~/.cache/sbuild/resolute-amd64.tar.zst` (release
  pocket only, 2026-09-22) is the record of the builds up to 2026-09-29.

Publication sequence (UNITY-20260929-009). These rules come from publishing
between 2026-09-29 and 2026-10-08. Each rule is marked by who enforces it:
- **[tool]**: a script refuses when the rule is broken.
- **[process]**: only the owner, C and the Verifier check it.

The steps run in this order. When a step refuses, go back to the step that
caused it.

1. **Slot.** Ask C for a publication slot, listing the task's known gaps
   (rule K).
   - One publication runs at a time. The repository `unity-resolute` is
     shared, so a snapshot carries every record in it, including another
     task's unpublished ones. **[process]**
2. **Gated build** in the worktree of the task that carries the
   publication.
   - `--source-repo` must be `packages/<source>` under the repository the
     gate script runs from. `create_release_gate.py` refuses otherwise
     ("source repository must be a package checkout under packages/"), and
     `publish_aptly.py` does the same.
   - A build made in another task's worktree therefore cannot be gated.
     Rebuild in this worktree and tie the rebuild to the tested build with
     `tested_build` (rule B). **[tool]**
3. **Database backup.** Run `python3 scripts/backup_aptly_db.py --task
   UNITY-YYYYMMDD-NNN` (UNITY-20261008-004). **[tool]**
   - **What it does.** It copies the live `db/` to
     `~/backups/<task>-<UTC stamp>/` (mode 0700), with a shared flock held
     on `db/LOCK` for the copy and the comparison. Next to the copy it
     writes `db.sha256` and `backup.json`.
   - **When it refuses** (exit 2, nothing created):
     - `db/` or `db/LOCK` is missing;
     - the lock is busy;
     - a repository tool process is running;
     - the target exists, lies inside the live root, or cannot be
       created.
   - **Exit codes.** 0 means a complete copy equal to the live db. 1 means
     the copy failed or differs; it is left in place for inspection, and
     you must not go on. 2 is a refusal.
   - **Scope.** The copy covers `db/` only. That is enough for steps 4 and
     5, which change only `db/`. It is not a backup for `publish switch` or
     `db cleanup`, which change `public/` and the pool.
   - **Guard.** It denies a target path that ends in `/aptly`, so leave the
     default name or choose another.
   - **Record.** Put the backup path and its `list_sha256` in the card.
     **[process]**
   - The `tools/backup-db.py` copies in older task cards are records of
     those tasks.
4. **Repository and snapshot.** **[process]**
   - `aptly repo add unity-resolute <files>`: exactly the artifacts of the
     gated build's manifest. That is the `.dsc`, which carries its source
     files, and every `.deb` and `.ddeb`, but no `.buildinfo` or
     `.changes`.
   - Check each pool file's sha256 against the manifest. This is an early
     check: since UNITY-20261008-002, `publish_aptly.py` also checks the
     bytes in the snapshot (step 5).
   - `aptly snapshot create unity-resolute-YYYYMMDD-NNN from repo
     unity-resolute`, with the task's ID.
   - `aptly snapshot diff <live snapshot> <new snapshot>` must show only
     this build's records added, nothing removed or changed. The diff
     compares names and versions, not bytes. The pool check above, and the
     publisher (step 5), cover the bytes.
   - Commit the diff as `gate/snapshot-diff.txt`. This is new with this
     section, and the gate does not pin it.
   - The live snapshot is the one in the publish record with the latest
     `published_at` in `~/coordinator/publish-records/`. Cross-check it
     with the files under `/srv/aptly/public`. Never read it with
     `aptly publish`, not even `show` or `list`.
   - The guard admits `repo` and `snapshot` subcommands. Nothing checks
     the repository name, the snapshot name or the diff.
5. **Replacing unpublished records (`-r2`)** when the records in the
   repository are not the bytes to be published, for example after a
   rebuild:
   1. take a fresh database backup (`scripts/backup_aptly_db.py`, step 3);
   2. `aptly repo remove` those records, with a dry run first;
   3. `aptly snapshot drop` the unpublished snapshot;
   4. `aptly repo add` the new build's artifacts, then check the pool
      sha256 values;
   5. create the snapshot again under the same name with `-r2`.

   The old pool files stay as orphans until the pool cleanup task.

   These steps are **[process]**. The result is **[tool]**: before the
   switch, `publish_aptly.py` (`check_gated_snapshot`, UNITY-20261008-002)
   checks the snapshot. It requires:
   - every manifest binary exactly once, with its sha256;
   - exactly one source package of this name and version, made of exactly
     the `.dsc` and its files with their sha256.

   A regenerated source or binary of the same name and version is refused
   ("aptly snapshot <s> does not hold the build's artifacts: missing
   [...], other sha256 [...]"). `taskctl` uses the same check for a later
   live snapshot at `PUBLISHED`.
6. **Version safety.** **[tool]**
   - Run `scripts/apt_view.py --manifest ... --snapshot <new> --write
     gate/version-check.json`, then `scripts/version_safety.py`. The result
     must be `SAFE`.
   - The defaults of `apt_view.py --release` and of the gate's `--prefix`
     match the live publication: prefix `.`, distribution `resolute`. Do
     not pass another prefix.
   - At publication, the view must be no older than four hours.
7. **Peer notice** before the gate is created.
   - Notify the other package owner and wait for the ACK.
   - If the direct send fails, append to that agent's inbox and wait. A
     failed send is not an ACK.
   - C may record `COORDINATOR_CONFIRMED_NO_CONFLICT` only when the other
     agent is confirmed idle.
   - The release record carries the value. `create_release_gate.py` and
     `publish_aptly.py` refuse any other value. **[tool]**
   - The ACK itself, and any other human claim such as a Verifier
     judgment, needs cited evidence and an independent reviewer.
     **[process]**
8. **Evidence first, gate last.**
   - Finish the card, the verification record, the patch record, the
     release record and the version check. Commit and push them, together
     with the build manifest and its `.buildinfo`.
   - The gate and the publisher refuse a gated build whose `.buildinfo`
     is not committed (UNITY-20261008-003). **[tool]**
   - Then run `scripts/create_release_gate.py`. It refuses unless the
     board state is `REVIEW` or `READY_TO_PUBLISH`.
   - The gate pins the sha256 of the build manifest, of `tested_build` and
     of the evidence manifest. The evidence manifest covers the card, the
     verification, patch and release records, the version check, and a
     decision record when the task requires one. `publish_aptly.py` recomputes every one of them.
   - Any later edit to a pinned file refuses the publication, even one line
     in the card. Regenerate the gate and have C check it again before May
     is asked. **[tool]**
   - Record the gate path in the task evidence. Commit and push the gate.
9. **`READY_TO_PUBLISH`.**
   - Run `taskctl.py` from the task worktree, so that its repository is the
     one that holds the gate. Each script takes its repository from its own
     location (`scripts/..`), not from the current directory.
   - With base's `taskctl.py`, a relative gate path resolves in base
     ("cannot read release gate"). An absolute path into the worktree is
     refused ("release_gate must stay inside the repository").
   - The same applies to `PUBLISHED` and to `publish_aptly.py` ("gate must
     be inside this repository"). **[tool]**
   - Append a `START` line to `~/AGENTS-LOG.md` with the package and the
     full candidate version.
10. **Publish.** C checks the gate, and May confirms directly in the
    owner's session. Then run `scripts/publish_aptly.py --gate <gate>` and
    nothing else. **[tool]**
    - The publisher refuses unless the gate, the evidence manifest, the
      build manifest and log, the release record, the review evidence and
      the parent repository commit are pushed, tracked, committed and
      clean.
    - It checks the source commit and tree identity, remote-ref ancestry,
      manifest linkage and each artifact hash, and the snapshot content.
    - It never accepts an aptly command from the caller, and it checks that
      the board state is `READY_TO_PUBLISH`.
    - Afterwards, confirm the exact source and binary versions by reading
      the files under `/srv/aptly/public`.
11. **Target verification** on the assigned clean target. **[process]**
    - Upgrade through the repository's normal path. Check `apt-cache
      policy`, the installed version and the package hashes.
    - Test in the users' environment: no drop-in, override, kernel argument
      or test configuration of ours. Include at least one natural boot into
      the session after the upgrade. Remove any test helper used earlier in
      the task first, and record that you did.
    - A `dpkg -i` of build files does not satisfy this gate.
    - One exception exists only with C's approval for the task
      (UNITY-20261002-003). It applies when the target already holds the
      tested build of the same version with other bytes, so `apt-get
      install --reinstall` refuses, and the VM snapshot cannot be restored.
      Then:
      - fetch the published debs with `apt-get download`;
      - check their sha256 against the gated manifest;
      - install them with `dpkg -i`;
      - check that `apt-cache policy` shows the published version as both
        candidate and installed.
    - The target verification record states the test, the repository
      version, the target state, which path was used, and the limitations.
    - `taskctl` requires `target_verified: true` and an existing
      `target_verification_record` file. It does not check their content.
12. **`PUBLISHED`, then `DONE`.** `DONE` requires that all records are
    committed and pushed, and that C has merged the task branch.

Rules used by these steps:

- **B. Tested build.** The target test normally runs on an earlier build.
  The gate ties it to the gated build with `tested_build` (see "Test build
  and gated build" above).
  - Use `same_chroot` when the gated build was made on the tested tarball
    with `--tested-with`.
  - Use `buildinfo_identical` when the two builds differ only in container
    bytes. For example, the source tarball takes its files' mtimes from the
    checkout, so two clones of one commit give different `.tar.*`, `.dsc`
    and `.deb` bytes.
  - The tool compares the source commit and tree, the extra build
    dependencies, the `.buildinfo` identity fields and
    `Installed-Build-Depends`. **[tool]**
  - It does not compare file contents. The owner shows that only container
    bytes differ by comparing file lists, control fields and md5sums
    (UNITY-20261002-003). **[process]**
  - The tested `.buildinfo` is committed with its manifest. Since
    UNITY-20261008-003, `.gitignore` admits `.buildinfo` files in
    `docs/research/<task>/<build dir>/`. A file elsewhere needs
    `git add -f`.
- **P. `published_by`.** A task whose change shipped in another task's
  publication closes through `published_by: {task_id, record_sha256}`.
  `taskctl` requires the following (UNITY-20261008-003). **[tool]**
  - The same `package` and `candidate_version`.
  - Verification `PASS` with a `review_status`.
  - The task's own `build_sbuild.py` manifest, tied to the published bytes
    in one of two ways:
    1. Its `source` and `binary` artifacts equal the publish record, by
       file and sha256.
    2. Otherwise, it is `buildinfo_identical` to the published build. The
       published build is read through the record's `gate_file` and
       `gate_sha256`, then the gate's `build_manifest`. Both builds must
       have the same source commit and tree, the same extra build
       dependencies, the same `.buildinfo` identity fields and the same
       `Installed-Build-Depends`. Both `.buildinfo` files must be
       committed.

  A commit that is only an ancestor of the published one is refused. So is
  a task whose version was not published.
- **K. Known gaps.** A gap known before the gate goes on the board as its
  own task first. It does not wait for the publication or for May. A gap is
  a case not covered, a related bug or a follow-up. **[process]**
- **S. Security material.** A finding that shows how to bypass a lock,
  authentication or permission check stays out of every pushed branch
  until the fix is published. That covers the recipe, the reproduction
  scripts and the runs. Keep the task's records in a local branch. A public
  branch carries only facts that give no recipe. The guard checks force
  pushes only, not content. **[process]**

Example commands, run from the task worktree, for task
`UNITY-YYYYMMDD-NNN` with card directory `$D`:

```sh
python3 scripts/apt_view.py --source-package <package> --write /tmp/pockets.json
python3 scripts/version_safety.py --view /tmp/pockets.json --pre-build \
  --candidate-version <version> --source-commit <commit>
tmux new-session -d -s UNITY-YYYYMMDD-NNN-build \
  "python3 scripts/build_sbuild.py --task-id UNITY-YYYYMMDD-NNN \
  --source-repo packages/<package> --target-series resolute \
  --output-dir $D/build-gate"
# slot from C, then the db backup (step 3; exit 0 required), then step 4:
python3 scripts/backup_aptly_db.py --task UNITY-YYYYMMDD-NNN
aptly repo add unity-resolute <the manifest's .dsc, .deb and .ddeb files>
aptly snapshot create unity-resolute-YYYYMMDD-NNN from repo unity-resolute
aptly snapshot diff <live snapshot> unity-resolute-YYYYMMDD-NNN > $D/gate/snapshot-diff.txt
python3 scripts/apt_view.py --manifest $D/build-gate/<manifest>.json \
  --snapshot unity-resolute-YYYYMMDD-NNN --write $D/gate/version-check.json
python3 scripts/version_safety.py --view $D/gate/version-check.json \
  --manifest $D/build-gate/<manifest>.json --write $D/gate/version-safety.json
# peer notice and ACK; commit and push all evidence; then, last:
python3 scripts/create_release_gate.py --record $D/gate/release-record.json \
  --build-manifest $D/build-gate/<manifest>.json \
  --distribution resolute --snapshot unity-resolute-YYYYMMDD-NNN \
  --output $D/gate/release-gate.json
# commit and push the gate, then:
python3 scripts/taskctl.py transition UNITY-YYYYMMDD-NNN READY_TO_PUBLISH \
  --actor A --evidence ~/coordinator/evidence/UNITY-YYYYMMDD-NNN.json
# after C's check and May's confirmation:
python3 scripts/publish_aptly.py --gate $D/gate/release-gate.json
```

## 7. Canonical fix examples

Promote only independently verified fixes as examples. Every canonical record
uses `docs/FIX-EXAMPLE-TEMPLATE.md` and includes the exact reproduction,
observed/expected behavior, root cause, invariant, rejected approaches, chosen
layer and reason, patch, regression test, before/after results, verifier status,
limitations, and source commit. `CANONICAL_FIX` is allowed only after verifier
`PASS`; a candidate or merely working patch stays non-canonical. Copy
`docs/FIX-EXAMPLE-TEMPLATE.md` into the relevant research record or example
collection. An example is not canonical until it names its source commit,
review result, passing evidence, and known limits. Keep `Why this
implementation` and `Why not these alternatives` explicit so a working but
architecturally misplaced patch is not taught as the preferred solution.

## 8. Policy, live state, and knowledge

- **Policy:** `CLAUDE.md`, this process, `TWO-AGENTS.md`, and `COORDINATOR.md`.
- **Live task state:** private `~/coordinator/TASKS.md`, changed only through
  the locked `scripts/taskctl.py` interface. The board remains the authority
  for task owner and state; `taskctl` enforces the transition graph and
  evidence gates.
- **Activity history:** `~/AGENTS-LOG.md`, append-only; never treat its last
  `START` as current without checking for a later `DONE`.
- **Knowledge:** `docs/research/`, `docs/DECISIONS.md`, `docs/PATCHES.md`, and
  canonical examples in the repository.
- **Agent identity:** `~/coordinator/AGENT-REGISTRY.json` contains current A/B/C
  identities; `~/AGENTS-HISTORY.md` is append-only. The legacy `~/AGENTS.md` is
  retained as historical data, never consulted as the live registry.
- **Session state:** `docs/status/A.md` and `docs/status/B.md` record each
  assigned desktop and work-in-progress details. They do not assign tasks.
- **Project summary:** `docs/STATUS.md` is dated and maintained by the
  coordinator; it is not the live task board.

Keep private coordination notes, credentials, and correspondent drafts out of
the public repository. If a credential was committed, removing it from the
current file does not remove it from Git history; rotate it and follow the
repository owner's history-removal process separately.

## 9. Shell command guard

The project `.claude/settings.json` installs a `PreToolUse` guard for Claude
Code's `Bash` and `Monitor` tools (both run shell text). It tokenizes shell
command lists (newlines, `$(...)`, backticks and heredocs included) and blocks
common forms of broad staging, force pushes (including force refspecs), `aptly
publish`, `xwd`, pattern-based process matches, and dangerous recursive
removal. It handles common command/env/sudo prefixes and absolute executable
paths.

For aptly (UNITY-20260927-058) it does not follow aptly's flag grammar:

- `aptly` must be called literally, with one of `repo snapshot mirror
  package db config serve version graph` as its first command word, and
  without the words `publish`, `task` or `api`.
- Any other mention of aptly is allowed only when it cannot reach a command
  that runs something. It must not be a wrapper, a remote or nested shell, an
  interpreter, a pipe into one, or a copy of the binary.
- Commands made only of plain readers (`grep`, `ls`, `cat`, `git log`,
  `echo`, project scripts such as `taskctl.py`) may mention aptly and
  publish freely.
- The live-phase exception of section 6 (UNITY-20260929-008) admits only
  the strings of `.claude/hooks/live-commands.json`. Each starts
  `/usr/bin/aptly -config=/home/claude/.aptly.conf publish` and runs as a
  foreground Bash call. C's live marker must name the session and the
  list's sha256. Each admitted command is logged to
  `~/coordinator/live-log.jsonl`. The check runs before every other rule,
  and only for a string that starts with that prefix.
- Apart from that, the rehearsal exception of section 6
  (UNITY-20260927-057) is the only allowance for `publish`. The command must start exactly
  `/usr/bin/aptly -config=/var/tmp/aptly-rehearsal/<path> publish`
  (`--config=` also works), with no other flag before `publish`, as one
  plain command with no quoting, expansion, redirection or prefix. The
  config is strict JSON, with every place aptly writes inside
  /var/tmp/aptly-rehearsal. The root is checked for links, hard links and
  mounts. C's dated marker
  `~/coordinator/rehearsal-authorization.json` must name the session, and
  every allowed command is logged to `~/coordinator/rehearsal-log.jsonl`.

In practice:

- Run aptly directly, not through `timeout`, `xargs`, `bash -c` or a
  variable.
- Write `-architectures=amd64` rather than `-architectures amd64`.
- Commit messages go in the heredoc form.
- A Python heredoc that mentions aptly and starts processes is refused. Use
  the Edit and Write tools for files.

Shell syntax, aliases, interpreters that build words at run time, and files
written earlier and run later cannot be reliably secured by this hook
(`docs/research/UNITY-20260927-058-command-guard/`). Use `scripts/safe_git.py
stage|push` for Git updates, `scripts/build_sbuild.py` for package builds,
and `scripts/publish_aptly.py` for publishing. VBox MCP calls have no project hook:
agents can use their disposable VM freely. The MCP server configuration allows
`target-desktop`, `target-desktop-2`, and `oem-test`, and lists `builder-server`
under `never_allowed`. For a restore or suspected shared VBoxSVC failure, use
`docs/TWO-AGENTS.md` and the `vbox-recovery` skill; a `PreToolUse` hook cannot
reliably diagnose or contain a host-wide VBoxSVC incident.

## 10. Merging a task branch into `main`

A task's repository changes live on its task branch (for example
`a/UNITY-YYYYMMDD-NNN` or `b/UNITY-YYYYMMDD-NNN`) until they are merged into
`main`. A task branch never pushes its changes directly into `main`; the merge
happens only through the controlled project workflow, and `scripts/safe_git.py
push` only pushes the current branch to its own ref.

Before merging, verify that:

- the task branch contains only the intended task changes (`git log` and
  `git diff` from the merge base to the branch tip);
- every gate required for the task's state has passed, and the verification
  and review requirements in sections 5 and 6 are satisfied;
- the local `main` is current with `origin/main`;
- neither checkout has undeclared changes that the merge would include.

Merge method:

- **Fast-forward** when it is naturally possible, that is, when `main` has not
  advanced since the task branch was created.
- **`git merge --no-ff`** as the standard method when `main` has advanced. Name
  the task ID in the merge commit message.
- **Do not rebase an already-pushed task branch** solely to make a
  fast-forward possible, and do not rewrite published task-branch history when
  evidence, verification records, or other process artifacts reference its
  commit hashes.

`main` can advance legitimately while another agent is working on a task
(for example, a shared decision record appended to the base checkout), so a
fast-forward cannot be assumed. A rebase performed only to keep an artificial
fast-forward invariant replaces the commits that the task's evidence cites;
`--no-ff` keeps them. See `docs/DECISIONS.md`, 2026-09-27, "Task branches merge
into `main` with `--no-ff` when fast-forward is not possible".

If the merge conflicts, stop it (`git merge --abort`) and return the conflict
to the normal engineering process for resolution. Do not make an ad-hoc
technical decision merely to complete the merge.

After merging, verify the resulting `main` (the expected task commits are its
ancestors and the tree contains only the declared changes), then push `main`
with `scripts/safe_git.py push`. The task ID, task branch, task commit(s), and
the merge (or fast-forwarded tip) on `main` must stay traceable to one another.
