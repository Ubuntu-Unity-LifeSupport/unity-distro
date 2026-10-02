# UNITY-20260928-022: target verification

Published 2026-10-02 (about 15:40Z): `./resolute` switched to snapshot
`unity-resolute-20260928-022` (= `unity-resolute-20260927-012` + 8 records)
by `scripts/publish_aptly.py --gate gate/release-gate.json` (rc 0; write-once
publish record written), after the coordinator's check and May's direct
confirmation.

On `target-desktop`, through the normal repository path, without the test
drop-in:

- `apt-get update`; candidate `15.04.1+21.10.20220802-0ubuntu7+unity9` from
  `http://192.168.56.10:8080 resolute/main`; `apt-get install --reinstall` of
  unity-settings-daemon, libunity-settings-daemon1, unity-settings-daemon-schemas
  from the repository: sha256 in `/var/cache/apt/archives` equal the gate's
  target-test debs (`c56cad4b...`, `57e86ee9...`, `7b4ad0e7...`); `dpkg -V`
  clean.
- Drop-in `zz-u012-perturb.conf` removed; the running u-s-d has no
  GLIBC_TUNABLES and no replaced file mapped (`runs-published/00-state.txt`).
- What this task fixed, on the published binaries without the drop-in:
  - `power-dbus-checks.sh`: stopped plugin answers "The power plugin is not
    running" for Get and Screen.GetPercentage; inhibitors back after the quick
    toggles; daemon alive (`runs-published/01`).
  - `keyboard-toggle-race.sh`: "No keyboard backlight" 353 times, every call
    answered, same pid, NRestarts 0, 0 crash files (`runs-published/02`).
- Boots: of two boots of the published +unity9, one session had no owner of
  `org.gnome.SettingsDaemon.Power` (see "After publication" in README.md);
  `systemctl --user restart`: owned 3/3.

**Limitation:** Power registration race (pre-existing since archive) ->
UNITY-20261002-002. A `stop()` of the power plugin before the session-bus
result arrives leaves Power unregistered until the daemon restarts; the code
is in the archive's 0ubuntu6 and in +unity7, reproduced on both +unity7 and
+unity9 (`runs-race/`). Not introduced by this task's change; fixed forward in
UNITY-20261002-002 (+unity10).

Left on target: u-s-d `+unity9` from the repository with its two dbgsym
packages from the gated build, valgrind, the test scripts in `~`, `~/.dirty`.

target_verified: true
