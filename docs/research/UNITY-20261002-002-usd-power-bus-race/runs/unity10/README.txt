Target test of the gated +unity10 build (build/, chroot 20260929T201245Z) on target-desktop, 2026-10-02.
Installed with dpkg from ~/u10/ over the published +unity9 (runs/unity10/00-install.txt); the sha256 of the files in ~/u10/
equal build/ (checked by A and by the Verifier on target). tested_build: this_build.

Installed:
  525413cff756b9bbbe2f0384dcf4a4ba057b9deb5c878873a96c5a219f60f786  unity-settings-daemon_15.04.1+21.10.20220802-0ubuntu7+unity10_amd64.deb
  37115e246466ddd548af6d0a942c6f6f9830e201acdc963d2bb03dc99aa78e38  libunity-settings-daemon1_15.04.1+21.10.20220802-0ubuntu7+unity10_amd64.deb
  8f3192d411967342f312dc0fc21ca6eb66eb79019d7391332e4db58b8ec87742  unity-settings-daemon-schemas_15.04.1+21.10.20220802-0ubuntu7+unity10_all.deb
  b7801718cd32e7665f031b504b3e097b561826bf8215177b83b3c362b9720ed0  unity-settings-daemon-dbgsym_15.04.1+21.10.20220802-0ubuntu7+unity10_amd64.ddeb
  825435e75d5f77d73323f5ffc5476ab5580240b69d7b484dcb732255460d547e  libunity-settings-daemon1-dbgsym_15.04.1+21.10.20220802-0ubuntu7+unity10_amd64.ddeb

Runs on these debs: 01/02 stop-before-bus.sh nostop/stop (PASS: owner kept, Get Icon and Screen.GetPercentage answered);
03 toggle unit disabled; 04 keyboard-toggle-race under valgrind (0 errors, owner before and after); 05 power-dbus-checks;
06 keyboard-toggle-race under systemd; 07 -012 power-regress 2/0/2; 08 -012 color-uaf; 09 -052 two-clients SURVIVED;
runs/toggle-unity10/ 3 boots (owner 3/3); runs/boots-unity10/ 10 natural boots (owner 10/10, 0 stops, 0 crash, NRestarts 0).
Test units removed and target rebooted before the gate: Power owned, no drop-ins, no bpftrace, 0 crash files.
