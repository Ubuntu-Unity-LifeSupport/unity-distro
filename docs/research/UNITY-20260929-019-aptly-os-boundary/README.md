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

**May's decision (via C, 2026-09-29): option 2.** The signing key moves out
of `claude`'s reach. Root on builder stays for everything else.

## Design, round 2 (after the Design Challenger's REVISE; no system changed)

### What it guarantees, and what it does not

Everything that runs as `claude`, the Verifier included, can be forged by
root on builder. That covers gates, manifests, Verifier records and ACKs.
Checks on material that builder sends can therefore prove only that the
request is consistent. They cannot prove provenance: a trojan `.deb`,
listed with its real sha256, passes them.

So the boundary is a person. **Every live publication needs May's
confirmation on a channel agents cannot drive: the signer's own console.**

What May approves there is a diff that the signer computed itself from the
indexes. For each added, removed or changed record it shows:

- package, version and architecture;
- sha256 and size;
- whether the `.deb` has maintainer scripts;
- the previous version, if one existed.

It never shows text that builder wrote. The signer's automatic checks
(below) are a safety net under May's decision; they do not replace it.

What is protected: anything that installs from the repository on machines
the agents do not control, meaning May's own machines, OEM installs May
runs, and any future mirror.

What is not protected: `target-desktop`, `target-desktop-2` and `oem-test`,
including their snapshots. Agents have root there over ssh and through the
MCP console, and can change their keyrings or install packages directly.
They stay test machines.

### The signer and its reach

`aptly-signer` is a small Linux VM on May's host. The vbox MCP server must
treat it like builder-server (`never_allowed`), and additionally:

- no MCP tool that takes a medium or a path accepts the signer's disk or
  its exports (`clone_linked`, `create_vm`, `attach_iso`, `list_media`);
- the MCP configuration and May's backup location are not writable by
  agents;
- the signer runs no sshd;
- its only listener on the host-only network is the signing API, which is
  acceptable because nothing is signed without May;
- NAT is off, and May turns it on only for the signer's own updates;
- maintenance: autostart, updates, and a VM or key backup that May keeps
  offline.

### Two-phase signing, so aptly's database lock is never held while waiting

Every aptly command holds a database lock, reads included. If the signing
step waited inside the publish switch for May, all agent reads,
`apt_view.py` and taskctl's PUBLISHED gate would stall. So:

1. **Proposal.** `publish_aptly.py` makes a rehearsal publication of the
   gated snapshot, with signing off, on the rehearsal root. Its
   `Packages`/`Sources` are the ones the live switch will produce. It sends
   that index set with the task ID to the signer, then ends.
2. **Approval.** May reviews the signer-computed diff on the signer console
   and approves or rejects it. The signer stores approved index sets by
   their checksums.
3. **Live switch.** `publish_aptly.py` runs the switch. aptly calls the
   gpg stand-in, the stand-in sends the Release to the signer, and the
   signer signs at once if the checksums of every index file the Release
   lists match an approved set. The Release's Date changes on every run,
   so the Release file itself is not what gets approved.

### Automatic checks, the safety net under May's approval

Before it signs, the signer checks all of these:

- The Release lists only files the signer checked:
  - every Packages and Sources variant (plain, `.gz`, `.xz`, `.bz2`,
    `by-hash`) for every component and architecture;
  - each compressed variant decompresses to the same content;
  - a Release listing anything else is refused.
- The distribution is `resolute`, the component `main`, the prefix `.`.
- `Valid-Until` is short (a few days). The signer re-signs on a cadence
  only for index sets it has already approved, so a replayed old
  `InRelease` expires.
- The same Release may be signed twice, once detached and once clearsigned,
  because aptly asks for both. The signer's "last live" state advances
  only when builder reports the switch as done, and the signer can verify
  that by fetching `InRelease` from :8080.

Removals and replacements are shown to May as such and need the same
approval. This covers the -021 replacement and -047-style rollback L5a.
Expect hours of latency.

### The gpg stand-in (to be proven in rehearsal)

- aptly uses a gpg provider that execs a `gpg` binary (`gpg` or `gpg2`, not
  `internal`). The stand-in answers `--version` and implements aptly's
  detached-sign and clearsign calls with their `-u`, keyring, passphrase and
  `--batch` arguments. The exact arguments are to be taken from aptly's
  documentation or source; the guard refuses even the help of the
  publishing command, so the Design Challenger could not read them here.
- Rehearsal must prove two things: aptly signs temporary files before it
  renames them into place, and a refusal from the signer leaves the old
  `InRelease`/`Release.gpg` and indexes live. That is what "no unsigned
  window" rests on.

### Rotation

The current key was readable by every agent and by root, so the threat
model treats it as copied. It is retired:

1. The signer generates a new key, which never leaves it. May keeps an
   offline backup of the new key, and only a revocation certificate of the
   old one. A backup of the old secret key is pointless.
2. May publishes the new key's fingerprint out of band, not only in the
   repository, which agents can write.
3. The targets first get a keyring file with both keys. Then the signer
   switches to the new key. Then the keyring holds the new key only.
4. The old key is removed from every keyring that trusted it: that is what
   stops old signatures from being trusted. It is removed from `claude`'s
   `~/.gnupg` last, after the first live publication with the new key.
   Publishing the revocation is mostly cosmetic for apt.
5. `oem-test` live sessions pin the fingerprint when they fetch the key,
   instead of trusting whatever builder serves.

### Design Challenger round 2 (REVISE): changes taken

1. **An approval is used once and is bound to its base.** Each approval
   records the signer's last-live state it was diffed against.
   - It is valid only while that state is still last-live.
   - It is consumed when its set goes live.
   - Moving last-live revokes every other outstanding approval.
   - The re-sign cadence covers only the current last-live set.
   So a switch back to an older approved set (for example the one before the
   -021 replacement) needs a new approval from May.
2. **The signer writes Valid-Until.** aptly is not known to emit it. This
   is to be confirmed from its documentation or source, since the guard
   refuses the help text. So:
   - The signer returns a rewritten `Release` (new Date and Valid-Until)
     with `InRelease` and `Release.gpg`.
   - The stand-in writes all three over aptly's temporary files before
     aptly renames them into place. Rehearsal must prove it.
   - The cadence refresh pulls all three files from the signer. A builder
     that withholds a refresh makes the repository expire, which is
     visible.
3. **Contents files.** aptly also lists `Contents-*`, and possibly i18n
   files. The signer checks them the same way (decompressed content, every
   variant), or they are not published (`skipContentsPublishing`). The
   choice is made during implementation.
4. **Approvals match on decompressed content**, and every compressed
   variant must decompress to it. The rehearsal root's `.gz`/`.xz` bytes
   need not equal the live ones.
5. **Maintainer-script flag.** For each added `.deb`, the signer fetches it
   from :8080, checks its sha256 against the Packages entry, and reads the
   control archive. Builder's word is never used for this.
6. **Last-live confirmation.** The signer checks that the `InRelease`
   served on :8080 carries its own signature over exactly the Release it
   signed, not just that a file is there.

### Design Challenger round 3: APPROVE

Non-blocking findings, taken:

- **Valid-Until is 3 days.** A set that was signed but held back by builder
  can be served at most until then. This window is accepted.
- **Gate.** If a rehearsal proof fails, the design goes back to the Design
  Challenger instead of being patched during implementation. The two
  proofs are "aptly signs temporary files before renaming them" and "the
  stand-in can overwrite Release, InRelease and Release.gpg before that
  rename".
- **Contents: `skipContentsPublishing`, decided now.** The signer refuses
  any Release that lists `Contents-*`.
- **Expiry is reported as such.** If the cadence refresh stops, the
  repository expires for every user, the test targets included.
  `publish_aptly.py` and taskctl's PUBLISHED gate report this as "the
  repository has expired (Valid-Until passed)", not as a generic failure.

### What changes for existing tools

| Tool or operation | Effect |
|---|---|
| `publish_aptly.py` | Gains the proposal step and a clear failure with a timeout when the signer refuses or is down. |
| taskctl, `apt_view.py`, backups | Unchanged. |
| Rehearsal | Unchanged, plus a test-key mode on the signer for end-to-end tests. |
| Live operations and rollback | Go through May's approval. |

### Order of work, each step after May confirms

1. May creates `aptly-signer`, adds it to the MCP's never-allowed list with
   the medium and path restrictions, and disables sshd on it.
2. B writes the signer service, the stand-in and their tests in the
   repository. The Design Challenger and the Verifier review them.
3. May installs the service and generates the new key on the signer.
4. End-to-end run with the test key on the rehearsal root. Then a first
   live publication with the new key, approved by May on the console.
5. Rotation on the targets: both keys, then the new key only. The old key
   is removed from builder last.

