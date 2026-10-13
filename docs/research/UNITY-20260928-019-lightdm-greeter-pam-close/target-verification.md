# UNITY-20260928-019 target verification (after publication)

Publication: `publish_aptly.py --gate gate/release-gate.json` (gate on
`a/UNITY-20260928-019` `fdab8e3`), after the coordinator's check and May's
direct confirmation; `./resolute` switched to snapshot
`unity-resolute-20260928-019`, record
`~/coordinator/publish-records/UNITY-20260928-019.json` (published_at
2026-09-29T17:06:28Z, aptly_result PASS, post_publish_check PASS).

target-desktop (`runs/15-target-upgrade.txt`), agent A, 2026-09-29:

- The rt's temporary user `utest`, its greeter preselection and the test
  files removed.
- `apt-get update`: no E/W lines; our InRelease `Date: Tue, 29 Sep 2026
  17:06:28 UTC` (the publication).
- `apt-cache policy lightdm`: candidate `1.32.0-6ubuntu4+unity2` from
  `http://192.168.56.10:8080 resolute/main` (the rt had installed the same
  version with `dpkg -i`, so it was reinstalled from the repository with
  `apt-get install --reinstall lightdm liblightdm-gobject-1-0`: fetched
  236 kB from our repository); `apt-get upgrade`: nothing else from this
  publication.
- Installed: lightdm and liblightdm-gobject-1-0 `1.32.0-6ubuntu4+unity2`;
  `/usr/sbin/lightdm` sha256 `815531b0...` = the published pool file's
  (`pool/main/l/lightdm/lightdm_1.32.0-6ubuntu4+unity2_amd64.deb`) = the
  binary verified in runs/05-10.
- Rebooted (boot 2026-09-29 20:08:14 EEST): lightdm active, mike's
  autologin session on seat0, no error-priority lightdm journal lines.

The fix's behaviour on this binary was verified before publication (full
plan on the identical test build, rt 6/6 on the gated build: runs/05-10).
