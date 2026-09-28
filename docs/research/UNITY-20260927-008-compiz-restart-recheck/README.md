# UNITY-20260927-008: compiz restart fixes (unity +unity6..8) re-checked on a clean snapshot

Legacy A-L04. `research/compiz-restart/` (2026-09-24) found four things a
compiz restart got wrong on our stack and fixed them in unity `+unity6..8`,
compiz `+unity2` and gtk-nocsd `+unity2`. That work was done on a target that
had been upgraded step by step. This record repeats its scenarios on a clean
snapshot, before and after the normal update from our aptly. Agent A, target
`target-desktop`, 2026-09-28. No code change.

## Method

1. `target-desktop` powered off from inside, restored to
   `Clean-updated-2026-09-23` (after a pause), booted. Checked inside: no
   `~/.dirty`, boot time new, stock packages (unity `0ubuntu3`, compiz-core
   `0ubuntu3`, gtk-nocsd `3+0~20260321+0b77e1b-1`, cinnamon-session `6.4.2-1`),
   no aptly source. Only `xdotool` added (from the Ubuntu archive) for the
   scenarios.
2. **Before**: `tools/run-all.sh` on the stock packages
   (`runs/before/log.txt`, screenshots `runs/before/*.png`).
3. Our aptly source and key added (the same `unity-distro.list` and
   `/etc/apt/keyrings/unity-distro.asc` as before the rollback), `apt-get
   update && apt-get full-upgrade`, reboot: unity `+unity11`, compiz `+unity2`,
   gtk-nocsd `4.8-1+unity3`, nux `0ubuntu15+unity2`, cinnamon-session
   `+unity3` and the rest of our packages (`runs/after/packages.txt`, 60
   packages with `+unity`).
4. **After**: the same `tools/run-all.sh` (`runs/after/`), then
   `tools/logout-cycles.sh` (two logouts, root through systemd-run, as in
   research/compiz-restart).

`tools/run-all.sh`, after compiz manages windows and 30 s of settling: 2x2
workspaces through the key the Settings checkbox writes, one xterm per
viewport and a gnome-terminal on (1280,0) (`tools/vpsetup.sh`, titles pinned
so windows are found by name), the lower-row xterms moved to y 1032; then five
`killall -1 compiz` 30 s apart with all positions after each
(`tools/vpdump.sh`) and compiz's pid; a screenshot of each viewport; then
`systemctl --user restart unity7.service`, positions and screenshots; then
gtk-nocsd's crash handler with a GTK3 window that segfaults
(`tools/nocsdcrash.sh`, from research/compiz-restart). After each step:
segfault / general protection / core dump / `g_hash_table` lines in the
journal, and `/var/crash`.

Two before-runs were lost to my tools, kept for the record: the xterms'
shell retitled them (`runs/00-...`), then `vpdump.sh` read only
`_NET_WM_NAME` (`runs/00b-...`); a third hung in `xwininfo` because the run
started before compiz managed windows (not kept). All three already showed
compiz crashing on every SIGHUP. The tools were fixed as described.

## Result

| Check | Before (stock, clean snapshot) | After (our aptly) | Fixed by |
|---|---|---|---|
| compiz on 5x SIGHUP | new pid every time, one restart with no compiz 30 s later; `/var/crash/_usr_bin_compiz.1000.crash`; 80 journal hits | same pid 2781 all five times; 0 journal hits; `/var/crash` empty | unity `+unity6` |
| lower-row windows | 1032 -> 1000 -> 1000 -> 968 -> 936 -> 904 (-32 px per restart once compiz came back); 872 after the unity7 restart | 1032 after every SIGHUP and after the unity7 restart; every window to the pixel | compiz `+unity2` |
| unfocused window after a restart | xterm vp-1280-0 bare (no title bar, buttons or frame) after 5 SIGHUP and after the unity7 restart (`runs/before/after-*-vp-1280-0.png`) | title bar and buttons (`runs/after/after-*-vp-1280-0.png`) | unity `+unity8` |
| `systemctl --user restart unity7.service` | journal 100 hits cumulative | new compiz, positions kept, 0 hits | unity `+unity6` |
| gtk-nocsd crash handler | the handler itself segfaults (`ld-linux-x86-64: segfault at 10 ... in libgtk-nocsd.so.0`), `_usr_lib_x86_64-linux-gnu_ld-linux-x86-64.so.2.1000.crash` | the handler restarts the program (new pid 10569, same argv), no segfault | gtk-nocsd (now 4.8-1+unity3) |
| logout, 2 cycles (after only) | - | compiz gone before the greeter (3 s) both times, 0 journal hits, `/var/crash` empty (`runs/after/logout-cycles.txt`) | - |

On the clean snapshot the stock light-locker also crashed at every login
(`_usr_bin_light-locker.1000.crash`, LP #2038808, fixed in our
light-locker `+unity2`); not part of this task, and absent after the update.

One crash report in both runs is my test's own: `timeout` from
rust-coreutils (`/usr/lib/cargo/bin/coreutils/timeout`, `Signal: 11`,
`ProcCmdline: timeout 20 python3 /tmp/segv.py first-run`) re-raises its
child's SIGSEGV on itself and apport records that as a crash. It wraps the
test program only; nothing in the session runs under `timeout`. Not
investigated further (whether GNU timeout disables core dumps before
re-raising and uutils does not is a question for rust-coreutils).

## Evidence card

```yaml
task_id: UNITY-20260927-008
package: unity (with compiz, gtk-nocsd)
target_series: resolute
issue: legacy A-L04 - compiz teardown and decorations after a compiz restart, unity +unity6..8, re-checked on a clean snapshot
status: REPRODUCED   # all four on the stock packages of Clean-updated-2026-09-23
issue_search_result: FOUND   # research/compiz-restart, release notes' "windows land on the first workspace"
source_version: unity 7.7.1+26.04.20260306-0ubuntu3+unity11, compiz 1:0.9.14.2+25.10.20250930-0ubuntu3+unity2, gtk-nocsd 4.8-1+unity3 (published)
binary_version: same, on target after apt full-upgrade from our aptly
source_commit: UNKNOWN   # not re-read in this task; the fixes are those of research/compiz-restart
observed: >-
  Stock: compiz crashes on every SIGHUP and on a unity7 restart, lower-row
  windows move up 32 px per restart, an unfocused window loses its
  decorations, gtk-nocsd's crash handler segfaults. Our aptly: none of these;
  logout clean.
expected: a compiz restart keeps compiz alive (SIGHUP) or restarts it cleanly, keeps every window where it was, decorated
reproduction: tools/run-all.sh (and tools/logout-cycles.sh) on target
evidence: runs/before/, runs/after/; target journal 2026-09-28 15:19-16:40 UTC
root_cause: see research/compiz-restart (unchanged)
invariant: see research/compiz-restart
existing_fix_result: FIXED_LOCAL
existing_fix_evidence: before/after on one clean snapshot, table above
chosen_approach: NONE - no change; the published fixes hold
code_risks:
  ownership_lifetime: not_applicable
  callbacks_cancellation: not_applicable
  threading_reentrancy: not_applicable
  ABI_API_file_list: not_applicable - no change
unknowns:
  - "Multi-monitor and `unity --replace` (not covered, as in 2026-09)."
  - "The layer of the +unity6..8 fixes was not re-reviewed here; this task
    checks that they hold on a clean system."
  - "rust-coreutils timeout re-raising SIGSEGV with a core dump (test
    artefact above)."
design_challenger_required: false   # no code change; revalidation only
architectural_task: false
design_review_result: NOT_REQUIRED
```

## Outcome

`ALREADY_FIXED` / `FIXED_LOCAL`: on a clean `Clean-updated-2026-09-23`
snapshot all four restart defects reproduce with the stock packages, and none
does after the normal update from our aptly. Target left as target = aptly
(full-upgrade), `~/.dirty` present; `xdotool` stays installed.
