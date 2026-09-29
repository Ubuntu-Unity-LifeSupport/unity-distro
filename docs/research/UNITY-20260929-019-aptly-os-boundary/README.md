# UNITY-20260929-019 - aptly behind an operating-system boundary

Kind: `operation` (users, ownership and sudo on `builder`), SECURITY.
Owner: B. Asked by May on 2026-09-29, after UNITY-20260929-018 was merged as
a partial tightening. The guard stays, but the real limit on publication
should come from permissions, so that a guard bypass cannot publish.

Status: **inventory done; design not started.** One question has to go to
May first, because it decides whether an operating-system boundary is
possible at all (see "Precondition").

## Inventory (2026-09-29 ~20:45Z, read-only)

### The live repository

- `/srv/aptly` (`db`, `pool`, `public`) is owned by `claude:claude`,
  755/775. `~/.aptly.conf` (`rootDir: /srv/aptly`, signing on) is
  `claude:claude` 644.
- The signing key, `29A893E0…C27B152C`, is the only secret key in
  `claude`'s `~/.gnupg` (700).
- nginx (`/etc/nginx/sites-enabled/unity-distro`, workers run as
  `www-data`) serves `root /srv/aptly/public` on `192.168.56.10:8080`. It
  only reads.
- Backups: `~/backups/aptly-*` and `~/backups/repo-*`, owned by `claude`,
  700.

### Callers of aptly

All of them run `aptly` from PATH as `claude`, with `~/.aptly.conf`:

- `scripts/publish_aptly.py`:
  - `snapshot show` and `snapshot search`;
  - `publish switch`, the only publishing command;
  - `publish show`;
  - it writes `~/coordinator/publish-records/` and appends to
    `~/AGENTS-LOG.md`.
- `scripts/apt_view.py`: `snapshot search`/`show` (read).
- `scripts/taskctl.py`: `publish show`, `snapshot search` (read, PUBLISHED
  gate).
- `scripts/build_dependencies.py`: reads the pool, for extra build
  packages.
- Agents, directly, as the process allows:
  - `repo add` and `snapshot create`/`drop` (write, no publish);
  - `repo show/search`, `snapshot list/diff/search` (read);
  - backups by copying `/srv/aptly`.
- `.claude/hooks/command_guard.py`: rehearsal and live allowances for
  `/usr/bin/aptly`.

Every aptly command opens the database with a lock, reads included
(UNITY-20260927-047 "db opens"). So a read also needs write access to
`db`. Reads cannot simply stay with `claude` once `db` belongs to another
user.

### `claude`'s root

`/etc/sudoers.d/99-claude-nopasswd` gives `claude` `(ALL) NOPASSWD: ALL`,
and `claude` is in group `sudo`. From the transcripts, sudo on builder
itself (outside ssh to the targets) is used mainly for:

- `sudo -n unshare --mount --pid --fork … sh -c` into dev chroots under
  `/var/tmp/sbuild-claude` (about 130 calls);
- `rm`/`mv`/`cp`/`tee`/`tar`/`chmod` inside those chroots;
- `chroot` (about 20);
- `gdb -p` / `timeout gdb` attaching to processes;
- `apt-get update/install` on builder;
- `systemctl restart nginx` and nginx site edits;
- `sysctl kernel.core_pattern`, `timedatectl`, `loginctl`, `dbus-monitor`,
  `ip addr`, `journalctl`, `find /`, `du`/`vgs`/`lvs`;
- reading `/etc/sudoers.d`;
- input-event scripts (`~/evseq.py`, `~/evinject.py`, `~/evclick.py`).

## Precondition: a boundary needs `claude` without unrestricted root

Any process with root can run a publishing command as the aptly user,
whatever the ownership:

- `sudo -u <aptly user> aptly …`;
- `sudo unshare … sh -c`;
- `sudo chroot`;
- `sudo tee` to sudoers.

With `NOPASSWD: ALL`, a dedicated user and a single sudo rule for
`publish_aptly.py` limit only well-behaved callers. That is the same thing
the guard does today, so it is not a stronger boundary.

Possible directions, for May to choose from before any design work:

1. **Remove `claude`'s unrestricted root on builder.**
   - Replace it with a short list of exact sudo rules.
   - Move the dev-chroot work to rootless user namespaces (`unshare -r`,
     `mmdebstrap --mode=unshare`), as sbuild already runs.
   - Accept losing, or reviewing one by one, the other root uses above
     (gdb on others' processes, `apt-get`, `sysctl`, nginx changes).
   - This is the strongest option and the largest change to daily work.
2. **Take the signing key off `claude`'s reach.**
   - The Release signing happens in a place `claude`'s root cannot reach:
     a separate machine or VM, or a signing service on May's host that
     signs only what a gated `publish_aptly.py` asks for.
   - `claude` could still write `public/` files, but without a valid
     signature the targets' apt rejects them.
   - Root stays for everything else.
3. **Keep root, add a separate user anyway.**
   - A dedicated aptly user plus sudo rules, with `NOPASSWD: ALL` left in
     place.
   - It protects only against accidents, not against a bypass. It is
     documented as such.

My recommendation is 2. The protected asset is "a signed Release that the
targets trust", and moving only the key keeps the rest of the work as it
is. 1 is the only full boundary on the machine itself, but it costs the
most daily capability. May decides.

Nothing on builder has been changed.
