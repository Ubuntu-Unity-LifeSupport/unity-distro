# indicator-datetime: tasks with only a due date abort the service (LP #1848969, #2099742)

Agent B, 2026-09-26, on `target2`: our indicator-datetime `+unity1`, EDS
3.56.2-8, Unity session. target2 was rolled back to `Clean-2` afterwards.

## Rule 0

- **LP.**
  - #1848969 (2019): `DateTime::get(): assertion failed: (m_dt)`.
  - #2099742 (2025): "crashes and disappears" with a Nextcloud account; it
    works with the account's calendar sync disabled.
  - Nothing new on indicator-datetime was filed since 2026-04-01. Only
    #1987920, an FTBFS, was touched.
- **26.10** has the same `0ubuntu6`.
- **Ayatana** merged 47e005d (PR #140, 2025-09-01): `DateTime::get()`
  returns NULL instead of asserting, for "incomplete DateTime objects" from
  Google Calendar. That removes the abort, but the unset time then goes on
  into `g_date_time_format(NULL)` and similar, and the task still has no
  time. We fix the cause instead.

## Cause

`EdsEngine` reads task lists as well as calendars. `get_appointment()` takes
`begin` from DTSTART only. A VTODO with a DUE and no DTSTART — what
Nextcloud Tasks creates, and a time-range query returns it by its DUE —
therefore gets an unset `begin`.

The `g_debug()` at the end of `get_appointment()` formats `begin`. Its
arguments are evaluated even when debug output is off, so
`DateTime::format()` calls `DateTime::get()`, which asserts on an unset
`m_dt` and aborts. This explains #2099742: Nextcloud syncs tasks, Gmail
does not.

## Reproduced (`eds.py`, `dt.sh`)

A VTODO with only `DUE` (`todo-due.ics`) in the local task list, then the
service started as in the session:
- `+unity1` aborts with `Indicator-Datetime:ERROR:./src/date-time.cpp:172:
  … assertion failed: (m_dt)`.
- The core dump shows `DateTime::get` ← `DateTime::format` ←
  `EdsEngine::Impl::get_appointment` ← `add_event_to_subtask` ←
  `on_event_fetch_list_done`.

A VTODO with neither DTSTART nor DUE is not returned by the range query and
did not crash.

**Checked with `+unity1` without a crash:**
- events (`ev-*.ics`): daily recurring with an EXDATE and a TZID; all-day;
  TZID `Etc/Utc`, which libical does not know (the #1848969 log); no DTEND
  with a VALARM;
- timezone changes under the running service (`dt2.sh`): New York, Kolkata,
  Chatham (+12:45), Lord Howe (half-hour DST), and back;
- date changes of +1 day, +40 days and -1 day, with NTP off;
- suspend-to-idle and resume (`rtcwake -m freeze`; VirtualBox's RTC did
  not wake the guest, a key press did after 2.5 min).

## Fix: `+unity2`

In `packages/indicator-datetime`, `846dfa0` (a git-ubuntu clone, no remote
of ours):
- a VTODO without DTSTART is placed at its DUE;
- a component that still has no time is not added;
- the debug message only formats a time that is set.

Test `test-eds-ics-tasks-without-start` has three tasks: DTSTART only, DUE
only, and neither. It expects the first two and not the third.
- The build in a clean `sbuild -d resolute` passes 29 of 29 tests.
- A control build with the test but the old `engine-eds.cpp` fails exactly
  this test, with `assertion failed: (m_dt)`.

**On target2 with `+unity2`:**
- The same due-only task: alive 3 of 3.
- The task appears in the menu ("Task with due only").
- The timezone and date changes pass as well.

`+unity2` is in aptly.

## LP #1515821 (recurring events shown once)

Seen on the way, and not a bug of this kind. The menu adds each event UID
once (`Menu::add_appointments`, "don't show duplicates"), so a recurring
event shows its next occurrence only. The code even cites bug 1515821. On
target2 a daily event showed once, next to four other events. Showing more
occurrences would be a behaviour change, not a fix; left alone.
