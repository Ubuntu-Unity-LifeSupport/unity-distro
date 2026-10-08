Target test of the gated +unity11 build (build/, chroot 20260929T201245Z) on target-desktop, 2026-10-03.
Installed with dpkg from ~/u11/ (sha256 equal to build/, checked by the Verifier on target); tested_build: this_build.

Installed:
  b4cba78fb62b24e56c36c6bb9a4a184fb73fc4bbeb25cbb7edda3092495458d3  unity-settings-daemon_15.04.1+21.10.20220802-0ubuntu7+unity11_amd64.deb
  8afcf5adee4c7ed203b90ac7a0c479c799a2445e8e2023d42c85b94265ee3117  libunity-settings-daemon1_15.04.1+21.10.20220802-0ubuntu7+unity11_amd64.deb
  5447a543cbc05e9bcbd336780bc9d87a1a902418f25bc9088c89b5e611b01e33  unity-settings-daemon-schemas_15.04.1+21.10.20220802-0ubuntu7+unity11_all.deb

Runs on these debs: 02 after (0 idle callbacks after stop), 03 after with gnome.is_vm=0 (modes, one user-active watch,
0 callbacks), 04 27 min idle on AC with the override (no suspend, no idle callback), 05 regressions of -022/-012/-052/-002.
Test environment also had cinnamon-session +unity4 (F2, not part of this publication) and gnome.is_vm=0 (changed test condition).
Users' environment (gate): 06 one natural boot with the published cinnamon-session (+unity3), no gnome.is_vm, u-s-d +unity11: Power owned, NRestarts 0, 0 crash, dpkg -V clean, override effective.
