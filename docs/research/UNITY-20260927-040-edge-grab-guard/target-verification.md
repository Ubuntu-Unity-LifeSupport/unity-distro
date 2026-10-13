# UNITY-20260927-040 target verification (after publication)

Published 2026-09-29 18:40:26Z: `./resolute` switched to snapshot
`unity-resolute-20260927-040` by `scripts/publish_aptly.py --gate` (rc 0,
record `~/coordinator/publish-records/UNITY-20260927-040.json`), after the
coordinator's answer, B's window (`runs/peer-notice.txt`) and May's direct
confirmation.

target-desktop (`runs/target-upgrade.txt`):

- `apt-get update` from our repository: no errors; InRelease dated
  18:40:25Z; apt's candidate for unity and libunity-core-6.0-9 is
  `7.7.1+26.04.20260306-0ubuntu3+unity12` from 192.168.56.10.
- unity, libunity-core-6.0-9, unity-schemas, -services, -uwidgets
  reinstalled from the repository (they had been installed from the gated
  debs for the tests): all `+unity12`; `libunityshell.so` sha256
  `9266969d...`, the same as in the tested and gated builds.
- After a reboot (boot 21:42 EEST): no deleted library mapped in compiz; the
  regression, title drag in expo, 0/5 stuck; replay of the first stuck case
  0 active and 0 frozen grabs (`runs/pub`).

Target left afterwards: published unity `+unity12` and lightdm `+unity2`,
workspaces 1x1, test tools and results removed, rebooted (boot 21:49 EEST);
`~/.dirty` present; the two UNITY-20260927-047 capture files stay in `~`.
