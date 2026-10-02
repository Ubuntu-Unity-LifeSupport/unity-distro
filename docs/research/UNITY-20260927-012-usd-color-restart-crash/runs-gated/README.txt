Key runs on the gated +unity7 build (build-gated/, chroot 20260929T201245Z) on target-desktop, 2026-10-02,
dpkg-installed with dbgsym, drop-in tools/zz-u012-perturb.conf active (GLIBC_TUNABLES perturb=165, tcache_count=0).
u-s-d deb sha256 44a92fc4321f...

- 01-power-regress.txt: tools/usd-power-regress.sh, session callbacks 2/0/2 as in runs/13.
- 02-color-uaf.txt: tools/usd-color-uaf.sh, STOP-CALLED, process alive, 0 journal lines, no crash file; as runs/14.
- 03-namevanish.txt: tools/usd-uaf-namevanish.sh (root, systemd-run), STOP-CALLED, AFTER-CONTINUE, no callback, 0 crash reports; as runs/15.

Between 02 and 03 the guest was rebooted; the reboot hit a VirtualBox Guru Meditation (host side, guest journal ends at
shutdown), the VM was powered off and started, and 03 ran on the fresh boot.
