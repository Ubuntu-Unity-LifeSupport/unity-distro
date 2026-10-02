# UNITY-20260927-026: indicator-datetime +unity2's no-time guard

Owner: agent B (target2). This comes from the legacy reconciliation, B-L14,
as PATCH_TOO_BROAD. Besides the main fix (a task with only DUE is placed at
its due date, LP #1848969 and #2099742), indicator-datetime +unity2 added a
guard that leaves out a component with no time at all. The guard was never
shown to be reachable or tested. The task is to prove it reachable and test
it, or to drop it and keep only the main fix. The main fix's regression
must stay fail-before / pass-after. Publication stops at the gate, which is
expected. Aptly freeze applies.

**Outcome: the guard is reachable. It stays, and +unity3 adds the test
that proves it.** The first conclusion, "unreachable, drop it", was wrong.
The Verifier found the path that disproves it; see "Correction" below.

```yaml
task_id: UNITY-20260927-026
package: indicator-datetime
target_series: resolute
issue: local - untested guard in our +unity2 (LP #1848969, #2099742 for the main fix)
status: REPRODUCED
issue_search_result: NOT_FOUND  # our own change
source_version: 15.10+21.04.20210304-0ubuntu6+unity2 (846dfa0; our aptly)
binary_version: indicator-datetime 0ubuntu6+unity2
observed: >
  846dfa0 has two guards: when appointment.begin is unset, get_appointment()
  skips its g_debug and add_event_to_subtask() adds nothing. Its test held
  only a task without dates, which EDS already filters, so the guard was
  never exercised.
root_cause: >
  EDS 3.56.2 itself never generates an instance for a component with a null
  start: in e_cal_recur_generate_instances_sync, intersects_interval() is
  FALSE for a null time. But the engine has its own path:
  - on_event_generated() records the UID of every generated instance of a
    recurring task;
  - fetch_detached_instances() reads the stored components of that UID
    (e_cal_client_get_objects_for_uid);
  - merge_detached_instances() replaces a generated instance with the
    stored override whose RECURRENCE-ID matches (e_cal_component_id_equal)
    and never checks for a start.
  So an override with neither DTSTART nor DUE reaches get_appointment() with
  no time. Without the guard, g_debug formats the unset DateTime and
  DateTime::get() aborts on the m_dt assertion.
root_cause_mechanism: merge_detached_instances() hands a dateless override to get_appointment(); the guard is what keeps it out
root_cause_evidence: >
  logs/07 (experiment 298583b: an override with a RECURRENCE-ID matching the
  generated instance aborts without the guard), logs/08 (the final test,
  with the guard removed: abort); engine-eds.cpp on_event_generated,
  fetch_detached_instances, merge_detached_instances, add_event_to_subtask
invariant: >
  get_appointment() only formats and adds appointments that have a start
  (the guard); a task with only DUE is placed at its due date
existing_fix_result: NOT_FIXED
candidate_approaches:
  - (A) drop the guard - rejected: it is reachable (logs/07, logs/08)
  - (B) keep the guard and add a test for the reachable case - chosen
chosen_approach: B - +unity3 changes only tests (9a00446) plus the EDS directory fix (5a21b08)
design_challenger_required: false  # no code change; a test added
design_review_result: NOT_REQUIRED
architectural_task: false
correct_layer: >
  the guard stays in get_appointment()/add_event_to_subtask(), where the
  engine's own merge path delivers the component; the test in
  test-eds-ics-tasks-without-start, which already covers the no-start cases
defensive_workaround_rejected: >
  moving the check into merge_detached_instances() would duplicate the
  guard for one caller; get_appointment() is where the time is required
code_risks:
  ownership_lifetime: not_applicable
  callbacks_cancellation: not_applicable
  threading_reentrancy: not_applicable
  ABI_API_file_list: checked  # no code change in src/; tests and changelog only
unknowns:
  - only overrides whose RECURRENCE-ID matches a generated instance reach the
    guard. A floating or TZID RECURRENCE-ID that does not match (logs/07)
    is never merged; the matching rules for every form were not mapped
  - an alarm-only path for such an override (add_alarms_to_subtask) was not
    measured separately; it goes through the same get_appointment()
  - other EDS versions are not measured
  - the single test-eds-ics-all-day-events failure in the control e6576ce
    (logs/03) is not explained: the control itself was not rerun. +unity3
    passed it in four later builds (logs/04, 05, 06/08)
```

## Correction (verification round 1: FAIL, ROOT_CAUSE_UNPROVEN)

The first result (+unity3 5d6492d, "drop the unreachable guard") rested on
reading EDS and on logs/02. That run probed a plain dateless task, RDATE,
RRULE, a detached RECURRENCE-ID without a master, and a VALARM. The Verifier
showed that the engine merges stored overrides of recurring tasks itself,
without EDS's filtering, and that the detached probe had no master, so it
never exercised that path. The experiments in logs/07 confirmed the
Verifier:

- f7eb632: a floating override RECURRENCE-ID did not match the generated
  instance (20150623T140000Z), so it was not merged and nothing aborted.
- 298583b: an override whose RECURRENCE-ID matches (UTC) aborted the
  service without the guard. The TZID variant did not match.

5d6492d is superseded (`patches/superseded/`, local branch
superseded/026-drop-guard) and must not be released. Also corrected: the
claim that all-day-events failed through timing flakiness was stronger than
the evidence (see unknowns).

## Finding on the way: indicator-datetime does not build from git

`logs/01`: the unmodified +unity2 (846dfa0) was built from a fresh git clone
with `scripts/build_sbuild.py`. 11 of 29 tests fail, every test-eds-ics-*
one. The reason is that run-eds-ics-test.sh cannot copy `tasks.ics`:
`.local/share/evolution/tasks/system` does not exist. The release tarball
ships `tests/test-eds-ics-config-files/.local/share/evolution/{calendar,tasks}/system`
as empty directories, and git does not keep empty directories. The published
+unity2 (2026-09-26, 29/29) was built from a tree that had them. The chroot's
package versions are unchanged.

+unity3 therefore also creates the directory in `run-eds-ics-test.sh`
(commit 5a21b08, test harness only). Without that, none of the EDS
regression tests, this task's included, runs in our pipeline.

**Why it goes in this upload** (section 4: one defect per patch; the
coordinator asked for a justification or a split).

- It is a second defect, so it is its own commit and its own patch
  (`patches/0001-*`), separate from the guard test (`0002-*`).
- It is not separable from this upload. Our pipeline builds from git
  (`build_sbuild.py`), where the directory does not exist:
  - without 5a21b08 every test-eds-ics-* test fails in dh_auto_test and
    the build of +unity3 fails (logs/01, the control of the unchanged
    +unity2);
  - so section 4's "run the package's relevant tests and a clean sbuild"
    cannot be done for this task;
  - the guard's new test and the main fix's test
    (test-eds-ics-tasks-without-start) cannot fail before and pass after
    (logs/03 and logs/08 need 5a21b08);
  - no +unity3 could be built for publication.
- It changes only test behaviour (`mkdir -p` before `cp`). It is
  idempotent and a no-op on a release-tarball tree, where the directory
  exists.
- The general case, empty directories of the orig that git drops, is
  UNITY-20260928-010 (a check at pipeline level). If that task fixes
  builds from git for every package, this commit becomes redundant but
  stays harmless, and it can be dropped from our patch series then.

## First experiment (logs/02, superseded)

42c0f3f (not for release) is +unity2 without the guard, with probes: plain,
RDATE only, RRULE only, a detached RECURRENCE-ID *without a master*, and a
VALARM. Nothing aborted: EDS filters all of these. This did not cover the
engine's own merge of overrides; see Correction.

## Result

- **Package** (`packages/indicator-datetime`, local branch
  b/UNITY-20260927-026; `patches/0001-*`, `0002-*`):
  - 5a21b08 makes the tests mkdir the EDS tasks directory, so the package
    builds from git;
  - 9a00446 adds to test-eds-ics-tasks-without-start a recurring task
    (DTSTART 2015-06-22T14:00Z, daily, three times) with an override of
    its 06-23 instance (RECURRENCE-ID 20150623T140000Z) that has no
    DTSTART and no DUE. Expected: the 06-22 and 06-24 instances; the
    override is left out and nothing aborts. It releases +unity3, and the
    changelog trailer comes from `date -u`.
  - src/ is unchanged from +unity2.
- **Build** from git (`build/`, `logs/06-build-unity3-guard-kept.txt`):
  29 of 29 tests pass, status successful.
- **Regression** (logs/08): the same test with the guard removed (control
  002c06d, not for release) aborts with `DateTime::get(): assertion
  failed: (m_dt)`. Fail before, pass after.
- The main fix's regression is unchanged (logs/03). Without the due-date
  fallback, the DUE-only task aborts.

## Verification round 2: PASS

Result: PATCH_CORRECT, review status REVIEWED. The Verifier read the logs
and did not rebuild. It confirmed:

- the merge path;
- that src/ is unchanged from +unity2;
- that the test separates "merged and kept out by the guard" from "never
  merged" (the passing log shows only 06-22 and 06-24);
- fail before and pass after (logs/08), and the correction in this card.

Its non-blocking caveats:

- **Version reuse.** The superseded 5d6492d was also +unity3. It never
  reached aptly: the pool holds indicator-datetime 0ubuntu6+unity1 and
  +unity2 only (checked read-only, 2026-09-28). So +unity3 stays the right
  version for 9a00446.
- **The TZID pair "did not match".** The evidence is the first build of
  the test with both pairs, before the TZID pair was removed. That build
  had the guard kept and 29 tests; test-eds-ics-tasks-without-start failed
  only on the expected list. Its actual appointments contained the TZID
  master's 06-23 instance (`recurring-tzid@example.org`, 2015-06-23 10:00
  -0500), next to 06-22 and 06-24, while the UTC pair's 06-23 was missing.
  So the TZID override was not merged. That build's log was overwritten by
  the final build; the list is quoted here from its output.
- logs/07 and logs/08 are summaries; the full sbuild log is only for the
  final build. The earlier logs/04 build log is in git history (8ee9991).

## Status

BLOCKED at the publication gate (047; freeze no. 1). The version check and
release gate need the package in an aptly snapshot.

## Gated rebuild and target test of this build (2026-10-02)

- **Source.** `9a00446` on `Ubuntu-Unity-LifeSupport/indicator-datetime`,
  branch `b/UNITY-20260927-026` (5a21b08 + 9a00446 on the published +unity2,
  846dfa0), pushed.
- **Gated build** on the pinned chroot 20260929T201245Z (UNITY-20260929-016):
  `build-gated/UNITY-20260927-026-indicator-datetime-build-manifest.json`,
  PASS, 29 of 29 tests (test-eds-ics-tasks-without-start included), with the
  archive's `indicator-datetime_15.10+21.04.20210304.orig.tar.gz` (sha256
  29af1057…, as the resolute Sources index).
- **Payload against the tested build** (logs/09): the .deb has the same
  control fields, file list and exported symbols, and every file inside is
  byte-identical (0 of 39 differ).
- **Target test, mode this_build** (`research/UNITY-20260927-023-libindicator-abi/logs/07-target-this-build.txt`,
  shared with libindicator), on the UNITY-20260927-029/-028 session of
  target2 (Clean-2, our repository, gated hud): the gated .deb installed from
  a file repository, the manifest's (sha256 b090852c…). After a reboot into
  the auto-login Unity session, no drop-in, no test environment:
  indicator-datetime-service is the gated .deb's file (e85fafc7…), its only
  "(deleted)" mappings are the two dconf databases; the service is on the
  bus and its desktop-header action has the clock label and the title.
  There is no src change in +unity3, so the session check is that the
  service runs and serves the panel.
- **Clock:** NTPSynchronized=yes on both phases (UNITY-20260929-022; the
  before/after is in the -029 card).

## Known gaps before the gate

| gap | state |
|---|---|
| which RECURRENCE-ID forms (floating, TZID, UTC) merge_detached_instances matches was not mapped | closed with a reason: the guard sits in get_appointment(), after the merge, so every merged override without a start is covered whatever its form; the mapping decides only which overrides are merged |
| the alarm-only path (add_alarms_to_subtask) not measured separately | closed with a reason: it goes through the same get_appointment() |
| other EDS versions not measured | closed with a reason: the target is resolute's EDS 3.56.2, the pinned chroot's |
| one test-eds-ics-all-day-events failure in the control e6576ce, not explained | no task ID yet; +unity3 passed it in five builds, the gated one included (29 of 29) |
| orig-vs-git empty directories (the EDS test directories) | fixed here by 5a21b08; the general check is task UNITY-20260928-010 |
