# UNITY-20260928-014 - greeter input sources rewritten while AccountsService has no data

```yaml
task_id: UNITY-20260928-014
task_kind: package
package: indicator-keyboard
target_series: resolute
issue: follow-up of UNITY-20260927-024 (LP #2166139); local description below
status: REPRODUCED
issue_search_result: NOT_FOUND
source_version: 0.0.0+19.10.20240924-0ubuntu1+unity3 (ours); stock 0.0.0+19.10.20240924-0ubuntu1
binary_version: 0.0.0+19.10.20240924-0ubuntu1+unity3 on target2 (built 2026-09-26, ~/work/b/ik3/out, deb sha256 52576c1d...)
source_commit: 10eb95c (packages/indicator-keyboard, unity/resolute)
observed: see Reproduction
expected: while AccountsService has no data for a listed user, the greeter's org.gnome.desktop.input-sources is left as it is; current is never outside sources (0 when sources is empty)
existing_fix_result: NOT_FIXED
architectural_task: false
design_challenger_required: true
design_review_result: APPROVE  # round 1 REVISE, round 2 REVISE, round 3 APPROVE (design A'')
code_risks:
  ownership_lifetime: checked (fresh list_users() is a local, used only within the synchronous pass; the users field and per-user closures unchanged, UNITY-20260928-016)
  callbacks_cancellation: checked (one manager notify::is-loaded handler in both branches; one manager user-changed handler gated by migration_pending; writes only on changed content, so repeated passes are no-ops)
  threading_reentrancy: not_applicable (main loop only)
  ABI_API_file_list: checked (internal functions of the service binary; no library, no file-list change)
unknowns:
  - visible effect of the ~0.3 s window in the greeter panel (not captured; too short to screenshot)
```

## Observed

The greeter's `indicator-keyboard-service` (runs as `lightdm`) rebuilds the
greeter's `org.gnome.desktop.input-sources` from every AccountsService user in
`migrate_input_sources()` (lib/main.vala:517-611). When `accounts-daemon`
restarts, e.g. on an accountsservice upgrade while the login screen is up,
libaccountsservice flips the manager to loaded while the users it lists have
no data yet. The service then writes, in this order:

1. `current = list.size - 1` (lib/main.vala:605) - `list` is empty, the uint
   underflows to 4294967295;
2. `sources = []` (lib/main.vala:608);

and 0.3 s later, on the daemon's `Changed` signal, the correct
`[gb, us]` / 0 again.

## Reproduction

target2 (VM target-desktop-2), clean snapshot `Clean-2`, `~/.dirty` set;
greeter switched to unity-greeter (`/etc/lightdm/lightdm.conf` line 103, the
file overrides `lightdm.conf.d`), autologin disabled
(`lightdm.conf.d/90-unity014.conf`); user mike with AccountsService input
sources `[gb, us]`; login screen up after a normal boot. `repro.sh restart 10`
(this directory) watches the lightdm user's settings with `gsettings monitor`
(every write is an event) and restarts accounts-daemon.

- FACT stock 0ubuntu1 (logs/01, 3 of 3): the service segfaults
  (`g_variant_ref: assertion 'value != NULL' failed`, SIGSEGV in libglib -
  the -024 crash); no write to the settings; systemd restarts it.
- FACT +unity3 after a normal boot (logs/02, 3 of 3; service env without
  `UNITY_GREETER_DBUS_NAME` and `DISPLAY`): `current 4294967295`, then
  `sources []`, then `current 0`, `sources [gb, us]` 0.29-0.60 s after the
  first write. Same pid throughout. So the path needs no greeter variable -
  it is live in the normal boot state.
- FACT (logs/03): with the daemon only stopped for 30 s nothing is written;
  the window opens when it comes back (`start`).
- FACT (logs/04): SIGKILL of the service right after `sources []` (standing in
  for the greeter ending inside the window): systemd restarts it and the new
  instance writes `[gb, us]` / 0. (That instance later misbehaves: logs/06, 10, 12 M3.)
- FACT (logs/05, `nonexistent-in-window.py`, 3 of 3): in the manager's
  `notify::is-loaded` handler, the listed user mike is `loaded=True
  nonexistent=False user_name=None uid=0 input_sources=NULL`; before the
  restart `user_name='mike' uid=1000`.

## Harm

- FACT: the only reader of the greeter's `current` is indicator-keyboard
  itself and each read checks the index (main.vala:619, 690, 1164, 1264,
  UNITY-20260927-024). unity-greeter disables the u-s-d keyboard plugin, so
  the X layout used for the password is not taken from these settings.
- FACT: no crash. A lasting effect exists: a stored `current 4294967295`
  comes back after a reboot as the last index (logs/07, gb -> us), and an
  instance started inside the window stays at `[]` or misses new users
  (logs/06, 10, 12 M3).
- INFERENCE: the effect is a ~0.3 s invalid state (no layouts, an index past
  the end) that other readers of the lightdm user's settings could see, and a
  write of `[]` over good data; under lightdm-gtk-greeter with `DISPLAY` the
  same write degrades the list to the system layout only (`[gb]`, -024
  logs/05). Small, but it is the service writing data it does not have.

## Root cause

`root_cause_mechanism`: `migrate_input_sources()` treats "a listed user has no
AccountsService data" the same as "a listed user has no layouts" and writes
the union of what it could read. libaccountsservice reports the manager loaded
before the listed users are repopulated (UNITY-20260927-024: an ordering
weakness in the library; NULL is also returned by design for nonexistent
users). The index is then computed as `list.size - 1` with no empty check.

`invariant` (narrowed after DC round 1): the greeter's input sources are not
written while every listed, loaded, existing user has an empty
AccountsService cache; `current < n_sources`, or 0 when there are none.

`correct_layer`: indicator-keyboard, the consumer (UNITY-20260927-024
conclusion: NULL belongs to the consumer). The library window cannot be
relied on to close, NULL is a legitimate library answer, and only the
consumer knows it is about to overwrite good data with a partial union.

## Existing fix search (2026-09-29, delegated, 20 min)

- Ubuntu: resolute 0ubuntu1; stonking 0ubuntu4 (0ubuntu2..4: no code change)
  - still `list.size - 1`, no guard. Debian: no package.
- Upstream lp:indicator-keyboard trunk: last code change is the one in
  20240924; no related MP. Launchpad bugs (93 Ubuntu, 33 upstream titles):
  none about empty sources / 4294967295 / accounts-daemon restart.
- Ayatana ayatana-indicator-keyboard (C rewrite, HEAD e4c8cb3a): no greeter
  migration, nothing to take. Lomiri uses Ayatana.
- Local: 10eb95c (+unity3) handles the NULL crash only.

Result: `NOT_FIXED`; `issue_search_result: NOT_FOUND` (gap: bug descriptions
were not full-text searched; bzr history not walked line by line).

## Candidate approaches

A. **Skip the write while AccountsService has no data; clamp current**
   (proposed). In `migrate_input_sources()`, before building the list: if a
   listed user is loaded, not nonexistent and has a NULL `user_name`, return
   without writing (logs/05 shows exactly that state in the window). The
   existing LightDM `user-changed` callback (main.vala:433) re-runs the
   migration when the daemon's `Changed` arrives (the recovery write in
   logs/02 comes from it). Compute `current` with a helper that returns 0 for
   an empty list, `wanted` if it is in range, else the last index. Both
   decisions as small functions in `lib/input-sources.vala` with unit tests
   (the -024 test seam). Cost: ~25 lines + tests.
B. Fix libaccountsservice so `is-loaded` becomes true only after the users are
   repopulated. Rejected: -024 measured it as a library ordering weakness but
   NULL stays a legitimate answer (nonexistent users), other consumers are
   not ours, and it would not stop the consumer from overwriting good data
   with a partial union in other NULL cases.
C. Clamp `current` only. Rejected: leaves `sources = []` over good data.
D. Skip only when the resulting list is empty. Rejected: under
   lightdm-gtk-greeter with `DISPLAY` the list is not empty but degraded to
   the system layout (-024 logs/05); the missing data, not the empty result,
   is the condition.
E. Delay the migration with a timer. Rejected: timing-based; the daemon's
   `Changed` already signals completion.

Version: `0.0.0+19.10.20240924-0ubuntu1+unity4`.

## Design Challenger round 1: REVISE (2026-09-29) and what was measured after

DC points: (1) the recovery trigger is inferred, make the retry structural
(Act.User `changed`); (2) a user deleted while the daemon is down may stay
listed with NULL data and freeze A; (3) narrow the invariant (users not yet
loaded converge through their own `notify::is-loaded`); (5) write `sources`
before `current`; keep the helper free of Act.User. Points 4, 6, 7 agreed.

Measured after (target2, +unity3):

- FACT (logs/08, clean boot): user ik014del (xkb de) deleted while the daemon
  was stopped. After `start`: the usual window, then `[gb, us]` - the dead
  user contributes nothing. `list-users-probe.py` (as mike): the object
  `/org/freedesktop/Accounts/User1001` stays listed for 23 s and more as
  `loaded=True nonexistent=False name=None uid=0`. So DC point 2 is real: A's
  condition as written would skip every later migration.
- FACT (logs/06, 07): in the service instance systemd restarted after the
  SIGKILL of logs/04, a later useradd plus daemon restart left the greeter at
  `sources=[] current=4294967295` for good (no recovery write; journal:
  `ActUserManager: user (null) has no username (object path
  /org/freedesktop/Accounts/User1001, uid: 0)`). After a reboot the stored
  `current 4294967295` came back as `current 1` (`lightdm_current >= size`,
  so `size - 1`): the greeter's current layout index moved from gb to us
  across the reboot. A lasting effect, contrary to the first reading of
  logs/04.
- FACT (logs/09, 3 runs): a kill inside the window and the restarted instance
  then serving two more daemon restarts recovered each time. So the stuck
  state of logs/06 needs more than that sequence (a new user plus a restart
  in that instance); not reduced further yet.

Revision direction (not yet reviewed): skip the write only when no listed,
loaded, existing user has data (all have a NULL name) - a dead object among
users with data then no longer blocks; retry with a one-shot `changed`
connection on the users without data; `sources` before `current`; clamp;
helper takes plain values. Open: reduce logs/06 to a reproducible sequence and
check that the revision recovers from it.

Paused 2026-09-29 ~09:53Z for UNITY-20260927-047 (C); resumed 10:06Z.

## After the pause (2026-09-29 10:06Z on)

- FACT (logs/10): kill inside the window, then, in the restarted instance,
  useradd ik014del (xkb de) + daemon restart: the greeter settings come back
  as `[gb, us]` **without de**, while on a clean boot (logs/08) the same step
  gives `[gb, us, de]`. INFERENCE: the restarted instance migrates from a
  stale `users` snapshot. `migrate_keyboard_layouts()` calls `list_users()`
  once when the manager is already loaded at start and connects no
  `notify::is-loaded` handler in that branch (main.vala:396-409), so new users
  and replaced objects never enter `users`. logs/06 (`[]` for good) is the
  same instance kind; its snapshot objects stayed without data. Overlaps
  UNITY-20260928-016 (weak `users` list).
- FACT (logs/11, `manager-user-changed.py`, 3 of 3): after a daemon restart,
  `ActUserManager` emits `user-changed` 0.24-0.25 s after `is-loaded`, and a
  fresh `list_users()` then has the data (name `mike`).

## Design A' (for Design Challenger round 2)

In `migrate_input_sources()`:

1. Read a fresh `manager.list_users()`; if the manager is not loaded, return
   (its `notify::is-loaded` handler migrates when it is). This drops the
   stale snapshot as the source of the union (logs/06, 10) - needed, or the
   skip in 2 would freeze on objects that never get data.
2. Count listed users that are loaded and not nonexistent: with data
   (`user_name != null`) and without. Skip the write when at least one has no
   data and none has data (the restart window: logs/05, 11). A dead object
   among users with data (logs/08) does not block: it contributes nothing, as
   today. Record that a pass was skipped.
3. Retry structurally: connect once to `ActUserManager::user-changed`; when a
   pass was skipped, run the migration again (logs/11: emitted with data
   0.25 s later). The existing LightDM callbacks stay.
4. Write `sources` before `current`; `current` from a helper: 0 when there
   are no sources, the wanted index when in range, else the last.
5. Helpers in `lib/input-sources.vala` take plain values (counts, index,
   size) and get unit tests in `tests/main.vala`.

Narrowed invariant: the greeter's input sources are not written while every
listed, loaded, existing user has an empty AccountsService cache; `current`
is always `< n_sources`, or 0 when there are none. Users not yet loaded stay
out, as today (their own `notify::is-loaded` migrates them).

Superseded by A'' below (DC round 2: REVISE).

### DC round 2 measurements (logs/12, +unity3, 10:12Z)

- M1 FACT: a fresh process lists only live users (mike); the object of a
  user deleted while the daemon was down exists only in long-running
  processes such as the greeter's service.
- M3 FACT: in the instance that was restarted after the kill of logs/10, a
  second real user ik014two (de) plus a daemon restart again came back as
  `[gb, us]` without de (stale snapshot, second time).
- M2 FACT: after restarting only the service (a new instance), de was
  present at once, and a new user ik014new (fr) plus a daemon restart gave
  `[]`, then in one pass `[gb, us, fr, de]` / 0. With three real users the
  recovery wrote the complete union at once; no partial union was seen
  (1 run). So an instance started normally re-lists users on every daemon
  restart (the manager was not loaded at its start, so the `notify::is-loaded`
  handler exists). The instance started inside the reload window took the
  "already loaded" branch (main.vala:396-409), which has no handler and never
  re-lists (INFERENCE from the code and M2 vs M3).

## Design A'' (after DC round 2)

- `migrate_keyboard_layouts()`: one manager `notify::is-loaded` handler,
  connected in both branches (loaded or not at start), that calls the
  migration when the manager becomes loaded. The per-user `notify::is-loaded`
  closures and the `users` field stay as they are (UNITY-20260928-016).
- One `ActUserManager::user-changed` handler: re-runs the migration while
  `migration_pending` is set.
- `migrate_input_sources()`: local fresh `manager.list_users()`, used only
  within the synchronous pass. Return early when the manager is not loaded.
  Count loaded, existing users with data (`user_name != null`) and without
  it. `migration_pending = without > 0`; skip the write when `with == 0 &&
  without > 0`. Otherwise build the union from the users with data plus the
  LightDM layout as today.
- Write only what changes: `sources` if it differs from the stored value,
  then `current` from the helper (0 if empty, wanted if in range, else last)
  if it differs. Then `update_greeter_user()` as today.
- Helpers in `lib/input-sources.vala` on plain values, with unit tests.

Behaviour changes, stated:

- If accounts-daemon is absent or never loads, today the greeter gets
  `[system layout]` from LightDM callbacks iterating an empty list. With A''
  nothing is written, the stored values stay, and `update_greeter_user()` is
  not reached from the migration (it still runs on entry selection).
- A dead object among users with data keeps `migration_pending` set. That is
  harmless: every later `user-changed` re-runs a pass, and the pass writes
  nothing when the values are unchanged.
- "Written once" in validation means no write with different content between
  the stored good values and the recovered ones.

Known remaining (A''):

- With several users the recovery pass may see some users still without
  data and write a partial union. It is never empty, `migration_pending`
  stays set, and the next manager `user-changed` completes it. It was not
  seen in 1 three-user run (logs/12 M2); validation repeats this at least
  3 times.
- A `current` of 4294967295 already stored by +unity3 is treated as today
  (out of range, so the last index) after the next start; that is the gb->us
  shift of logs/07. A'' never writes the underflow again. Mapping an
  out-of-range stored `current` to 0 would change stock semantics; not done.
- A dead object alone (every real user deleted while the daemon was down)
  keeps the old sources instead of writing `[]`.

Live validation for A'': repro.sh restart x3, stop/start, the kill-in-window
sequence, M2 and M3 of round2-measure.sh, 3 multi-user restarts, and one
boot (first write present). Pass criterion: no write of `[]` or of an index
out of range, and no write with different content between the good values
and the recovered ones.
