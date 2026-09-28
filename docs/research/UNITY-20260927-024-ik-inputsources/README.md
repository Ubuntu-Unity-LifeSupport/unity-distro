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

- **by design**, for every nonexistent user;
- **during a daemon restart**, because of an ordering weakness in the
  library itself: the manager says "loaded" before the user proxies have
  their properties back.

A consumer has to handle NULL either way. Fixing the library would close
only the restart window and would not remove the need for the guard.

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
  FACT (logs/04): a nonexistent user (`nosuchuser`, `*other`, `*guest`) is
  is-loaded=TRUE, nonexistent=TRUE, user_name NULL and InputSources NULL,
  with no restart involved. A real user without a keyfile gets `[]`, not
  NULL.
expected: the service does not crash, and the greeter's layouts are whole again once the daemon is back
reproduction: act-probe.py, nonexistent-probe.py, greeter-restart.sh (this directory); the crash itself in research/indicator-keyboard-2166139/ (ik.sh, +unity2 3 of 3 SIGSEGV)
evidence: logs/01-05
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
design_review_result: PENDING
architectural_task: false
correct_layer: >
  The consumer. NULL from these getters is part of the library's
  observable contract for nonexistent users; this is its steady state, not
  a race. indicator-keyboard reaches that state: update_greeter_user() calls
  get_user() on the unity-greeter entry name, and the entries include
  `*other` and `*guest` (INFERENCE from main.vala:306-324 and logs/04; not
  run under unity-greeter). A library fix would remove only the restart
  window.
defensive_workaround_rejected: >
  Not a workaround: the guard is where the library's NULL arrives, and the
  library returns NULL in a documented-by-behaviour state that no library
  change would remove. Hiding NULL inside libaccountsservice (returning an
  empty aa{ss}) would change a shared library's API for every consumer.
code_risks:
  ownership_lifetime: checked  # (transfer none) value is only read in place
  callbacks_cancellation: not_applicable
  threading_reentrancy: not_applicable
  ABI_API_file_list: not_applicable  # no code change
unknowns:
  - the `*other`/`*guest` path was shown at library level (logs/04) and in
    the code, not run under unity-greeter
  - the LightDM user-name guard in +unity3 (no NULL name to
    lightdm_user_list_get_user_by_name) still has no test of its own; it only
    removes a g_return_val_if_fail critical, not a crash
  - the ~240 ms recovery comes through LightDM.UserList user-changed; that it
    is this signal and not another one is inferred from timing
```

## Mechanism

### The restart window (logs/01-03)

`act-probe.py` watches the manager and the user `mike` with 20 ms snapshots
while accounts-daemon restarts. Every run looked the same (3 of 3):

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
user", and it holds for as long as the object lives. An existing user with
no keyfile gets an empty `aa{ss}` from the daemon (patch 0016), never NULL.

### What the library documents

`act_user_get_input_sources()` is added by the Ubuntu-only patch
`0016-add-input-sources-support.patch`. It is annotated
`(transfer none)`, not `(nullable)`, so the earlier record's "accountsservice
documents that NULL" was wrong. The behaviour is the same as for every other
getter written on the `accounts_proxy == NULL` pattern. `act_user_is_loaded()`
says the object is "loaded and ready to read from", which the restart window
contradicts.

## The consumer after the restart: layouts recover (logs/05)

On target2, at lightdm-gtk-greeter, +unity3 ran as `lightdm` on the
greeter's bus (the same method as `ik.sh`). The greeter's
`org.gnome.desktop.input-sources` was recorded on every change, 3 runs:

- before: `[gb, us]`;
- 0.3-0.8 s after the restart: `[gb]`, only LightDM's system layout, written
  by `migrate_input_sources()` inside the window;
- 0.2-0.4 s later: `[gb, us]` again, right after the daemon's `Changed`;
- the service stayed alive, with no critical and no segfault.

`current` stayed 0 throughout. The unchanged +unity2 code (Ubuntu's
0ubuntu1 behaves the same here) crashed 3 of 3 in the same setup
(research/indicator-keyboard-2166139/).

## Layer decision

| Layer | What a fix there would do | Verdict |
|---|---|---|
| indicator-keyboard (consumer) | treat NULL as "no layouts", fall back; already +unity3 | **owns it**: NULL reaches it by design (nonexistent users) and in the window |
| libaccountsservice | reset `ActUser:is-loaded` on owner loss, or hold the manager's `is-loaded` until every user proxy has reloaded | closes only the restart window; nonexistent users still return NULL. `is-loaded` has been one-way (`_act_user_update_as_nonexistent` asserts `!loaded`), and consumers connect `notify::is-loaded` as a one-shot, so going back to FALSE is a behaviour change in a shared library for gnome-shell, gdm, unity-greeter, unity-control-center and others. Security updates (now 5.2) would need rebasing |
| accounts-daemon | nothing: it always exports InputSources (`[]` with no keyfile) | not involved |

The ordering in libaccountsservice is a real weakness: the manager reports
"loaded" before its users are readable. It lasts about 150 ms, heals itself,
and does not change what the consumer must do. It can go upstream as a
report (through C and May). We do not carry it as our own patch.

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

## Result

- No package change. +unity3 (`10eb95c`) stays as published.
- The previous record is corrected in `docs/DECISIONS.md`: the NULL is not
  documented; the consumer owns it for the reasons above.
- target2 is rolled back to `Clean-2` afterwards.
