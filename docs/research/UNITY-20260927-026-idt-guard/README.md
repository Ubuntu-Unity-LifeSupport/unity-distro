# UNITY-20260927-026: indicator-datetime +unity2's no-time guard

Owner: agent B (target2). This comes from the legacy reconciliation, B-L14,
as PATCH_TOO_BROAD. Besides the main fix (a task with only DUE is placed at
its due date, LP #1848969 and #2099742), indicator-datetime +unity2 added a
guard that leaves out a component with no time at all. The guard was never
shown to be reachable or tested. The task is to prove it reachable and test
it, or to drop it and keep only the main fix. The main fix's regression
must stay fail-before / pass-after. Publication stops at the gate, which is
expected. Aptly freeze applies.

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
  846dfa0 has two guards: g_debug in get_appointment() is skipped and
  add_event_to_subtask() adds nothing when appointment.begin is unset
  (DTSTART and DUE both missing). Its test holds a task without dates and
  expects it to be absent, but never showed where that absence comes from.
root_cause: >
  The guard was written defensively next to the fix without a measured path.
  EDS 3.56.2 never hands the indicator a component without a start.
  - Server side, e_cal_util_get_component_occur_times gives a VTODO
    without DTSTART and DUE the range _TIME_MIN.._TIME_MAX, so it does
    match occur-in-time-range? and reaches the client.
  - Client side, e_cal_client_generate_instances ->
    e_cal_recur_generate_instances_sync takes DUE when DTSTART is missing.
    With neither, dtstart is a null time, and intersects_interval() returns
    FALSE for a null time (e-cal-recur.c:329), so no instance is generated
    and the callback that feeds get_appointment() is never called.
  - The indicator only sees generated instances (on_event_generated), both
    for events and for alarms (e_cal_util_generate_alarms_for_list over
    those components).
root_cause_mechanism: EDS generates no instance for a component with a null start, so get_appointment() is only reached with a start
root_cause_evidence: >
  evolution-data-server 3.56.2-8 source (e-cal-recur.c:319-330, 420-501;
  e-cal-util.c:2310-2342; e-cal-client.c:2440-2540); logs/02 (live EDS
  without the guard)
invariant: >
  get_appointment() only formats and adds appointments that have a start, and
  a task with only DUE is placed at its due date
existing_fix_result: NOT_FIXED
candidate_approaches:
  - (A) drop the guard, keep the due-date fallback, keep the test (its
    dateless task now asserts EDS's behaviour) - chosen
  - (B) keep the guard and add a test for it - rejected: no input reaches
    it (logs/02), so a test could only exercise it by calling
    get_appointment() directly, i.e. test dead code
design_challenger_required: false  # removal of an unreachable branch; no layer, ABI or dependency choice
design_review_result: NOT_REQUIRED
architectural_task: false
correct_layer: src/engine-eds.cpp, where +unity2 added it
defensive_workaround_rejected: >
  keeping an unreachable guard "just in case" is what PATCH_TOO_BROAD flags:
  it hides whether EDS's contract changed. If a future EDS delivers a
  component without a start, the existing test's dateless task will abort
  the test (DateTime::get() assertion), which is the signal we want.
code_risks:
  ownership_lifetime: not_applicable
  callbacks_cancellation: not_applicable
  threading_reentrancy: not_applicable
  ABI_API_file_list: checked  # no API change; file list compared in logs
unknowns:
  - other EDS versions (26.10 ships 3.58?) are not measured; the test would
    catch a change
  - process deviation: the +unity3 commits were made before the evidence
    was entered and the task moved to READY_FOR_FIX (the experiment's
    result was already in logs/02); recorded here
```

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
  (`patches/0001-*`), separate from the guard removal (`0002-*`).
- It is not separable from this upload. Our pipeline builds from git
  (`build_sbuild.py`), where the directory does not exist:
  - without 5a21b08 every test-eds-ics-* test fails in dh_auto_test and
    the build of +unity3 fails (logs/01, the control of the unchanged
    +unity2);
  - so section 4's "run the package's relevant tests and a clean sbuild"
    cannot be done for the guard removal;
  - the main fix's regression test (test-eds-ics-tasks-without-start)
    cannot fail-before/pass-after (logs/03 needs 5a21b08);
  - no +unity3 could be built for publication.
- It changes only test behaviour (`mkdir -p` before `cp`). It is
  idempotent and a no-op on a release-tarball tree, where the directory
  exists.
- The general case, empty directories of the orig that git drops, is
  UNITY-20260928-010 (a check at pipeline level). If that task fixes
  builds from git for every package, this commit becomes redundant but
  stays harmless, and it can be dropped from our patch series then.

## Experiment (logs/02)

42c0f3f (not for release) is +unity2 without the guard. Its test calendar
adds VTODOs without DTSTART and DUE:

- plain;
- RDATE only;
- RRULE only;
- a detached RECURRENCE-ID instance;
- one with an absolute VALARM.

The empty EDS directories were created on disk. Result:

- 28 of 29 tests pass, and nothing aborts;
- get_appointment() produced three appointments: the DTSTART task, the DUE
  task and the RDATE-only probe, at its RDATE (2015-06-20 09:00, start set
  by EDS). All three have a start;
- the other probes never reached the indicator.

The test failed only because it did not expect the RDATE probe.

## Result

- **Package** (`packages/indicator-datetime`, branch b/UNITY-20260927-026):
  - 5a21b08 makes the tests mkdir the EDS tasks directory;
  - 5d6492d drops both guard hunks and keeps the due-date fallback, as
    +unity3 (changelog trailer from `date -u`).
- **Build** from a git clone (`logs/04-build-unity3.txt`, `build/`):
  29 of 29 tests pass, status successful.
- **Main-fix regression** (logs/03). The control e6576ce, not for release,
  is +unity3 without the due-date fallback. test-eds-ics-tasks-without-start
  aborts there with `DateTime::get(): assertion failed: (m_dt)`, the
  original crash, and it passes with +unity3: fail before, pass after.
  - In that control run test-eds-ics-all-day-events also failed. It got
    0 appointments within its wait, i.e. EDS did not deliver the calendar
    in time.
  - That test uses only VEVENTs and the control changed only the VTODO
    path, and it passed in the +unity3 and experiment builds. It is
    treated as timing flakiness of the first EDS test. A rerun of +unity3
    is recorded in logs/05: +unity3 again passes 29 of 29, so the control's
    all-day-events failure was timing flakiness.

## Status

Resumed after UNITY-20260927-057 (2026-09-28). logs/05 is recorded, and
the section 4 justification for 5a21b08 is above. Next: VERIFYING
(independent Verifier), then BLOCKED at the publication gate (047).
