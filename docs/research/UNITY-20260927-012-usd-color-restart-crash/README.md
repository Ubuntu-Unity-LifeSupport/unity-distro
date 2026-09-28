# UNITY-20260927-012: unity-settings-daemon crash at restart - root cause, and the same defect left in the power plugin

Legacy A-L32. On 2026-09-24, while measuring the #6 shutdown path, the
archive unity-settings-daemon crashed "in its color plugin during teardown
(`libcolor.so`, signal handler)" at almost every restart
(`research/shutdown-path/README.md:383`, no stack kept); it was closed as a
probable consequence of the compiz exit crash, without a root cause.
UNITY-20260927-011 re-checked the color fixes (+unity2/+unity3) and showed
the precondition of the logout crash: the color plugin's handler on the
shared session-manager proxy outlived `stop()`. Agent A, target
`target-desktop`, 2026-09-28/29.

## Mechanism (code, FACT unless marked)

- `gnome_settings_bus_get_session_proxy()` returns a process-wide singleton;
  `main.c:354` holds a reference to it for the life of the process, so it
  outlives every plugin. `gnome_settings_bus_get_screen_saver_proxy()` is a
  weak singleton kept alive by the plugins that hold it (power,
  screensaver-proxy, ...): power's screensaver handler outlives power only
  while another holder is alive, which depends on unload order.
- On the session manager's client `Stop` (and `SessionOver`, name loss),
  `stop_manager()` calls `gnome_settings_manager_stop()`: `_unload_all()`
  deactivates every plugin and unrefs its `GnomeSettingsPluginInfo`
  (gnome-settings-manager.c:375), whose finalize unrefs the plugin
  (plugin-info.c:97), whose finalize unrefs the manager
  (gnome-settings-plugin.h:113); nothing else holds the power or color
  manager, so both are finalized. Then only `gtk_main_quit()`: the sources
  already chosen for the current main-loop iteration are still dispatched.
- A handler left on a shared proxy then runs on freed memory if that proxy's
  signal is among them. **Which handler crashes depends on the signal**:
  - the session manager **leaving the bus** makes the proxy emit
    `g-properties-changed` with an empty `changed` and invalidated
    properties. color's `gcm_session_active_changed_cb` reads
    `manager->priv` unconditionally (gsd-color-manager.c:2103-2111) and
    crashes; power's `engine_session_properties_changed_cb` touches
    `manager` only when `changed` holds `SessionIsActive` or
    `InhibitedActions` (gsd-power-manager.c:2933-2959) and does nothing.
    INFERENCE: this is why the 2026-09-24 crash was in libcolor.
  - an **`InhibitedActions`** change (an inhibitor taken or dropped, e.g. by
    an application exiting at logout) or a **`SessionIsActive`** change after
    Stop crashes power's handler; a screensaver `ActiveChanged` would reach
    `screensaver_signal_cb`, which has no guard. INFERENCE: possible at
    logout/restart, not observed.
- Plugins shipped (`dpkg -L`: libcolor, libpower, ...; no automount) and
  their handlers on the shared proxies (source read and delegated sweep;
  proxy handlers only): color - disconnected since +unity2; background,
  updates - disconnected; smartcard, media-keys - no handlers; **power - not
  disconnected**: `g_signal_connect (session, "g-properties-changed")` and
  `g_signal_connect (screensaver_proxy, "g-signal")` in `start()`
  (gsd-power-manager.c:3221-3229), `stop()` only `g_clear_object`s both
  (:3366, :3405), `finalize()` touches neither. The same code is in every
  Ubuntu source, 26.10 included (sweep: its gsd-power-manager.c is
  byte-identical to `ubuntu/devel`); gnome-settings-daemon fixed the session
  handler in fb2ca61f (2019, 3.33.0), after u-s-d forked; its screensaver
  handler is still a plain `g_signal_connect` there.

## Reproducers (deterministic, under gdb, in the live session)

Both make u-s-d run `gnome_settings_manager_stop()` - what `Stop` does - by
`call (void) gnome_settings_manager_stop (gnome_settings_manager_new ())`
(`gnome_settings_manager_new()` returns the existing singleton;
`'main.c'::manager` and `manager_object` are optimized out, `runs/00*`),
but leave the main loop running, then send a signal on the session proxy:

- `tools/usd-color-uaf.sh`: an inhibitor taken and dropped (two
  `InhibitedActions` changes);
- `tools/usd-uaf-namevanish.sh`: cinnamon-session killed, so
  `org.gnome.SessionManager` vanishes - the natural trigger (ends the
  session; lightdm restarted after).

The u-s-d user unit gets a test drop-in (`tools/zz-u012-perturb.conf`:
`glibc.malloc.perturb=165`, tcache off, `G_MESSAGES_DEBUG=all`) so freed
memory reads 0xa5. What the reproducers do not model: `gtk_main_quit()` is
skipped, so the window after Stop is open indefinitely instead of one
main-loop iteration; there is no QueryEndSession/EndSession sequence.

| Build | Inhibitor trigger | Session manager vanishes |
|---|---|---|
| +unity5~nocolor1 (011's test build, color fixes reverted) | SIGSEGV in power: `idle_is_session_inhibited` <- `idle_configure` (:2495) (`runs/01`) | - |
| +unity5 (published) | SIGSEGV in power, same frame; apport report `Date: 00:22:24` (`runs/02`) | power's handler **runs on the freed manager** and returns (empty `changed`); color's is not called; no SIGSEGV until gdb stopped on a SIGCONT of the session teardown (an earlier version of the tool, before `handle SIGCONT nostop`; the backtrace in the file is that pango thread's), no crash report afterwards (`runs/05`) |
| +unity5+test2 (power fix, color fixes reverted) | SIGSEGV in color: `gcm_session_active_changed_cb`, `priv=0xa5a5a5a5a5a5a5a5` (`runs/06`) | **SIGSEGV in color**, same frame, one apport report (`/var/crash` was emptied right before this run, so the count is of new reports; the report itself was deleted later, its `Date:` not kept) - the 2026-09-24 crash (`runs/07`) |
| +unity5+test1 (power fix) | no power or color callback after stop, no crash (`runs/08`) | no callback, no crash (`runs/09`) |

So: the 2026-09-24 libcolor crash is the color handler outliving the
finalize, triggered by the session manager leaving the bus (reproduced
with the fixes reverted; FACT for the mechanism, INFERENCE that it is the
same event as the unstacked 2026-09-24 report); color is fixed since +unity2.
The power plugin still has the defect in +unity5; on the natural trigger its
handler runs on freed memory without crashing, on an inhibitor change after
Stop it crashes.

## Natural restarts

11 restarts through Unity's dialog on +unity5 with the drop-in: 0 u-s-d
crashes (`runs/03`, `runs/04`); on +unity5+test1, 6 restarts, 0 (`runs/12`; the 6 criticals in its first line are the previous boot's regression check - `active_v` assertions from its inhibitor calls). INFERENCE:
the dconf `unwatch_fast` burst ~60 ms after the restart request suggests
the plugins are unloaded before systemd's SIGTERM, but it does not
distinguish Stop from SIGTERM (whose `g_object_unref(manager)` after the
loop unloads them too) and the raw lines are not kept; u-s-d's own
`g_debug` is not logged by its handler; a gdb trace lost its output at
shutdown (`runs/04a`). The criticals counted in `runs/03` restart 6 and
`runs/04` restart 2 are `setup_bg: assertion 'manager->priv->bg == NULL'`
(background plugin at login, unrelated).

## The fix and power's behaviour (candidate `2ac4128`)

`gsd_power_manager_stop()` disconnects its handlers from both shared proxies
(`g_signal_handlers_disconnect_by_data`) before dropping them, and `start()`
connects them with `g_signal_connect_object (..., manager, 0)` as a
backstop for a finalize without stop - the color plugin's +unity2 pattern
and fb2ca61f's choice. Checked on a fresh boot each (`tools/usd-power-regress.sh`,
`runs/11`, `runs/10`):

| | +unity5 | +test1 |
|---|---|---|
| inhibitor taken and dropped, plugin running | 2 callbacks, idle reconfigured | 2 callbacks, idle reconfigured |
| plugin switched off, then inhibitor | 2 callbacks - into the stopped manager | 0 |
| switched on again, then inhibitor | 4 callbacks - handlers doubled | 2 |
| screen lock/unlock (`loginctl`) | 0 screensaver callbacks | 0 screensaver callbacks |

So the fix also removes a visible defect of +unity5: every off/on of the
power plugin adds another handler and the stopped manager keeps being
called. The screensaver path could not be exercised: compiz owns
`org.gnome.ScreenSaver` and no `ActiveChanged` came on a `loginctl` lock in
either build (`runs/11b`: a second run in one +unity5 process started with
the handlers already doubled).

## Release build +unity7

`15.04.1+21.10.20220802-0ubuntu7+unity7`: the fix (`7c5f234`, cherry-picked
from `2ac4128`) and its changelog (`b570a22`) on top of
`a/UNITY-20260927-052` (`f674b6b`, u-s-d +unity6 - the idle-monitor fix,
built and reviewed, waiting for the aptly freeze to lift), branch
`a/UNITY-20260927-012` on Ubuntu-Unity-LifeSupport/unity-settings-daemon
(pushed from a GitHub clone; the push reported `remote rejected (failure)`
but the remote ref is `b570a22` - `git fetch`, `ls-remote`, `push --dry-run`
"Everything up-to-date"). Built with `scripts/build_sbuild.py`, exit 0
(`build/UNITY-20260927-012-unity-settings-daemon-build-manifest.json`);
pre-build ordering check `version-prebuild.json` (newer than resolute's
0ubuntu6; `UNKNOWN` by design before a build). So +unity7 carries both
fixes and publishes after, or instead of, 052's +unity6.

On target (+unity7 with its dbgsym, perturb drop-in): power regression
2 / 0 / 2 callbacks, not doubled (`runs/13`); inhibitor reproducer: no
callback after stop, no crash (`runs/14`); session manager vanishing: no
callback, no crash (`runs/15`).

## Evidence card

```yaml
task_id: UNITY-20260927-012
package: unity-settings-daemon
target_series: resolute
issue: legacy A-L32 - u-s-d crash in libcolor at restart; root cause, and the same stale shared-proxy handlers in the power plugin
status: REPRODUCED   # deterministically: color variant (fixes reverted) on the name-vanish trigger, power variant on +unity5 on an inhibitor trigger; not naturally in 11 restarts today
issue_search_result: NOT_FOUND   # no bug for idle_is_session_inhibited / engine_session_properties_changed_cb (sweep); LP #1567116 is a different power crash (fixed 2016)
source_version: 15.04.1+21.10.20220802-0ubuntu7+unity5
binary_version: same (published)
source_commit: Ubuntu-Unity-LifeSupport/unity-settings-daemon unity/resolute d2c24b7
observed: see the tables above
expected: no plugin handler runs after its plugin stopped or was finalized
reproduction: tools/usd-color-uaf.sh, tools/usd-uaf-namevanish.sh with tools/zz-u012-perturb.conf
reproduction_result: PASS
evidence: runs/00-12
root_cause: >-
  gsd_power_manager_start() connects handlers to the shared session and
  screensaver proxies with g_signal_connect; stop()/finalize() never
  disconnect them
root_cause_mechanism: see "Mechanism"
root_cause_evidence: runs/01, runs/02 (power), runs/06, runs/07 (color variant), gsd-power-manager.c:3221-3229, :3366, :3405
invariant: >-
  the power plugin's handlers on the shared session and screensaver proxies
  do not outlive its stop() (narrowed: other long-lived registrations of the
  power manager are out of scope - follow-ups below)
existing_fix_result: NOT_FIXED   # no Ubuntu/Unity branch, 26.10 identical; gnome-settings-daemon fb2ca61f (session proxy only), not in u-s-d
candidate_approaches:
  - "F1: disconnect both handlers in stop() and connect with
    g_signal_connect_object - chosen"
  - "F2: g_signal_connect_object only (fb2ca61f): covers finalize, but a
    stopped, not finalized manager keeps being called (the doubled handlers
    above) and screensaver_signal_cb has no guard"
  - "F3: guards inside the callbacks: cannot help once the manager is freed"
  - "F4: per-plugin proxies instead of shared singletons: upstream design"
chosen_approach: F1, candidate commit 2ac4128 (fix/power-shared-proxies), not yet on unity/resolute
correct_layer: >-
  The power manager owns the handlers it connects; the shared proxy cannot
  know when a plugin goes away. Disconnecting in the plugin's own stop(),
  with g_signal_connect_object as a backstop, keeps the invariant where it is
  created - the layer and pattern of the color fix and of fb2ca61f.
defensive_workaround_rejected: F3
alternatives_rejected: [F2, F3, F4]
code_risks:
  ownership_lifetime: >-
    g_signal_connect_object holds no reference on manager;
    disconnect_by_data matches its closures (data = manager); power connects
    only these two handlers on these proxies and no other plugin passes the
    power manager as data
  callbacks_cancellation: checked - after stop() no power handler remains on the session proxy (measured, runs/10) nor on the screensaver proxy (code read only: the screensaver path could not be triggered); a second stop is a no-op
  threading_reentrancy: main-loop only
  ABI_API_file_list: not_applicable - static functions, no API change
unknowns:
  - "Natural rate today: 0 in 11 restarts on +unity5; the power variant needs an InhibitedActions/SessionIsActive change or a screensaver ActiveChanged after Stop."
  - "The screensaver handler path was not exercised (no ActiveChanged on a loginctl lock)."
  - "g_signal_handlers_disconnect_matched: assertion 'G_TYPE_CHECK_INSTANCE (instance)' at stop, in stock too - source not identified (candidate: gsd-updates-refresh.c:554 with a NULL proxy_session)."
follow_ups_proposed:
  - "power: other registrations of the manager that outlive stop() -
    idle-monitor watches (:2348, :2537-2617, not cleared), the D-Bus object
    registered on the session connection (:3748, never unregistered),
    timers with manager as data (:1509, :1540, :2661), async proxy creation
    with a NULL cancellable (:3258, :3269), notification weak pointers into
    priv (:987); code read by the Design Challenger, not reproduced"
  - "screensaver-proxy: g_dbus_connection_register_object without unregister
    (gsd-screensaver-proxy-manager.c:324, :332; stop :386-393); apps'
    org.freedesktop.ScreenSaver Inhibit/UnInhibit at logout are a realistic
    trigger; not reproduced"
architectural_task: false
design_challenger_required: true
design_review_result: APPROVE   # review 1: REVISE, review 2: APPROVE with four card edits (applied)
```
