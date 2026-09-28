# UNITY-20260927-012: unity-settings-daemon crash at restart - root cause, and the same defect left in the power plugin

Legacy A-L32. On 2026-09-24, while measuring the #6 shutdown path, the
archive unity-settings-daemon crashed "in its color plugin during teardown
(`libcolor.so`, signal handler)" at almost every restart
(`research/shutdown-path/`); it was closed as a probable consequence of the
compiz exit crash, without a root cause. UNITY-20260927-011 re-checked the
color fixes (+unity2/+unity3) and showed the precondition of the logout
crash: the color plugin's handler on the shared session-manager proxy
outlived `stop()`. Agent A, target `target-desktop`, 2026-09-28/29.

## Mechanism (code, FACT)

- `gnome_settings_bus_get_session_proxy()` and
  `gnome_settings_bus_get_screen_saver_proxy()` return process-wide
  singletons; `main.c` holds a reference for the life of the process, so
  they outlive every plugin.
- When the session manager sends the client `Stop` signal (and on
  `SessionOver` / name loss), `stop_manager()` calls
  `gnome_settings_manager_stop()` - every plugin is deactivated and its
  `GnomeSettingsPluginInfo` unreferenced, which finalizes the plugin and its
  manager - and then only `gtk_main_quit()`: the main loop finishes the
  current iteration, dispatching whatever is already ready in it.
- A plugin whose handler on a shared proxy was not disconnected is then
  called on freed memory if a signal of that proxy is dispatched after the
  finalize: at logout or restart, the session manager leaving the bus makes
  its proxy emit `g-properties-changed` (the 2026-09-24 logout crash's stack:
  `on_name_owner_changed` -> `g-properties-changed` ->
  `gcm_session_active_changed_cb` -> `cd_client_get_connected`, SIGSEGV).
- Plugins shipped (`dpkg -L`: libcolor, libpower, ...; no automount) and
  their handlers on the shared session proxy (source read, delegated sweep):
  color - fixed in +unity2 (disconnect in `stop()`, `g_signal_connect_object`);
  background, updates - disconnected; **power - not**: `g_signal_connect
  (session, "g-properties-changed", engine_session_properties_changed_cb)`
  and `g_signal_connect (screensaver_proxy, "g-signal",
  screensaver_signal_cb)` in `start()` (gsd-power-manager.c:3221-3229),
  `stop()` only `g_clear_object`s both (:3366, :3405), `finalize()` touches
  neither.

So the 2026-09-24 libcolor crash at restart is the 011 mechanism, reached
through `Stop` -> finalize -> the session manager's name vanishing in the
same main-loop iteration; it is gone for color since +unity2. The same
defect is still in the power plugin, in +unity5 and in every Ubuntu source,
26.10 included (sweep: its gsd-power-manager.c is byte-identical to
`ubuntu/devel`); gnome-settings-daemon fixed the session-proxy handler in
fb2ca61f (2019, 3.33.0), after u-s-d forked; its screensaver handler is
still a plain `g_signal_connect` there.

## Reproduced

Deterministic reproducer (`tools/usd-color-uaf.sh`), under gdb in the live
session: call `gnome_settings_manager_stop()` - exactly what `Stop` does -
but leave the main loop running, then change the session manager's
properties (take and drop an inhibitor: two `PropertiesChanged`). The u-s-d
user unit gets a test drop-in (`tools/zz-u012-perturb.conf`:
`GLIBC_TUNABLES=glibc.malloc.perturb=165:glibc.malloc.tcache_count=0`) so
freed memory reads 0xa5 and a use of it crashes at once.

| Build | Result |
|---|---|
| +unity5~nocolor1 (011's test build: color fixes reverted) | SIGSEGV in `idle_is_session_inhibited` <- `idle_configure` (gsd-power-manager.c:2495) <- `g_signal_emit` - the **power** handler, on the freed power manager; it fires first (`runs/01`) |
| +unity5 (published) | the same SIGSEGV in the power plugin, apport report written (`runs/02`) |

Two invalid first attempts are kept (`runs/00*`): gdb could not use
`'main.c'::manager` or `manager_object` ("value has been optimized out");
the working call goes through `gnome_settings_manager_new()`, which returns
the existing singleton.

**Natural restarts do not hit it today**: 11 restarts through Unity's dialog
on +unity5 with the same drop-in, 0 u-s-d crashes (`runs/03`, `runs/04`).
The plugins are unloaded at 60 ms after the restart request (a burst of
dconf `unwatch_fast` from u-s-d before systemd stops the session scope,
`runs/04`), i.e. through `Stop`; what is missing is the session manager's
name vanishing inside that same main-loop iteration, which cinnamon-session
+unity3's exit timing (UNITY-20260927-003) no longer produces as it did on
2026-09-24. (A gdb trace of the exit path lost its output at shutdown,
`runs/04a`; u-s-d's own `g_debug` is not logged by its handler.)

Side finding: in normal operation every session-manager property change
logs `gcm_session_active_changed_cb: assertion 'active_v != NULL' failed`
(cinnamon-session does not export `SessionIsActive`) - harmless noise,
present in +unity5.

## Evidence card

```yaml
task_id: UNITY-20260927-012
package: unity-settings-daemon
target_series: resolute
issue: legacy A-L32 - u-s-d crash in libcolor at restart; root cause, and the same stale handler in the power plugin
status: REPRODUCED   # deterministically: power plugin UAF on +unity5 and on the nocolor build; not naturally in 11 restarts today
issue_search_result: NOT_FOUND   # no bug for idle_is_session_inhibited / engine_session_properties_changed_cb (sweep); LP #1567116 is a different power crash (fixed 2016)
source_version: 15.04.1+21.10.20220802-0ubuntu7+unity5
binary_version: same (published)
source_commit: Ubuntu-Unity-LifeSupport/unity-settings-daemon unity/resolute d2c24b7
observed: >-
  With the plugins finalized by gnome_settings_manager_stop() and the main
  loop still running, a session-manager property change crashes u-s-d in the
  power plugin's handler (idle_is_session_inhibited, freed manager); color's
  handler is disconnected since +unity2.
expected: no plugin handler runs after its plugin stopped or was finalized
reproduction: tools/usd-color-uaf.sh with tools/zz-u012-perturb.conf; natural: tools/restart-series.sh + restart-via-dialog.sh + usd-restart-check.sh
evidence: runs/00-04
root_cause: >-
  gsd_power_manager_start() connects handlers to two process-wide shared
  proxies with g_signal_connect and gsd_power_manager_stop()/finalize()
  never disconnect them
root_cause_mechanism: see "Mechanism" above
root_cause_evidence: runs/01, runs/02 (backtraces), gsd-power-manager.c:3221-3229, :3366, :3405
invariant: a plugin's handlers on the shared session and screensaver proxies do not outlive its stop()
existing_fix_result: NOT_FIXED   # no Ubuntu/Unity branch, 26.10 identical; gnome-settings-daemon fb2ca61f (session proxy only), not in u-s-d
issue_search_result_detail: sweep 2026-09-28, sources in the task evidence
candidate_approaches:
  - "F1: in gsd_power_manager_stop() disconnect both handlers
    (g_signal_handlers_disconnect_by_data on session and screensaver_proxy)
    before dropping the references, and connect them with
    g_signal_connect_object(..., manager, 0) in start() - what the color
    plugin does since +unity2; fb2ca61f's choice for the session proxy."
  - "F2: only g_signal_connect_object (fb2ca61f exactly): covers
    finalize, but a stopped-and-not-finalized manager still gets callbacks
    (priv->session NULL is checked in idle_configure's helpers, but not
    everywhere, e.g. screensaver_signal_cb)."
  - "F3: guard inside the callbacks (return if stopped): cannot help once
    the manager is freed - rejected."
  - "F4: stop making the proxies shared singletons: upstream design, every
    plugin relies on it - rejected."
chosen_approach: F1 (candidate commit 2ac4128 on fix/power-shared-proxies, not yet on unity/resolute)
correct_layer: >-
  The power manager owns the handlers it connects; the shared proxy cannot
  know when a plugin goes away. Disconnecting in the plugin's own stop(),
  plus g_signal_connect_object as a backstop for finalize, keeps the
  invariant where it is created - the same layer and pattern as the color
  fix and upstream's fb2ca61f.
defensive_workaround_rejected: F3 above
alternatives_rejected: [F2 - weaker invariant, F3, F4]
code_risks:
  ownership_lifetime: >-
    g_signal_connect_object holds no reference on manager; disconnect_by_data
    matches every handler with data == manager on that instance (power
    connects only these two to them)
  callbacks_cancellation: checked - after stop() no handler of power remains on the shared proxies
  threading_reentrancy: main-loop only
  ABI_API_file_list: not_applicable - static functions, no API change
unknowns:
  - "Natural rate today: 0 in 11 restarts; the trigger needs the session
    manager's name to vanish in the main-loop iteration of Stop."
  - "The color variant is shown again with a build that has the power fix
    and the color fixes reverted (test build +test2) - pending."
architectural_task: false
design_challenger_required: true   # a lifetime/callback choice
design_review_result: PENDING
```
