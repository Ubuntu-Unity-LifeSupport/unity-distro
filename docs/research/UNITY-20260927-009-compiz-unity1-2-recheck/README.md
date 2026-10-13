# UNITY-20260927-009: compiz +unity1 and +unity2 re-checked on a clean snapshot

Legacy A-L09/A-L10. compiz `1:0.9.14.2+25.10.20250930-0ubuntu3+unity2` carries
two changes of ours:

- `+unity1` (`research/shutdown-path/`): the XSMP die callback leaves with
  `_exit(0)` instead of `exit(0)`, because `exit()` ran Mesa's exit handlers
  while GDBus's worker was still writing and compiz crashed at logout/restart
  (3 in 7 restarts under cinnamon-session `+unity1`, 0 in 8 with the fix);
- `+unity2` (`research/compiz-restart/`): the first-decoration workarea
  clamp in `setWindowFrameExtents` uses the window's own viewport, so a
  compiz restart no longer moves windows on lower workspaces up by a title
  bar.

Agent A, target `target-desktop`, 2026-09-28. No code change.

## Method: isolate compiz

1. `target-desktop` restored to `Clean-updated-2026-09-23` (the vbox MCP was
   unreachable for a while, the task was BLOCKED meanwhile). Checked inside:
   no `~/.dirty`, new boot, stock unity and compiz, no aptly source.
2. Our aptly source added and the six compiz binaries **held at the stock
   `0ubuntu3`** (`apt-mark hold compiz compiz-core compiz-gnome
   compiz-plugins-default libcompizconfig0 libdecoration0t64`), then `apt-get
   full-upgrade`: everything else ours (unity `+unity11`, cinnamon-session
   `+unity3`, nux `+unity2`, gtk-nocsd `4.8-1+unity3`, ...). So "before"
   differs from "after" in compiz only - unlike UNITY-20260927-008, where
   stock unity's crashes on every restart muddled the drift.
3. **Before** (stock compiz): the SIGHUP scenario of UNITY-20260927-008
   (`tools/run-all.sh`: 2x2 workspaces, an xterm per viewport, lower row at
   y 1032, five `killall -1 compiz`, then `systemctl --user restart
   unity7.service`), and restarts through Unity's end-session dialog
   (`tools/restart-via-dialog.sh`: menu -> "Выключение..." ->
   "Перезагрузить", kernel `core_pattern` to `/var/tmp`, checked after each
   boot by `tools/restart-check.sh`; the last two with `tools/compiz-exit.bt`
   tracing how compiz leaves).
4. Holds removed, `full-upgrade` (compiz `+unity2`), reboot. **After**: the
   same SIGHUP scenario and 7 traced restarts.

## Result

| Check | Before: compiz stock `0ubuntu3` | After: compiz `+unity2` |
|---|---|---|
| lower-row windows, 5x SIGHUP (`runs/01`, `runs/05`) | 1032 -> 1000 -> 968 -> 936 -> 904 -> 872, one title bar (32 px) up per restart; 840 after the unity7 restart; upper row unchanged | 1032 after every SIGHUP and after the unity7 restart; every window to the pixel |
| compiz on SIGHUP | same pid all five times, no crash (unity `+unity11` has the teardown fixes) | same |
| how compiz leaves at a restart through the dialog (`runs/03`, `runs/04`) | **`exit(0)` called from `IceProcessMessages`** (the XSMP die callback), then the exit handlers, then `_exit` - 2 of 2 traced | **`_exit(0)` directly**, no exit handlers - 6 of 7; the 7th `_exit(1)` directly (see below) |
| compiz crashes at restart | **0 in 9** (7 in `runs/02`, 2 in `runs/03`): no core in `/var/tmp`, no segfault or dump in the journal | 0 in 7 |

So:

- **+unity2: reproduced and fixed.** With only compiz differing, stock
  compiz moves lower-row windows up 32 px per restart; `+unity2` keeps them.
- **+unity1: the fix is in place and does what it says, but the crash it
  prevents did not reproduce on today's stack.** Stock compiz still leaves
  through `exit()` from the ICE die callback while other threads run - the
  racy path is taken on every restart - but 9 restarts gave no crash. The
  2026-09-24 rate (3 in 7) was measured with cinnamon-session `+unity1`,
  whose "die" came milliseconds after Unity's last D-Bus traffic; with
  cinnamon-session `+unity3` (quits on logind's PrepareForShutdown,
  UNITY-20260927-003) the timing is different. With 9 clean runs, a rate
  like 3/7 is unlikely (about 0.7% by chance), but a lower rate is not
  excluded.

`runs/02` notes: the first line is a restart checked by hand after I had
stopped and restarted the series script (my own mistake: I switched the
worktree's branch while the script ran from it); one series step did not
restart (the same boot appears twice - the menu click came before the
session was ready) and the next boot shows `clicked=2`. Seven distinct boots.

The one `_exit(1)`: the compiz of restart 1 in `runs/04` was the one started
by `systemctl --user restart unity7.service` at the end of the SIGHUP
scenario; it left directly with status 1 rather than through the die
callback. INFERENCE: a compiz started outside the session's own startup is
not in the same XSMP state; it still left without exit handlers and without a
crash. Not investigated.

## Evidence card

```yaml
task_id: UNITY-20260927-009
package: compiz
target_series: resolute
issue: legacy A-L09/A-L10 - compiz +unity1 (_exit in the XSMP die callback) and +unity2 (frame-extents clamp on the window's viewport), re-checked on a clean snapshot
status: REPRODUCED   # +unity2's drift with stock compiz; +unity1's crash NOT reproduced today (0/9), its racy exit() path reproduced (2/2 traced)
issue_search_result: FOUND   # research/shutdown-path, research/compiz-restart
source_version: compiz 1:0.9.14.2+25.10.20250930-0ubuntu3+unity2 (published)
binary_version: same, on target after full-upgrade from our aptly
source_commit: Ubuntu-Unity-LifeSupport/compiz 07c0ebe (+unity1), 2241828 (+unity2)
observed: >-
  Stock compiz with the rest of our stack: lower-row windows up 32 px per
  restart; at a restart compiz leaves through exit() from the XSMP die
  callback (no crash in 9). compiz +unity2: windows stay; compiz leaves
  through _exit() (0 crashes in 7).
expected: windows keep their positions over compiz restarts; compiz leaves a session without running exit handlers under live threads
reproduction: tools/run-all.sh; tools/restart-series.sh with restart-via-dialog.sh, restart-check.sh, compiz-exit.bt
evidence: runs/01-05; target journal 2026-09-28 17:14-18:26 UTC
existing_fix_result: FIXED_LOCAL
existing_fix_evidence: before/after with compiz as the only difference, table above
chosen_approach: NONE - no change
code_risks:
  ownership_lifetime: not_applicable
  callbacks_cancellation: not_applicable
  threading_reentrancy: not_applicable
  ABI_API_file_list: not_applicable - no change
unknowns:
  - "+unity1's crash rate on today's stack: 0 in 9 without the fix; a low
    rate is not excluded. The fix's effect is shown on its mechanism (no exit
    handlers) rather than on a crash count."
  - "Layer of +unity1 (exit vs _exit in the die callback), not re-reviewed:
    _exit also skips anything a plugin would flush in a destructor or atexit
    handler (e.g. a pending GSettings write made just before 'die'); nothing
    observed, not measured. No reason found to doubt the choice, so no Design
    Challenger (as agreed with the coordinator)."
  - "The _exit(1) of a compiz started by systemctl --user restart (above)."
  - "Multi-monitor not covered."
design_challenger_required: false
architectural_task: false
design_review_result: NOT_REQUIRED
```

## Outcome

`ALREADY_FIXED` / `FIXED_LOCAL`: both changes are published and active on a
clean system updated from our aptly. +unity2's defect reproduces with stock
compiz and is gone with ours. +unity1 changes how compiz leaves exactly as
intended; the crash it was made for did not reproduce with today's
cinnamon-session in 9 restarts, so its benefit now is protection against a
race that is rarer than when it was measured. Target left as target = aptly
(no holds), `~/.dirty` present, xdotool installed.
