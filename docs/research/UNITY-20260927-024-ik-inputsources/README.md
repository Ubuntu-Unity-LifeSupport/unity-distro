# UNITY-20260927-024: which layer owns a NULL InputSources

Owner: agent B (target2). This comes from the legacy reconciliation, B-L17
(ROOT_CAUSE_UNPROVEN). indicator-keyboard +unity3 (`10eb95c`, LP #2166139,
in aptly since 2026-09-26) treats a NULL `act_user_get_input_sources()` as
"no layouts". It also stops passing a NULL user name to LightDM. The
reconciliation found three gaps in that record:

- it said AccountsService "documents" the NULL, with no source;
- the inconsistent state (a user that is `is-loaded`, but whose properties
  are gone) comes from AccountsService, while the guard sits at the
  consumer;
- nothing showed that the layouts come back once accounts-daemon returns.

The task is to establish which layer owns the invariant.

**Outcome: the consumer owns it. +unity3 is kept unchanged, and the task
closes ALREADY_FIXED (PATCH_ALREADY_EXISTS).** libaccountsservice returns
NULL for a loaded user in two states:

- **for every nonexistent user**, with no restart involved. indicator-keyboard
  reaches this state in normal use. Under unity-greeter, moving the
  selection mike -> `*other` -> mike -> `*other` crashes Ubuntu's stock
  service 3 of 3; +unity3 survives (logs/06-08).
- **during a daemon restart**, because of an ordering weakness in the
  library itself: the manager says "loaded" before the user proxies have
  their properties back.

A consumer has to handle NULL either way. A library fix would close only the
restart window and would not remove the need for the guard.

One new observation is not blocking. Inside the restart window, +unity3
writes an empty source list with `current` = 4294967295 to the greeter's
settings, for about 0.2 s, then recovers (3 of 3). See "The consumer inside
the window".

```yaml
task_id: UNITY-20260927-024
package: indicator-keyboard
target_series: resolute
issue: LP #2166139 (crash in g_variant_iter_new); legacy B-L17 owning layer
status: REPRODUCED
issue_search_result: FOUND  # LP #2166139 (ours, New); upstream #55 / !58 is the same class, partly fixed in 2020; see below
source_version: 0.0.0+19.10.20240924-0ubuntu1+unity3 (10eb95c; our aptly)
binary_version: indicator-keyboard 0.0.0+19.10.20240924-0ubuntu1+unity3 on target2 (for this test)
source_commit: 10eb95c (packages/indicator-keyboard, branch unity/resolute)
library_version: accountsservice, libaccountsservice0 23.13.9-8ubuntu5.2 (resolute-updates), GLib 2.88
observed: >
  FACT (logs/01, 3 of 3): across `systemctl restart accounts-daemon`,
  ActUserManager:is-loaded goes FALSE when the name owner vanishes and TRUE
  when the new owner appears. At that TRUE notification the user object is
  still is-loaded=TRUE but has user_name NULL, uid 0 and InputSources NULL.
  About 240 ms later the daemon's Changed signal arrives and the values are
  back.
  FACT (logs/04, logs/09): a nonexistent user (`nosuchuser`, `*other`,
  `*guest`) is is-loaded=TRUE, nonexistent=TRUE, user_name NULL and
  InputSources NULL, with no restart involved. Read the way the consumer
  reads it (get_user() and is_loaded at once), the first call is not
  loaded; the next call for the same name returns that NULL. A real user
  without a keyfile gets `[]`, not NULL.
  FACT (logs/06-08): under unity-greeter, the greeter's service calls
  get_user("*other") on EntrySelected. On the second selection it reads
  input_sources = NULL. Stock 0ubuntu1 then segfaults with
  `g_variant_ref: assertion 'value != NULL' failed`, 3 of 3, with no daemon
  restart. +unity3 survives six switches with no message.
expected: the service does not crash, and the greeter's layouts are whole again once the daemon is back
reproduction: act-probe.py, nonexistent-probe.py, repeat-get-user-probe.py, greeter-restart.sh, greeter-trace.bt, restart-trace.bt (this directory); unity-greeter + up/down keys (logs/06-08); the restart crash in research/indicator-keyboard-2166139/ (ik.sh, +unity2 3 of 3 SIGSEGV)
evidence: logs/01-09
root_cause: see "Mechanism"
root_cause_mechanism: >
  libaccountsservice keeps each ActUser's AccountsUser GDBusProxy across a
  change of daemon. GDBusProxy clears the property cache when the owner
  vanishes and reloads it with GetAll when the new owner appears. ActUser
  never resets is-loaded, so every getter returns NULL in between.
  ActUserManager sets is-loaded from its own proxy's notify::g-name-owner
  (on_name_owner_changed), which fires when the manager proxy's GetAll
  returns. The manager's and the user's GetAll are sent together and
  answered 20 us apart (logs/03), so a consumer that reacts to the manager
  reads the user before its reply is processed.
  Separately, and by design, a nonexistent user has no proxy at all
  (accounts_proxy NULL, _act_user_update_as_nonexistent sets is-loaded), so
  every getter returns NULL for it.
invariant: >
  indicator-keyboard never iterates or dereferences a NULL value from an
  act_user_get_* getter: NULL input sources means "no layouts from
  AccountsService", and it falls back to xkeyboard_layouts and then LightDM.
  After a daemon restart the greeter's layout list is whole again.
existing_fix_result: PATCH_ALREADY_EXISTS  # our +unity3 10eb95c
design_challenger_required: true
design_review_result: REVISE (round 1; findings answered below), round 2 pending
architectural_task: false
correct_layer: >
  The consumer. For a name that does not exist, libaccountsservice hands
  out a loaded user object marked nonexistent, and every getter on it
  returns NULL. The library logs a warning for it but gives no other answer.
  get_user() documents only waiting for is-loaded, so a consumer that reads
  a name it does not control (a greeter entry) must check
  act_user_is_nonexistent() or NULL. indicator-keyboard does not, and it
  crashes (logs/07). +unity3's NULL check covers both the nonexistent user
  and the restart window. A library fix would remove only the window.
defensive_workaround_rejected: >
  Not a workaround: the failure is the consumer's unchecked use of a value
  the library returns for a nonexistent user (logs/07, no library defect
  involved). The restart window is a separate library weakness. Fixing it
  in libaccountsservice would not change what the consumer must do, and it
  is left for upstream (see "Layer decision").
code_risks:
  ownership_lifetime: checked  # (transfer none) value is only read in place
  callbacks_cancellation: not_applicable
  threading_reentrancy: not_applicable
  ABI_API_file_list: not_applicable  # no code change
unknowns:
  - `*guest` was checked at library level only (logs/09); the greeter here
    offers no guest entry. It takes the same code path as `*other`
  - the LightDM user-name guard in +unity3 (no NULL name to
    lightdm_user_list_get_user_by_name) still has no test of its own; it only
    removes a g_return_val_if_fail critical, not a crash
  - the empty list written inside the restart window (see below) was only
    watched for about 0.2 s; typing a password in that window was not tested
  - the case of a daemon that never comes back is inferred: the greeter's
    list would stay empty until the service or greeter restarts
```

## Mechanism

### The restart window (logs/01-03)

`act-probe.py` watches the manager and the user `mike` with 20 ms snapshots
while accounts-daemon restarts. Every run looked the same (3 of 3):

Times below are from logs/01; the NULL span is 0.10-0.17 s per run.

| time (s) | event | user object |
|---|---|---|
| 3.90 | manager `is-loaded` = FALSE (old owner gone) | still whole (cache not yet cleared at that instant) |
| 3.9-4.06 | snapshots | `loaded=True name=None uid=0 input_sources=NULL` |
| 4.02-4.06 | manager `is-loaded` = TRUE | **`loaded=True name=None input_sources=NULL`**, read inside the handler |
| next snapshot | user proxy's GetAll processed | whole again |
| 4.26-4.30 | daemon's `Changed` -> ActUser `changed`, manager `user-changed` | whole |

On the bus (logs/03) the probe sends GetAll for `/org/freedesktop/Accounts`
and `/org/freedesktop/Accounts/User1000` to the new daemon in the same
microsecond. The replies arrive 20 us apart. The manager proxy's reply comes
first, and its `notify::g-name-owner` makes the manager `is-loaded` while the
user proxy's cache is still empty.

Source (accountsservice 23.13.9-8ubuntu5.2):

- `act-user.c`: `_act_user_update_from_object_path()` creates the proxy
  once, with `G_DBUS_PROXY_FLAGS_NONE`, and sets `is-loaded`. Nothing ever
  resets it or watches the proxy's owner.
- `act-user-manager.c`: `on_name_owner_changed()` sets
  `set_is_loaded (manager, owner != NULL)`.
- The getters (`act_user_get_input_sources()` and the others) return
  `accounts_user_get_*()` from the cache, or NULL when there is no proxy.

### NULL outside any restart (logs/04)

`act_user_manager_get_user()` on a name that does not exist loads the user
as nonexistent. It is `is-loaded=TRUE`, `nonexistent=TRUE`, and every getter
returns NULL (accounts_proxy NULL). This is how the library reports "no such
user", and it holds for as long as the object lives. The library logs a
warning for it ("user (null) has no username"), so it treats the state as
abnormal, but it still hands the object out as loaded. An existing user with
no keyfile gets an empty `aa{ss}` from the daemon (patch 0016), never NULL.

### What the library documents

`act_user_get_input_sources()` is added by the Ubuntu-only patch
`0016-add-input-sources-support.patch`. It is annotated
`(transfer none)`, not `(nullable)`, so the earlier record's "accountsservice
documents that NULL" was wrong. The behaviour is the same as for every other
getter written on the `accounts_proxy == NULL` pattern. `act_user_is_loaded()`
says the object is "loaded and ready to read from", which the restart window
contradicts.

## The consumer and a nonexistent user (logs/06-09)

target2 was switched to unity-greeter with manual login shown, so the list
has ik024test, Mike and `*other` ("Войти"). The entry was moved with the
arrow keys through the vbox tools. dbus-monitor showed `EntrySelected`
for each move.

- **Stock 0ubuntu1:** SIGSEGV 3 of 3 rounds (logs/07). Each round logged
  "user (null) has no username", then `g_variant_ref: assertion 'value !=
  NULL' failed`, then a segfault in libglib. systemd restarted the unit.
- **+unity3:** a trace of the library calls (logs/06) shows the second
  get_user("*other") returning input_sources = 0. The service falls back to
  LightDM and carries on. Six switches, no message, same pid (logs/08).

The path depends on the environment. The service watches the greeter only
when `UNITY_GREETER_DBUS_NAME` is set (main.vala:105-113). After a normal
boot the unit starts before unity-greeter puts that variable into the
lightdm user manager's environment, so the path is dead. Any later start
of the unit has it, for example a `Restart=on-failure` after a crash
(logs/09). With the stock package, one daemon restart therefore arms the
entry crash. This start-order dependency is a separate defect: after boot
the greeter's layout does not follow the selected user at all.

## The consumer inside the restart window (logs/05, 06)

Recovery does not depend on timing luck. The daemon's `reload_users()`
registers each user, then thaws notifications (daemon.c:625-634), and
`on_user_property_notify()` emits `Changed` after a 250 ms debounce
(user.c:1150-1165). liblightdm reloads the user on it and emits
user-changed, and the indicator re-runs `migrate_input_sources()`
(main.vala:433). The indicator's write inside the window comes from the
manager's `notify::is-loaded` handler: `list_users` at the same
millisecond as the NULL reads (logs/06, 27307 ms).

What gets written differs by greeter:

| greeter, how the service runs | inside the window | after | runs |
|---|---|---|---|
| lightdm-gtk-greeter, started by hand with DISPLAY=:0 (logs/05) | `[gb]`, current 0 | `[gb, us]`, 0 | 3 of 3 |
| unity-greeter, systemd unit, no DISPLAY (logs/06) | `[]`, current 4294967295, for 0.21-0.25 s | `[gb, us]`, 0 | 3 of 3 |

Under the unit, LightDM's system layout adds nothing without a display.
The list is then empty, and `current = list.size - 1` underflows. That
line is stock code; +unity3 only makes it reachable instead of crashing
first. Nothing was seen to persist. For a lasting effect the daemon would
have to stay away, and then the greeter has no user data anyway.

The earlier claim "current stayed 0" proved little. In logs/05 the system
layout and the first user layout are both `gb` at index 0. Under
lightdm-gtk-greeter, `update_greeter_user()` never has a selected user. Under
unity-greeter the selected user is re-applied on the recovery pass (logs/06,
`get_user(mike)` at 27583 and 27615).

The unchanged +unity2 code crashes on the restart 3 of 3
(research/indicator-keyboard-2166139/).

## Layer decision

| Layer | What a fix there would do | Verdict |
|---|---|---|
| indicator-keyboard (consumer) | treat NULL as "no layouts", fall back; already +unity3 | **owns it**: NULL reaches it by design (nonexistent users) and in the window |
| libaccountsservice, manager side | hold the manager's `is-loaded` until every user proxy has its properties back (GDBusProxy notifies `g-name-owner` after its GetAll, so the manager can wait for each user's proxy) | leaves ActUser's behaviour unchanged and would stop this consumer's handler from reading NULL at the notification. Between owner loss and the new owner, users still read NULL, and nonexistent users always do. So the consumer check stays. A patch to carry in a package under security maintenance (5.2) |
| libaccountsservice, user side | reset `ActUser:is-loaded` on owner loss | `is-loaded` is one-way today (`_act_user_update_as_nonexistent` asserts `!loaded`; `set_is_loaded (user, TRUE)` only). Consumers written for that would see a new FALSE. Not considered further |
| libaccountsservice, signals | forward the proxy's `g-properties-changed` as ActUser `changed` | would tell consumers ~250 ms earlier that data is back. It does not help indicator-keyboard, which does not listen to ActUser |
| accounts-daemon | nothing: it always exports InputSources (`[]` with no keyfile) | not involved |

The ordering in libaccountsservice is a real weakness: the manager reports
"loaded" before its users are readable. It lasts 0.10-0.17 s, heals itself,
and does not change what the consumer must do. The manager-side fix is the
right upstream shape. It can go there as a report (through C and May). We
do not carry it as our own patch.

## Search for an existing fix (2026-09-28)

A delegated search, spot-checked by the owner through the GitLab API and
upstream main's source:

- **Upstream accountsservice.** Issue #55, "Restarts of daemon crash
  consumers when gdm has AutomaticLogin configured" (closed 2020-05-15), is
  the same mechanism: after a restart `act_user_get_user_name()` returned
  NULL inside the library. MR !58 (32370764, merged 2020-05-04) added the
  manager's `on_name_owner_changed()`: the manager's `is-loaded` follows the
  daemon. That is the partial fix, and 23.13.9 already has it. On main today
  (latest tag 26.27.3, 2026-06-29) `ActUser` still only ever sets
  `is-loaded` to TRUE (act-user.c lines 1199, 1249, 1304), so the window
  measured here is unfixed upstream. No open issue or MR covers it.
- **Debian.** sid 23.13.9-8. The only related entry is 0.6.55-2, the !58
  backport (Debian #948228, LP #1843982). The input-sources patch is not in
  Debian.
- **Ubuntu 26.10.** 26.27.3-0ubuntu1 (2026-08-15), with no restart or NULL
  entry. It renames libaccountsservice0 to libaccountsservice1, which
  matters when the series moves on, not for this task.
- **Launchpad.** LP #2166139 has one task (indicator-keyboard), New, with
  no fix. LP #1843982 and #1841382 are the 2019 crashes fixed by !58. No
  bug about NULL `act_user_get_*` in a consumer after a restart.
- **Documentation.** The input-sources API is Ubuntu's patch 0016 (2013).
  Its getter is not `(nullable)`, and nothing documents NULL.

Gaps: GitLab issue notes need a login, so the discussion in #55 was not
read; errors.ubuntu.com buckets were not searched.

`existing_fix_result: PATCH_ALREADY_EXISTS`. The consumer fix is ours,
+unity3. Nothing newer in Ubuntu, Debian or upstream fixes either the
consumer or the library window.

## Design review, round 1: REVISE

Findings and answers:

1. **The nonexistent-user path was not shown for this consumer.** Now it
   is, with the consumer's own calling pattern (logs/09) and in the real
   greeter (logs/06-08: the stock package crashes 3 of 3, +unity3 survives).
   The start-order condition that the reviewer did not know about is in
   logs/09.
2. **logs/05 did not exercise update_greeter_user().** Rerun under
   unity-greeter with a selected user (logs/06). The "current stayed 0"
   claim is narrowed; the underflow found there is recorded.
3. **Other getters.** +unity3 survived `xkeyboard_layouts` on a
   nonexistent user: that path runs on every `*other` selection (logs/08).
4. **The manager-side library fix.** The table now weighs it properly.
   The conclusion stands, because it leaves the owner-gone span and
   nonexistent users to the consumer.
5. **The recovery path** is now cited from the source instead of inferred
   from timing.
6. **Wording.**
   - One set of window figures is used throughout.
   - Unsupported consumer claims (the one-shot `notify::is-loaded` list)
     were dropped.
   - "Documented by behaviour" was replaced by what the library does,
     including its warning.
   - `is_nonexistent` is named as the check that fits the library's model.
   - The empty-`aa{ss}` straw man was removed.
   - The trigger of the write is identified (logs/06).
7. **The `users` list is `SList<weak Act.User>`** (main.vala:34). If the
   manager drops a user, the entry dangles. Not verified here; listed as a
   follow-up.

## Follow-ups (not this task; for C to decide)

- indicator-keyboard: do not rewrite the greeter's sources while
  AccountsService has no data (a loaded, not-nonexistent user with a NULL
  name), and clamp `current` when the list is empty. Transient today; see
  "The consumer inside the window".
- indicator-keyboard/unity-greeter: after boot the unit starts without
  `UNITY_GREETER_DBUS_NAME`, so the greeter's layout does not follow the
  selected user (logs/09).
- indicator-keyboard: the weak `users` list (finding 7).
- Upstream report for accountsservice: the manager is loaded before its
  users are readable (the manager-side shape above). Through C and May.
- Ubuntu 26.10 renames libaccountsservice0 to libaccountsservice1, which
  consumers such as indicator-keyboard need for the next series.

## Result

- No package change. +unity3 (`10eb95c`) stays as published.
- The previous record is corrected in `docs/DECISIONS.md`. The NULL is
  not documented. The consumer owns it for the reasons above. The crash is
  also reachable without any daemon restart.
- target2 is rolled back to `Clean-2` afterwards.
