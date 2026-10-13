# UNITY-20260927-011: unity-settings-daemon color plugin fixes (+unity2/+unity3) re-checked on a clean snapshot

Legacy item. unity-settings-daemon carries two fixes of ours in the color
plugin (`plugins/color/gsd-color-manager.c`, `research/usd-color-logout-crash/`):

- `+unity2` (`10bb1c9`): the plugin connected `gcm_session_active_changed_cb`
  to the **shared** session-manager proxy and never disconnected it -
  `stop()` cleared `priv->session` first, so `finalize()` disconnected
  nothing. Every later property change of the session manager called into a
  stopped manager, and after finalize into freed memory: the SIGSEGV in
  `cd_client_get_connected` at logout. Fix: disconnect in `stop()`, connect
  with `g_signal_connect_object`.
- `+unity3` (`cc665b6`): `init()` created the colord client and the other
  resources that `stop()` destroys, so a plugin switched off and on started
  with nothing and never reconnected to colord. Fix: create them in
  `start()`.

Agent A, target `target-desktop`, 2026-09-28. No code change.

## How the color fixes were isolated

Our u-s-d is at `+unity5`; `+unity4`/`+unity5` changed other things (idle
monitor, helpers, one daemon per session from the systemd user unit, an
apport hook). The stock `0ubuntu6` would differ in all of them, and our aptly
holds only the latest version, so holding the package would not isolate
anything. Instead:

- **Before** = a test build, `15.04.1+21.10.20220802-0ubuntu7+unity5~nocolor1`
  (**NOT FOR PUBLICATION**, built with `scripts/build_sbuild.py`, sbuild exit
  0, output kept in `~/work/a/011-usd/out-nocolor-NOT-FOR-PUBLICATION`):
  our `unity/resolute` at `+unity5` (`d2c24b7`) with `git revert` of exactly
  the two color commits (`cc665b6`, `10bb1c9`) and a changelog entry, local
  commit `438f34a`. Its whole difference from `+unity5` is
  `plugins/color/gsd-color-manager.c` and `debian/changelog`
  (`tools/nocolor-test-build.diff`).
- **After** = `+unity5` from our aptly (its libcolor.so build-id
  `6c639173…` matches our dbgsym).
- Both on the same clean system: `Clean-updated-2026-09-23` restored and
  checked inside, our aptly source added, `apt-get full-upgrade` (everything
  else ours: unity `+unity11`, cinnamon-session `+unity3`, ...), each
  variant rebooted into, with its own `-dbgsym` for gdb.

## Scenarios (deterministic, under gdb)

From research/usd-color-logout-crash, adapted (`pgrep -x`, no `pgrep -f`):

- `tools/usd-color-stop-cb.sh` - the logout crash's mechanism: switch the
  plugin off (`com.canonical.unity.settings-daemon.plugins.color active
  false` -> `stop()`), then make the session manager's properties change
  twice (take and drop an inhibitor through `org.gnome.SessionManager.Inhibit`,
  two `PropertiesChanged` for `InhibitedActions`); dprintf on
  `gsd_color_manager_stop` and `gcm_session_active_changed_cb`.
- `tools/usd-color-restart.sh` - switch the plugin off and on; dprintf on
  `stop`, `start` and `gcm_session_client_connect_cb` (colord connected).

## Result (3 runs of each)

| Scenario | Before: +unity5~nocolor1 | After: +unity5 |
|---|---|---|
| callback after stop (`runs/03`, `runs/01`) | **3/3**: `STOP manager=0x64a8…`, then `CB manager=0x64a8… client=(nil)` twice - the handler runs on the stopped manager for each property change; 2 x `cd_client_get_connected: assertion 'CD_IS_CLIENT (client)' failed` | 0/3: `STOP`, no callback, 0 criticals |
| switch off and on (`runs/04`, `runs/02`) | **3/3**: `STOP`, `START`, no colord connection; `cd_client_connect: assertion 'CD_IS_CLIENT (client)' failed` | 0/3: `STOP`, `START`, `COLORD-CONNECTED`, 0 criticals |

In every run the two signals arrived (`PropertiesChanged signals: 2`) and
u-s-d kept its pid. `colord devices for this display: 1` in both columns is
the device registered at login, so it does not tell the two apart; the
connection is.

What the trace does and does not show: it shows the stale handler - the
condition of the logout crash - deterministically, and that `+unity2`
removes it. The crash itself needs the handler to fire **after finalize**
(freed memory; with the NULL client of a merely stopped manager libcolord's
`CD_IS_CLIENT` check catches it, hence the critical and no crash). That
happens only while u-s-d is shutting down at logout, as the session manager
leaves the bus - 1 in about 13 logouts on 2026-09-24. It was not forced here.

`runs/00a`, `runs/00b` are a first "after" run made without rebooting after
the upgrade: the running u-s-d was still the stock `0ubuntu6` process
(`libcolor.so (deleted)` in its maps), gdb found no symbols and the output is
the stock behaviour. Kept for the record, not counted.

## Evidence card

```yaml
task_id: UNITY-20260927-011
package: unity-settings-daemon
target_series: resolute
issue: color plugin - stale session-proxy handler after stop (logout crash, +unity2) and no colord after a restart of the plugin (+unity3), re-checked on a clean snapshot
status: REPRODUCED   # both, deterministically under gdb, 3/3, with the fixes reverted; the crash itself not forced
issue_search_result: FOUND   # research/usd-color-logout-crash
source_version: unity-settings-daemon 15.04.1+21.10.20220802-0ubuntu7+unity5 (published)
binary_version: same, on target after the tests
source_commit: Ubuntu-Unity-LifeSupport/unity-settings-daemon 10bb1c9 (+unity2), cc665b6 (+unity3); test build 438f34a (local, reverts both on d2c24b7)
observed: >-
  With the two color commits reverted: the session-proxy callback runs on the
  stopped manager for each property change (client NULL, CD_IS_CLIENT
  criticals), and a plugin switched off and on never reconnects to colord.
  With +unity5: no callback after stop, reconnects every time, no criticals.
expected: a stopped plugin receives no callbacks; a restarted plugin works again
reproduction: tools/usd-color-stop-cb.sh, tools/usd-color-restart.sh (gdb with the package's dbgsym)
evidence: runs/01-04; target journal 2026-09-28 20:56-21:05 UTC
existing_fix_result: FIXED_LOCAL
existing_fix_evidence: before/after with only the two color commits different, table above
chosen_approach: NONE - no change
code_risks:
  ownership_lifetime: not_applicable
  callbacks_cancellation: not_applicable
  threading_reentrancy: not_applicable
  ABI_API_file_list: not_applicable - no change
unknowns:
  - "The use-after-free crash at logout was not forced; the trace shows its
    precondition (the handler outliving stop) and its removal. A forced
    reproducer would need the property change between finalize and exit."
  - "Logout cycles were not counted: at the 2026-09-24 rate (1 in ~13) a
    count proves nothing either way."
design_challenger_required: false
architectural_task: false
design_review_result: NOT_REQUIRED
```

## Outcome

`ALREADY_FIXED` / `FIXED_LOCAL`: on a clean system updated from our aptly,
with the color fixes as the only difference, both defects reproduce every
time without them and never with them. Target left as target = aptly
(u-s-d `+unity5`, no holds, no dbgsym), `~/.dirty` present.
