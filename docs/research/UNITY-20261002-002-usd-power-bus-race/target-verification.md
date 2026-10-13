# UNITY-20261002-002: target verification

Published 2026-10-02 19:13Z: `./resolute` switched to snapshot
`unity-resolute-20261002-002` (= `unity-resolute-20260927-026` + 8 records)
by `scripts/publish_aptly.py --gate gate/release-gate.json` (rc 0; write-once
publish record written), after the coordinator's check and May's direct
confirmation in agent A's session.

On `target-desktop`, through the normal repository path, with no test
units, drop-ins or tracer (`runs/published/`):

- `apt-get update`: our repository's InRelease and Packages fetched;
  candidate `15.04.1+21.10.20220802-0ubuntu7+unity10` from
  `http://192.168.56.10:8080 resolute/main`.
- `apt-get install --reinstall unity-settings-daemon libunity-settings-daemon1
  unity-settings-daemon-schemas` (the tested build had been installed by
  dpkg): the three debs were downloaded from the repository; their sha256 in
  `/var/cache/apt/archives` equal the gate's target-test debs
  (`525413cf...`, `37115e24...`, `8f3192d4...`); `dpkg -V` clean.
- Two natural boots afterwards (`01-natural-boots.txt`): u-s-d +unity10
  running, no replaced file mapped, `org.gnome.SettingsDaemon.Power` owned
  (`:1.53`, `:1.51`), NRestarts 0, 0 crash files, the power plugin's three
  logind inhibitors held, no GLIBC_TUNABLES, no bpftrace.

Together with the tests on the same debs before publication (card: gdb
stop-before-bus PASS, key toggle in the window 3/3, valgrind race 0 errors,
-022/-012/-052 regressions, 10 natural boots 10/10) this is the fix in
place. The trigger of the one natural occurrence stays UNITY-20261002-009;
the identical gap in the housekeeping plugin is UNITY-20261002-006.

Left on target: u-s-d `+unity10` from the repository with its two dbgsym
packages from the gated build, valgrind, the test scripts of
-012/-052/-022/-002 in `~`, `~/.dirty`.

target_verified: true
