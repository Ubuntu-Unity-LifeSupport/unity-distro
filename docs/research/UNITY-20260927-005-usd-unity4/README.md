# UNITY-20260927-005: which of unity-settings-daemon +unity4's changes fixes #1?

Revalidation of legacy item A-L19 (`research/legacy-migration-20260927/A.md`).
`15.04.1+21.10.20220802-0ubuntu7+unity4` carried three changes and a revert in
one version (`research/cursor-after-login/`). This record separates them into
defects, measures which one fixes known issue #1, and checks what the
libexecdir change brought back to life. Agent A, target `target-desktop`,
2026-09-27.

## The three changes are three defects

| Commit | Change | Defect | Present in |
|---|---|---|---|
| `90f5773` | idle-monitor: keep the X event filter when the D-Bus name is lost | **D1** - the cause of #1 | archive 0ubuntu6, our base 0ubuntu7, 26.10 |
| `85d3511` | Start the daemon once per session: from the systemd user unit | **D2** - the daemon starts twice (the trigger of D1's race) | archive 0ubuntu6, 26.10; hidden in 0ubuntu7 by D3 |
| `b503ffd` | debian: install the helpers where their callers look for them | **D3** - libexecdir broken by 0ubuntu7's move to debhelper | our base 0ubuntu7 and 26.10 only - **not** the resolute archive |
| `3b54906` | Revert of +unity1's cursor change | not a defect: removes a wrong guess, restores archive behaviour | - |

Where 0ubuntu7 comes from (FACT): `gitlab.com/ubuntu-unity/unity/unity-settings-daemon`
`ubuntu/devel` (`216f054`, Tomasz Jeruzalski, 2026-04-14, "resolute"), never
published in resolute: `rmadison` shows resolute `0ubuntu6`, stonking
`26.10.1ubuntu.build1`. So D3 is a regression of the base we chose, not of the
archive users have.

D2 and D3 are coupled: fixing D3 alone brings back the archive's double start
(0ubuntu6 starts twice because its paths are right). That is why `85d3511`
had to come with `b503ffd`.

## Measurements

Real input only (the PS/2 mouse's existing evdev node, found by name).
unity-settings-daemon runs through a `dpkg-divert`ed wrapper that keeps its PID
and writes `G_MESSAGES_DEBUG=all --debug` output to `/tmp/usd-PID.log`
(`tools/usd-debug-wrapper*.sh`); the plugin's "Attempting to hide/show the
cursor" is the visibility signal (a VirtualBox screenshot cannot show the
pointer).

### Deterministic reproducer (`tools/repro2.sh`) - the regression test

Stop every instance, start one from the unit, wait until the cursor plugin has
hidden the pointer, take `org.gnome.Mutter.IdleMonitor` away for 2 s
(`tools/steal-idle.py`), move the real mouse, and read only what the plugin
logged after the move. `NOSTEAL=1` skips the name theft (control).

| Build | With name loss | Control |
|---|---|---|
| archive `0ubuntu6` | **FAIL 3/3** (nothing logged after the move) | PASS 1/1 |
| `0ubuntu7+unity4~v1` = +unity4 **without** `85d3511` (D1 and D3 fixed, double start back) | PASS 3/3 | PASS 1/1 |
| published `0ubuntu7+unity5` | PASS 3/3 | PASS 1/1 |

`runs/repro2-*.txt`; each run shows the "Lost or failed to acquire name" /
"Acquired name" pair. `+unity4~v1` is a local test build
(`~/work/a/usd-005`, source equal to `+unity4` except the reverted commit and
the changelog - checked with `diff -r` of the unpacked sources), not
published.

The older `repro1.sh` gave invalid results on 0ubuntu6 (`runs/repro1-0ubuntu6.txt`):
it restarts only the systemd unit, and when the xdg-autostart copy had won the
login, the restarted unit exited on the taken name and the script reported an
old "show". `repro2.sh` stops both launchers first.

### Cold logins, 12 per build (`tools/cursor-boots.sh`, `runs/boots-*.log`)

| Build | Instances started | Survivor lost the name | Pointer shown after real input |
|---|---|---|---|
| archive `0ubuntu6` | 2 in 12/12 (survivor: autostart copy 6, unit 6) | 0 | 12/12 |
| `+unity4~v1` | 2 in 12/12 (autostart 5, unit 7) | 0 | 12/12 |
| published `+unity5` | 1 in 12/12 (always the unit) | 0 | 12/12 |

Cold logins did not reproduce #1 today on the archive (0/12; on 2026-09-26
the same setup gave 2/12, `research/cursor-after-login/runs/series-c-0ubuntu6.log`).
The race is real but rare, so a 12-login series is not a reliable "fail
before"; the deterministic reproducer is the regression test.

### What the libexecdir change brought back (`tools/autostart-inventory.sh`, `runs/inventory-*.txt`)

| Item shipped by the package | archive 0ubuntu6 | +unity3 (0ubuntu7 base) | +unity4~v1 | +unity5 |
|---|---|---|---|---|
| `/etc/xdg/autostart/unity-settings-daemon.desktop` | runs localeexec -> second instance | points at missing `/usr/libexec/...` | second instance | `X-systemd-skip=true`, not generated |
| `/etc/xdg/autostart/unity-fallback-mount-helper.desktop` | running | points at missing `/usr/libexec/...` | running | running |
| user unit `ExecStart` | binary | binary | binary | `localeexec` |
| polkit `usd-backlight-helper`, `usd-wacom-led-helper` | exist | missing path | exist | exist |

So the only program "revived" in a Unity session is
`unity-fallback-mount-helper`, and the archive runs it too: +unity5 matches
0ubuntu6 here, and only our +unity3 differed. No journal error from it or from
`localeexec` in any boot inventoried (its lines are gvfs volume-monitor
activations).

Duplicates: `nemo-desktop` also runs with `org.cinnamon.desktop.media-handling
automount(-open)=true`, next to the helper's `org.gnome.desktop.media-handling`.
Inserting a real medium (VirtualBox Guest Additions ISO in the VM's DVD drive,
`runs/media-*.txt`): **neither mounted it, no window opened** - no duplicate,
but no automount either. The helper, run with debug output, logged the
removal and nothing on insertion: it asks `org.gnome.SessionManager` for
`SessionIsActive`, which cinnamon-session does not have ("No such property"),
so it treats the session as inactive (INFERENCE from
`gsd-automount-manager.c:217` and the missing log line). Separate finding, not
caused by +unity4: automount does not work in this Unity session, with the
archive package as well (same helper, same session manager).

The polkit helpers (backlight, Wacom LED) have no hardware in the VM; their
paths are right, their function was not exercised.

## Evidence cards

### D1 - idle monitor loses its X event filter with the bus name (the #1 fix)

```yaml
task_id: UNITY-20260927-005
package: unity-settings-daemon
target_series: resolute
issue: >-
  Ubuntu Unity 26.04 known issue #1 "cursor invisible after login";
  gitlab ubuntu-unity/issue-tracker #161; LP: #1390628 (2014, same symptom,
  never explained)
status: REPRODUCED
issue_search_result: FOUND
source_version: 15.04.1+21.10.20220802-0ubuntu6 (archive), 0ubuntu7+unity4/+unity5 (ours)
binary_version: measured 0ubuntu6, 0ubuntu7+unity3, 0ubuntu7+unity4~v1 (local), 0ubuntu7+unity5; target left on +unity5
source_commit: 90f5773 on unity/resolute (published in +unity4 40ed659 and +unity5 d2c24b7)
observed: >-
  After org.gnome.Mutter.IdleMonitor is lost and acquired again by a running
  daemon, real mouse input no longer makes the cursor plugin show the pointer
  it hid at start (0ubuntu6: 3/3).
expected: the first real pointer input after start shows the pointer.
reproduction: tools/repro2.sh (control NOSTEAL=1)
reproduction_result: PASS   # reproduced: FAIL on 0ubuntu6 3/3; PASS on +unity4~v1 3/3 and +unity5 3/3
evidence: runs/repro2-0ubuntu6.txt, runs/repro2-unity4v1.txt, runs/repro2-unity5.txt
root_cause: >-
  gnome-settings-daemon/gsd-idle-monitor.c added the process-wide X event
  filter (xevent_filter, which dispatches XSync alarms to every idle and
  user-active watch) in on_bus_acquired and removed it in on_name_lost;
  on_bus_acquired runs once per connection, so after a lost-and-regained name
  the filter is gone for the rest of the process.
root_cause_mechanism: >-
  The in-process watches of the cursor plugin (user-active) and the power
  plugin (idle dim/blank/sleep, gsd-power-manager.c:2537-2617) depend on
  alarm events reaching xevent_filter. Their lifetime is the process; the
  filter's lifetime was tied to owning a D-Bus name that only matters for the
  exported monitors. Any loss of the name - a second instance starting at
  login (D2), --replace, any other owner - silently disables every watch.
root_cause_evidence: >-
  2026-09-26: gdb on a live failing session re-adding the filter made the
  next movement show the pointer (research/cursor-after-login). 2026-09-27:
  the reproducer fails 3/3 on 0ubuntu6 and passes 3/3 on a build that has
  only D1 and D3 fixed and still starts twice (+unity4~v1).
invariant: >-
  Idle and user-active watches of the daemon keep firing for the life of the
  process, whoever owns org.gnome.Mutter.IdleMonitor. (D4 below can still break
  this through a different path - freed xsync state - and is a separate
  defect.)
existing_fix_result: FIXED_LOCAL
existing_fix_evidence: >-
  Only our 90f5773. Investigator sweep 2026-09-27T19:15Z: the add/remove pair
  dates from the 2014 copy (c290aeb, LP #1377847), untouched since except the
  LP #1380278 argument fix; still present in stonking 26.10.1ubuntu.build1;
  gitlab ubuntu-unity has no MR or commit after 0ubuntu7; no Launchpad bug
  names the mechanism.
candidate_approaches:
  - "D1-A (published): add the filter once when the monitors are initialised
    (gsd_idle_monitor_init_dbus), never remove it on name loss. Measured
    PASS 3/3 alone (+unity4~v1) and in +unity5."
  - "D1-B: re-add the filter in on_name_acquired. Not built."
  - "D1-C: start the daemon once (D2) and leave the idle monitor as it is.
    Not a fix: removes one trigger only."
chosen_approach: D1-A, published; no new change.
why_chosen: >-
  It ties the filter to the lifetime of what it serves (the in-process
  watches). Precedent (read by the investigator, not re-read by the owner):
  mutter 3.14 src/backends/meta-idle-monitor-dbus.c, on_name_lost only logs
  (https://gitlab.gnome.org/GNOME/mutter/-/raw/3.14.0/src/backends/meta-idle-monitor-dbus.c);
  gnome-flashback 0328eb07, filter added in init and removed in dispose, name
  callbacks empty (https://gitlab.gnome.org/GNOME/gnome-flashback/-/commit/0328eb07).
  Measured sufficient on its own. It moves one line and removes one.
alternatives_rejected:
  - "D1-B (INFERENCE, not built): keeps the watches dead for as long as
    another process owns the name, and still couples alarm delivery to D-Bus
    ownership."
  - "D1-C: the start-up race is only one way to lose the name; with D1 unfixed
    any later loss disables the watches (reproducer on 0ubuntu6, which the
    launcher change does not touch)."
code_risks:
  ownership_lifetime: >-
    checked - the filter cannot be added twice (gsd_idle_monitor_init_dbus is
    guarded by the static dbus_name_id and called once, main.c:481), xsync is
    allocated before the filter is added, nothing dispatches after gtk_main
    returns, monitors are reached only through device_monitors[] which
    on_device_removed clears before the unref. Found in passing, NOT fixed by
    D1: D4 (xsync freed in name_vanished_callback).
  callbacks_cancellation: checked
  threading_reentrancy: not_applicable
  ABI_API_file_list: checked
unknowns:
  - "Which session clients register idle watches over D-Bus (cinnamon-session,
    the screensaver, compiz) - they decide how often D4 is hit."
  - "Power plugin symptom (no idle dim/blank while the filter is gone) is read
    from the code, not measured."
  - "Real hardware not tested."
design_challenger_required: true
design_review_result: APPROVE
architectural_task: true
correct_layer: >-
  The idle monitor owns both the XSync alarms and the filter that delivers
  them; the bug is a lifecycle error inside it (filter lifetime bound to the
  bus name instead of the process). Launch order (D2) is a different
  component's defect that only supplies one trigger.
defensive_workaround_rejected: >-
  Fixing the start order instead (D1-C), or making the cursor plugin not hide
  the pointer (the +unity1 guess, reverted), would hide the symptom for one
  trigger and one plugin while idle watches still die on any name loss.
```

### D2 - the daemon is started twice per session

```yaml
package: unity-settings-daemon
status: REPRODUCED
observed: >-
  0ubuntu6: two instances at every login (12/12): unity-settings-daemon.service
  (wanted by unity-session.target) and app-unity-settings-daemon@autostart.service
  from /etc/xdg/autostart/unity-settings-daemon.desktop (systemd
  xdg-autostart generator). One exits on the taken name; which one survives is
  chance (6/6 today). The autostart copy runs localeexec (region LC_* and
  ibus IM variables), the unit ran the bare binary.
root_cause: >-
  The package ships both launchers and the .desktop has no X-systemd-skip,
  so the generator turns it into a unit (systemd xdg-autostart-service.c
  skips only X-systemd-skip=true or GNOME-only phase entries).
invariant: one daemon per session, started with localeexec's environment.
existing_fix_result: FIXED_LOCAL   # 85d3511; still unfixed in stonking
chosen_approach: >-
  85d3511 (published): unit runs localeexec, .desktop gets X-systemd-skip=true
  and stays for session managers without systemd. Precedent: at-spi2-core,
  gnome-online-accounts, plasma-workspace, xdg-user-dirs ship X-systemd-skip
  on entries that have a user unit; gnome-flashback instead dropped its
  autostart files (1a8f0bde, 2025).
measured: >-
  +unity5: one instance, from the unit, in 12/12 cold logins; +unity4~v1 without
  it: two in 12/12.
unknowns:
  - "Effect of the survivor lottery on localeexec's variables was not
    measured (region unset on target)."
  - "cinnamon-session also reads /etc/xdg/autostart (on +unity3 it warns
    that it cannot parse the broken mount-helper entry), but the instance
    counts - at most 2 on the archive, 1 on +unity5 - show it does not start
    a third copy; why it skips the entries was not traced."
design_challenger_required: false   # packaging: which of two existing launchers runs
```

### D3 - libexecdir broken in the 0ubuntu7 base

```yaml
package: unity-settings-daemon
status: REPRODUCED   # inventory of +unity3: autostart Exec and polkit exec.path point at missing /usr/libexec/...
root_cause: >-
  0ubuntu7's move to debhelper configured libexecdir=/usr/libexec and moved
  the files to /usr/lib/unity-settings-daemon afterwards (debian/rules,
  .install), so every path substituted with libexecdir pointed at nothing.
invariant: the paths compiled into the package match where it installs.
existing_fix_result: FIXED_LOCAL   # b503ffd; stonking still has it
chosen_approach: b503ffd (published) - configure with the directory 0ubuntu6 used.
measured: >-
  For the libexecdir-derived paths (mount-helper autostart Exec, localeexec,
  polkit exec.path) +unity5 matches archive 0ubuntu6; +unity3 had all of them
  pointing at /usr/libexec. The .desktop X-systemd-skip and the unit ExecStart
  differ from 0ubuntu6 by design - they belong to D2.
design_challenger_required: false   # mechanical packaging fix restoring the archive's paths
```

## Design review

Temporary Design Challenger (`.claude/agents/design-challenger.md`), separate
read-only subagent, for D1.

1. **REVISE** (2026-09-27): D1-A is the right design and stays as published
   (root cause and layer supported: the reproducer fails on 0ubuntu6 with a
   single instance, passes on +unity4~v1 which still starts twice; the idle
   monitor owns alarms, filter and xsync). Card fixes asked for and made:
   `ownership_lifetime` had missed D4 (xsync freed in `name_vanished_callback`,
   checked by the owner, recorded as a separate finding); invariant and
   unknowns narrowed accordingly; screensaver-proxy is not a watch user; the
   mutter/gnome-flashback precedent now carries links and its source; D1-B's
   rejection labelled INFERENCE; D2's +unity5 claim was a placeholder (now
   measured); D3's claim limited to libexecdir-derived paths;
   `reproduction_result` spelled out.
2. **APPROVE** (2026-09-27, same reviewer): every REVISE point addressed;
   closing D1 as FIXED_LOCAL with D2 and D3 recorded as already-fixed defects
   of the same version is supported; D4 stays a separate task.

## Outcome

`ALREADY_FIXED` / `FIXED_LOCAL`. The published `+unity4`/`+unity5` changes
stay as they are:

- **D1** (`90f5773`) is the fix for #1: the reproducer fails 3/3 on the
  archive and passes 3/3 on a build with D1 but without the launcher change
  (still starting twice), and on +unity5.
- **D2** (`85d3511`) and **D3** (`b503ffd`) are separate defects that were
  bundled into the same version. D3 restores the archive's paths and so
  revives the archive's double start, which D2 removes; +unity5 starts one
  instance in 12/12 cold logins and matches the archive's libexecdir paths.
  The only program the libexecdir change brought back in a Unity session is
  `unity-fallback-mount-helper`, which the archive runs too; no journal
  errors, no duplicate on media insertion.
- Re-splitting a published version would change nothing that runs: no new
  package change in this task.

Regression test: `tools/repro2.sh` - fail before (0ubuntu6), pass after.

## Other findings (not this task's defects)

- **D4 - idle monitor frees its XSync state when a D-Bus watcher leaves**
  (found by the Design Challenger, checked by the owner in
  `gsd-idle-monitor.c` of +unity5): `name_vanished_callback` does
  `if (xsync) g_slice_free (GsdXSync, xsync);` without resetting the pointer,
  and it runs whenever a D-Bus client that added an IdleMonitor watch
  disappears. `xevent_filter` then reads `xsync->sync_event_base` from freed
  memory on every X event; a second vanishing client frees it again. Present
  since the 2014 import (`f88f984`), so in the archive too; not introduced or
  fixed by +unity4. If the freed chunk is reused, every watch can die
  silently - the same symptom as #1 through a different path. Proposed as a
  separate task with its own reproducer (a client calls AddUserActiveWatch
  over D-Bus, then exits).
- **Correction to 90f5773's commit message and code comment**: they list
  screensaver-proxy among the users of the filter; it only calls
  `gsd_idle_monitor_get_idletime` and registers no watch. Harmless for the
  code; the card's mechanism names only the cursor and power plugins.

- **Automount does not work in the Unity session** (archive and ours): the
  helper needs `SessionIsActive` on `org.gnome.SessionManager`, which
  cinnamon-session lacks; nemo-desktop did not mount either. Proposed as a
  separate task.
- **Stray `.git` file in our u-s-d source packages** `+unity2`..`+unity5`
  (`gitdir: /home/claude/unity-distro/packages/unity-settings-daemon/.git/worktrees/usd`,
  from building in a worktree); `+unity1` and the test build are clean. The
  `+unity4` source otherwise equals commit `40ed659` (`diff -r`, plus
  dpkg-source 1.0 ignoring the deletion of
  `plugins/rfkill/61-gnome-settings-daemon-rfkill.rules`). No u-s-d source
  package is in aptly (binaries only).
- **Base version policy**: our `+unityN` sits on `0ubuntu7`, which is not the
  resolute archive version (`0ubuntu6`). Version ordering is safe
  (`0ubuntu7+unityN > 0ubuntu6`), but CLAUDE.md asks for the exact
  target-series base; carrying 0ubuntu7's changes is a decision for May.

## Tools

`tools/repro2.sh` (regression test), `tools/cursor-boots.sh` +
`tools/cursor-loop.sh` (cold logins), `tools/autostart-inventory.sh`,
`tools/usd-debug-wrapper.sh` + `-install.sh`, `tools/steal-idle.py`,
`tools/evinject.py`; `tools/repro1.sh` kept for the invalid runs above.
