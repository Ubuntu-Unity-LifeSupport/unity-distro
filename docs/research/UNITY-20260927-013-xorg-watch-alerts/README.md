# UNITY-20260927-013: xorg-watch alerts that reach the coordinator

Legacy A-L22. `xorg-watch.timer` (research/xorg-versioning) checks every 3 h
whether Ubuntu uploaded a resolute xorg-server above the base of our
`…+unityN`. Such an upload wins over ours once it reaches -updates or
-security, and we have about a week (the SRU minimum in -proposed) to rebase
our 32 carried patches onto it. Until now the only output was one line in
`~/AGENTS-LOG.md` - a file nobody is obliged to read, and a session starting
later reads only its last 20 lines. A failing watcher wrote only to its own
journal. Agent A, 2026-09-28. Tool task; no VM.

## Evidence card

```yaml
task_id: UNITY-20260927-013
task_kind: tool
issue: xorg-watch's alert does not reach the coordinator, and a failing watcher is silent
status: REPRODUCED
reproduction: >-
  scripts/tests/test_alerts.py against the previous scripts/taskctl.py
  (origin/main 81e6f6e): an open alert is not shown
  (test_taskctl_shows_open_alerts_until_acknowledged,
  test_new_upload_raises_one_alert_and_one_log_line fail); the previous
  watch.sh has no path from a new upload to anything but AGENTS-LOG.md, and
  none at all on failure (code read)
reproduction_result: PASS
existing_fix_result: NOT_FIXED
issue_search_result: NOT_FOUND   # nothing in scripts/ or docs routes automation output to C; peer_inbox.py serves A and B only
root_cause: >-
  the watcher's only channel is AGENTS-LOG.md, which no process requires anyone
  to read; failures go to the user journal only
root_cause_mechanism: >-
  watch.sh appends to ~/AGENTS-LOG.md (default XORG_WATCH_LOG) and exits 1 on
  a failed check; nothing else reads either
root_cause_evidence: docs/research/xorg-versioning/watch.sh at 81e6f6e; CLAUDE.md step 1 (last 20 lines of the log)
invariant: >-
  a new resolute xorg-server above our base, and a watcher that has stopped
  seeing uploads, reach the coordinator in a place it cannot pass over, and
  stay there until C or May has dealt with them
chosen_approach: >-
  scripts/alerts.py: an append-only ~/coordinator/ALERTS.md under flock, one
  RAISE per key, closed by an ACK from C or May; scripts/taskctl.py prints
  every open alert on each run; watch.sh raises xorg-server:<version>@<pocket>
  per upload (plus the AGENTS-LOG line as before) and
  xorg-watch-failing:<UTC time the streak began> after 3 failed runs in a row
correct_layer: >-
  The board tool is the one place the coordinator (and A and B) must use for
  every task operation, so an alert shown there cannot be passed over; the
  alert itself lives in ~/coordinator next to the board, outside git (it
  may name versions before we have decided anything). The watcher raises;
  it does not decide.
alternatives_rejected:
  - "taskctl create from the watcher: only C or May allocates task IDs
    (taskctl refuses other actors); a watcher acting as C would be an
    impersonation, and whether an upload needs a rebase (it may already
    carry our patches, it may be superseded) is the coordinator's call."
  - "A message to C (SendMessage): not available to a systemd unit, and a
    session that is not running would lose it."
  - "Another file in ~/coordinator without the taskctl notice: one more
    place to remember to look - the failure this task is about."
  - "PEER-INBOX files (peer_inbox.py): they are A's and B's, read by their
    owners; the recipient here is C."
regression_test: scripts/tests/test_alerts.py (11 tests; red on the old taskctl for the two notice tests)
validation_record: runs/02-validation.txt   # runs/01 is round 1
architectural_task: false
design_challenger_required: false   # a routing change inside our own tooling, no package or lifetime choice
unknowns:
  - "The timer runs watch.sh from the main checkout (~/unity-distro): the
    change takes effect there once this branch is merged and that checkout
    is at the merge."
  - "ALERTS.md does not exist until the first alert; C's first ack creates
    nothing new."
```

## Verifier, round 1: FAIL (fixed)

Independent Verifier (subagent), own simulated uploads under dash: most of it
held (parallel runs and raises, Security/Pending/superseded/equal-to-base,
ack then re-run, taskctl notice never blocks or alters a board operation,
no forged ACK or hidden alert). Findings fixed in watch.sh:

1. blocking - the failure key carried the day, so a second streak after an
   ack on the same day raised nothing: the key is now the UTC time the streak
   began (test `test_a_second_failure_streak_after_an_ack_is_a_new_alert`);
2. a run whose alert could not be written exited 0, counted nothing and
   wrote no log line: it now logs the line with "ALERT NOT RAISED", exits 1
   and counts as a failure (test updated);
3. a damaged failure counter aborted every run: it restarts at 0 (test
   `test_a_damaged_failure_counter_restarts`).

Notes kept as they are: two concurrent runs could log an upload twice (the
oneshot timer cannot overlap itself; a duplicate raise is no longer logged);
a non-UTF-8 key crashes `alerts.py raise` (not reachable from Launchpad
data); `--actor` is self-declared, as in taskctl; `open_alerts` reads without
the lock (a line being written shows at the next run); a valid but empty
Launchpad answer counts as success.

## Validation (runs/01-validation.txt, round 1; runs/02-validation.txt after the fixes)

- `python3 -m unittest scripts/tests/test_alerts.py`: 9 OK, no network
  (`XORG_WATCH_LP_JSON` stands in for Launchpad, `XORG_WATCH_BASE` for aptly,
  temporary board, log, state and alert file). Covered: raise once per key,
  ack by C or May only and only for a raised key, a message cannot forge an
  ACK line, taskctl shows open alerts until acked and ignores an unreadable
  alert file, one alert + one log line per new upload, nothing for uploads at
  or below the base or superseded, a new pocket is a new alert, an alert that
  cannot be written is retried on the next run (nothing recorded in `seen`),
  three failed runs raise one alert and a success resets the count.
- Red: the two taskctl-notice tests fail against taskctl from origin/main.
- Full suite: `python3 -m unittest discover -s scripts/tests` 103 OK.
- Live, into temporary files: the branch's watch.sh against the real aptly
  and Launchpad writes nothing (nothing above `1ubuntu1.3` today); with a
  fake base `1ubuntu1.2` it raised one alert for the real `1ubuntu1.3` in
  -proposed and wrote one log line.
