# UNITY-20260927-012 (with UNITY-20260927-052): target verification

Published 2026-10-02 15:15Z: `./resolute` switched to snapshot
`unity-resolute-20260927-012` (= `unity-resolute-20260927-027` + 8 records) by
`scripts/publish_aptly.py --gate gate/release-gate.json` (rc 0; write-once
publish record written), after the coordinator's check and May's direct
confirmation.

On `target-desktop`, through the normal repository path:

- `apt-get update`: our repository's InRelease and Packages fetched;
  `apt-cache policy unity-settings-daemon` - candidate
  `15.04.1+21.10.20220802-0ubuntu7+unity7` from `http://192.168.56.10:8080 resolute/main`.
- `apt-get install --reinstall unity-settings-daemon libunity-settings-daemon1
  unity-settings-daemon-schemas`: the three debs were downloaded from the
  repository; their sha256 in `/var/cache/apt/archives` equal the gated
  build's and the target-test record's (`44a92fc4...`, `ebcf1dee...`,
  `49aeae35...`); `dpkg -V` clean.
- The test drop-in `zz-u012-perturb.conf` removed, then a reboot: u-s-d
  `+unity7` running (pid 2244) without GLIBC_TUNABLES, no `(deleted)`
  mapping, NRestarts 0, owner of `org.gnome.SettingsDaemon.Power` and
  `org.gnome.Mutter.IdleMonitor`, no u-s-d crash file.
- Quick regressions on the published binaries: `usd-power-regress.sh`
  session callbacks 2 / 0 / 2 (not doubled); UNITY-20260927-052's
  `two-clients.sh`: SURVIVED (same pid).

Left on target: u-s-d `+unity7` from the repository (with the two dbgsym
packages from the gated build), valgrind (installed for the -052
regression), the test scripts in `~`, `~/.dirty`.

target_verified: true
