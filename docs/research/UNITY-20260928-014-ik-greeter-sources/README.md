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
design_review_result: PENDING
code_risks:
  ownership_lifetime: checked (no new references; users is the existing SList<weak Act.User>, UNITY-20260928-016)
  callbacks_cancellation: checked (the skipped write is redone by the existing LightDM user-changed callback)
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
  instance writes `[gb, us]` / 0. No lasting effect seen.
- FACT (logs/05, `nonexistent-in-window.py`, 3 of 3): in the manager's
  `notify::is-loaded` handler, the listed user mike is `loaded=True
  nonexistent=False user_name=None uid=0 input_sources=NULL`; before the
  restart `user_name='mike' uid=1000`.

## Harm

- FACT: the only reader of the greeter's `current` is indicator-keyboard
  itself and each read checks the index (main.vala:619, 690, 1164, 1264,
  UNITY-20260927-024). unity-greeter disables the u-s-d keyboard plugin, so
  the X layout used for the password is not taken from these settings.
- FACT: no crash, no persisted value in the tests above.
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

`invariant`: the greeter's input sources are only written from complete
AccountsService data; `current < n_sources`, or 0 when there are none.

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

Risk to check live for A: the skip relies on the recovery pass seeing the
data. INFERENCE from logs/02: the recovery write already contains mike's
`[gb, us]` with no `DISPLAY` and a NULL-name fallback unavailable, so the
`Act.User` had its data when LightDM's `user-changed` ran. If a run shows the
recovery pass also skipping (settings left at the old values while the daemon
is back), A needs a second trigger (the `Act.User` `changed` signal). Live
validation: N restarts, every one must end with the settings written once,
from complete data, and no intermediate write.
