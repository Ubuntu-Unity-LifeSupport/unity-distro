Key runs on the gated +unity9 build (build-gated/, chroot 20260929T201245Z) on target-desktop, 2026-10-02,
dpkg-installed with dbgsym over the published +unity7, drop-in tools/zz-u012-perturb.conf active (GLIBC_TUNABLES
perturb=165, tcache_count=0), after a reboot: u-s-d pid 2200, no replaced file mapped.

Installed on target (sha256 measured on target in ~/u9g/, equal to build-gated/ and to build-unity9/; dpkg-query:
version 15.04.1+21.10.20220802-0ubuntu7+unity9):
  c56cad4bc58849d2e2d9fba2cae905333558b8679a645a6c4f524d5410d92a42  unity-settings-daemon_15.04.1+21.10.20220802-0ubuntu7+unity9_amd64.deb
  57e86ee97ee0407850cfcfee0a4aff0f014bfb47392683fc1c6d0de7962099a4  libunity-settings-daemon1_15.04.1+21.10.20220802-0ubuntu7+unity9_amd64.deb
  7b4ad0e7a6d2b5647886a6d812c7a80c34ef92493ab99a53a43e0667186f590d  unity-settings-daemon-schemas_15.04.1+21.10.20220802-0ubuntu7+unity9_all.deb
  bb2295de1b1073fb91e229b4cc9570971757c3f55e9ee915102c5f2db19a540a  libunity-settings-daemon1-dbgsym_15.04.1+21.10.20220802-0ubuntu7+unity9_amd64.ddeb
  a5b06ef4a2081b26686122f77144f406a981d0f9017b14d3b2f564b430667c9b  unity-settings-daemon-dbgsym_15.04.1+21.10.20220802-0ubuntu7+unity9_amd64.ddeb

- 01-power-dbus-checks.txt: tools/power-dbus-checks.sh - stopped: "The power plugin is not running" in ~0.016 s for
  Get and Screen.GetPercentage; after quick on/off x3 and on, the lid-switch block and the sleep delay inhibitor are
  back; daemon alive, 0 journal lines; as runs/06 (+unity8) and runs/11.
- 02-keyboard-toggle-race.txt: tools/keyboard-toggle-race.sh (needs tools/kbdrace.py in /tmp; the first attempt,
  without it, made no calls and is not kept) - Keyboard.StepUp: "No keyboard backlight" 390 times, every call
  answered; Screen.GetPercentage likewise; same pid, NRestarts 0, 0 crash files; as runs/10.
- 03-quick-toggle.txt: tools/quick-toggle.sh - the trace shows the proxy callbacks of a start still arriving after
  the next STOP, as in runs/03 (+unity7): the dprintfs fire at the callbacks' entry, before +unity9's early return
  on a cancelled start, so the trace shows timing only; the effect is checked in 01 (inhibitors back). Alive, 0 crash.
- 04-finalized-unique-name.txt: tools/finalized-unique-name.sh - after a forced finalize, method and property Get by
  u-s-d's unique name answer "object does not exist", no crash; as runs/08.
