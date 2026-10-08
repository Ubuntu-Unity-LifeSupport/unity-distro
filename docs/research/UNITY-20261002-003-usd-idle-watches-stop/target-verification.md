# UNITY-20261002-003 (with UNITY-20261002-011): target verification

Published 2026-10-08 03:05Z: `./resolute` switched to snapshot
`unity-resolute-20261002-003-r2` (= `unity-resolute-20261002-002` + 8 records
of the gate rebuild `build-gate/`) by `scripts/publish_aptly.py --gate
gate/release-gate.json` (gate `cf302412`, rc 0, write-once publish record
written), after the coordinator's check and May's direct confirmation. A
first attempt with the earlier gate `68960b49` was refused by
`publish_aptly.py` before the switch (the card had been committed after that
gate); the gate was regenerated, re-checked by C and confirmed by May again.

On `target-desktop` (vbox MCP unavailable; checks over ssh), the users'
environment - published cinnamon-session 6.4.2-1+unity3, no `gnome.is_vm`:

- `apt-get update`: candidate `15.04.1+21.10.20220802-0ubuntu7+unity11` from
  our repository; the repository's `unity-settings-daemon` SHA256 is
  `21a64980...` = `build-gate/`.
- `apt-get install --reinstall` was refused ("cannot be downloaded"): the
  installed packages were the tested build `build/` of the same version with
  other container bytes. So the three debs were taken from the repository
  with `apt-get download` and installed with `dpkg -i`: sha256 `21a64980...`,
  `6401c109...`, `6127a636...` = `build-gate/`; `dpkg -V` clean
  (`runs/published/00-upgrade.txt`).
- Natural boot afterwards (`runs/published/01-natural-boot.txt`): u-s-d
  +unity11 running, no replaced mapping, `org.gnome.SettingsDaemon.Power`
  owned, NRestarts 0, 0 crash files, `dpkg -V` clean,
  `sleep-inactive-ac-timeout=0` (battery 1200) from the override.

Lesson (C, 2026-10-08): create the release gate after the last edit of the
card, or regenerate it (and have it re-checked) after any later edit; build
for the gate in the worktree of the task that carries the publication.

Left on target: u-s-d +unity11 from the repository with the two dbgsym
packages of the tested build, test scripts and debs in `~`, `~/.dirty`.

target_verified: true
