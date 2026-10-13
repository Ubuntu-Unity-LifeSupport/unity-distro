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

## Confirmation on a clean snapshot (2026-10-08 06:15-06:34Z)

The checks above ran over ssh. The vbox MCP server was unreachable at the
time, so the machine could not be rolled back first. Once vbox was
reachable again, the coordinator asked for the users' path to be repeated
on a clean machine.

1. **Restore.** `target-desktop` was shut down cleanly and restored to
   `Clean-updated-2026-09-23`, after `diagnose_vm` found VBoxSVC idle. The
   restore was confirmed from inside the guest: a fresh boot at 09:16:30
   (+03), no `~/.dirty`, `unity-settings-daemon 0ubuntu6` from the archive,
   no source of ours, no `gnome.is_vm`.
2. **Repository, as a user.** We set `~/.dirty`, then followed
   `repo/README.md`, "Client setup": the key copied with scp to
   `/etc/apt/keyrings/unity-distro.asc` (sha256 `e9109214...`), and
   `/etc/apt/sources.list.d/unity-distro.sources`. After `apt-get update`
   the candidate was `+unity11` from `192.168.56.10:8080`
   (`runs/clean-snapshot/01-repo-added.txt`).
3. **`apt-get full-upgrade`.** It ended with rc 0. Our stack came in,
   including `unity-settings-daemon`, `-schemas` and
   `libunity-settings-daemon1` `+unity11` and cinnamon-session
   `6.4.2-1+unity3`, together with archive updates and kernel 7.0.0-38
   (`runs/clean-snapshot/02-full-upgrade.txt`).
4. **One natural boot** into the users' session, on kernel 7.0.0-38
   (`runs/clean-snapshot/03-natural-boot.txt`, checked by
   `tools/natural-boot-check.sh`):
   - all three u-s-d packages are at `+unity11`;
   - the three `.deb` files apt fetched have sha256 `21a64980...`,
     `6127a636...` and `6401c109...`, equal to `build-gate/`;
   - `dpkg -V` is clean;
   - `org.gnome.SettingsDaemon.Power` is owned;
   - `unity-settings-daemon.service` is active with `NRestarts=0`;
   - `sleep-inactive-ac-timeout=0` (battery 1200), from the override;
   - no `gnome.is_vm`.
   - The `(deleted)` maps of the u-s-d process are SysV and pulseaudio
     shared memory, not replaced files.
   - One crash report exists. It belongs to another package and was
     written at 09:18:41, during the first boot after the restore,
     before our repository was added. It is not u-s-d. Its name is
     withheld here and was reported to the coordinator.

This confirms the result above on a clean snapshot. `target-desktop` now
runs the published stack from our repository, with `~/.dirty` present.
