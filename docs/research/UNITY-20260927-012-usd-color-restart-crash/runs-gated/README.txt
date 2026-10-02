Key runs on the gated +unity7 build (build-gated/, chroot 20260929T201245Z) on target-desktop, 2026-10-02,
dpkg-installed with dbgsym, drop-in tools/zz-u012-perturb.conf active (GLIBC_TUNABLES perturb=165, tcache_count=0).

Installed on target (sha256 measured on target in ~/u7g/, equal to build-gated/; dpkg-query: install ok installed,
version 15.04.1+21.10.20220802-0ubuntu7+unity7):
  44a92fc4321f5e5b776b749ab4b2da5fdd0f40cca8720581b9596871ddf0d926  unity-settings-daemon_15.04.1+21.10.20220802-0ubuntu7+unity7_amd64.deb
  ebcf1dee1dda302944572f9f15e3f44c4df6da084bfc3a2600e38e42b0bb1adf  libunity-settings-daemon1_15.04.1+21.10.20220802-0ubuntu7+unity7_amd64.deb
  49aeae3561e8cdd087a21a1e93e33a3a1e292255fa3038a243c4fdbebcd1a484  unity-settings-daemon-schemas_15.04.1+21.10.20220802-0ubuntu7+unity7_all.deb
  6eeba6b940a8e59f25002bede0fe9b6a4aa801507f10a84d608e819a9939eb99  libunity-settings-daemon1-dbgsym_15.04.1+21.10.20220802-0ubuntu7+unity7_amd64.ddeb
  ccf338a0c02663a53371cacf7449d8f8cc60ff97c1ba8de8adda4bf0d95905d7  unity-settings-daemon-dbgsym_15.04.1+21.10.20220802-0ubuntu7+unity7_amd64.ddeb

UNITY-20260927-012:
- 01-power-regress.txt: tools/usd-power-regress.sh, session callbacks 2/0/2 as in runs/13.
- 02-color-uaf.txt: tools/usd-color-uaf.sh, STOP-CALLED, process alive, 0 journal lines, no crash file; as runs/14.
- 03-namevanish.txt: tools/usd-uaf-namevanish.sh (root, systemd-run), STOP-CALLED, AFTER-CONTINUE, no callback, 0 crash reports; as runs/15.

Between 02 and 03 the guest was rebooted; the reboot hit a VirtualBox Guru Meditation (host side, guest journal ends at
shutdown), the VM was powered off and started, and 03 ran on the fresh boot.

UNITY-20260927-052 (its fix 09f45d9 is in +unity7; regression tests from its card's tools/):
- 04-052-two-clients.txt: two-clients.sh x3, u-s-d SURVIVED each time (same pid), no double free in the journal.
- 05-052-valgrind-input.log: INPUT=1 usd-valgrind.sh (valgrind 1:3.26.0-0ubuntu1, installed on target with apt for
  this run), real input after each departure: ERROR SUMMARY 0 errors from 0 contexts.
