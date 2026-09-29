# UNITY-20260929-021: aptly-signer implementation (step 2 of UNITY-20260929-019)

SECURITY, tool task, agent A. It implements the design approved in
UNITY-20260929-019: branch `b/UNITY-20260929-019` `60bbd9a`, card
`docs/research/UNITY-20260929-019-aptly-os-boundary/README.md`, Design
Challenger round 4 APPROVE, confirmed by May. This task is its step 2: the
signer service, the gpg stand-in, and their tests, all in this repository.

Out of scope, and done by May by hand:
- creating the signer VM (step 1);
- installing the service and generating the key (step 3);
- the end-to-end run and the live cut-over (step 4);
- the rotation (step 5).

Nothing on builder, no system configuration, no key and no `~/.gnupg` is
changed by this task.

May's invariant: automatic re-signing happens only for exactly the content
May already approved. Every other change needs May's explicit confirmation
on the signer console.

## 1. Facts established before planning

- **aptly and gpg.** aptly 1.6.2-2, gpg 2.4.8 on builder. The option strings
  in `/usr/bin/aptly` (read with `grep -a`; the guard refuses aptly's own
  help and the source package by name) are those of aptly's GnuPG signer:
  `-o`, `--digest-algo`, `--armor`, `--yes`, `--no-auto-check-trustdb`,
  `--no-default-keyring`, `--keyring`, `--secret-keyring`, `--pinentry-mode`,
  `--passphrase`, `--passphrase-file`, `--batch`, `--detach-sign`,
  `--clearsign` and `--status-fd`. As I recall from aptly's source:
  - detached signature:
    `gpg -o <dest> --digest-algo SHA256 --armor --yes [keyring, -u, passphrase and batch options] --detach-sign <src>`;
  - clearsigning:
    `gpg -o <dest> --digest-algo SHA256 --yes [same options] --clearsign <src>`;
  - version detection runs `gpg --version`.

  This is from memory and unverified. The stand-in therefore parses
  options by name and refuses anything it does not know, and the rehearsal
  proofs (section 4) settle the exact calls.
- **Python on the signer.** Python 3.14 standard library: `compression.zstd`,
  `lzma`, `gzip` and `bz2` are all present. The signer can read `.deb`
  control archives and every index compression with no third-party package,
  which matters on a minimal, mostly offline VM.

## 2. Plan

**P1. `signer/signer_core.py`: pure logic, no network, no gpg.** It is what
the refusal tests exercise.
- Parsing. It parses a Release (the field order kept) and an index set (a
  dict of relative path to bytes). It decompresses every variant (plain,
  `.gz`, `.xz`, `.bz2`, and by-hash copies) and refuses a set in which any
  variant decompresses differently, or which contains `Contents-*` or files
  other than Packages/Sources/Release variants of `main`.
- Distribution, component and prefix. They are fixed: `resolute`, `main`,
  `.`.
- `build_release(template, index_set, date)`:
  - the Release the signer publishes, from a fixed field template stored on
    the signer;
  - the index list and checksum sections (MD5Sum, SHA1, SHA256, SHA512),
    computed from the index set;
  - `Date` and `Valid-Until` = `Date` + 3 days.
- `compare(aptly_release, own_release)`: byte equality except the values of
  `Date` and `Valid-Until`. aptly's Release has no `Valid-Until`, so the
  line is removed from the signer's own copy before comparing. The first
  differing field or line is reported.
- `diff(base_set, new_set)`: per package record (name, version, arch),
  added, removed and changed, with sha256, size and the previous version.
- The state machine, on a JSON state held by the service:
  - proposals;
  - approvals, each bound to the last-live base it was diffed against,
    and used once;
  - last-live, moved only by a verified live confirmation;
  - the signed-Release history, for the monotonic `Date` and the
    detached/clearsign pair;
  - the cadence re-sign of the last-live set only.

**P2. `signer/aptly_signer.py`: the service on the signer VM.** It uses
only the standard library.
- `serve`: HTTP on the host-only address.
  - `POST /propose`: the task ID, plus the index set as base64. The signer
    validates it, computes the diff against last-live, and fetches every
    added `.deb` from `http://192.168.56.10:8080/`. It checks the `.deb`'s
    sha256 against the Packages entry and reads the control archive for
    maintainer scripts. It stores the proposal.
  - `POST /sign`: the Release bytes aptly wrote. The signer finds the
    approved set whose own Release matches, or the one it has just signed,
    for the second of the two calls. It signs its own Release, detached and
    clearsigned, and returns Release, InRelease and Release.gpg.
  - `POST /live`: the switch is done. The signer fetches
    `dists/resolute/InRelease` from :8080 and verifies that it is its own
    signature over exactly the Release it signed. It then moves last-live,
    consumes the approval and revokes the others.
  - `GET /current`: the latest re-signed trio for last-live.
- `console`: on the signer's TTY only, for May. It lists pending proposals
  with the signer-computed diff, then approves or rejects. It has no
  network listener.
- `resign`: run by a timer on the signer. It re-signs last-live with a new
  `Date` and `Valid-Until`, from the template and the approved set only.
- Signing backend: `gpg --batch --local-user <fpr> --detach-sign --armor`
  and `--clearsign`, with a `GNUPGHOME` given in the service
  configuration. The key is generated by May in step 3.

**P3. `scripts/gpg_standin.py`, on builder.** aptly is pointed at it as
its `gpg`, at cut-over, by May's setup; this task does not install it.
- It answers `--version`.
- For `--detach-sign` and `--clearsign` it parses the options above,
  refusing unknown ones, and sends the source Release to `POST /sign`.
- It overwrites the source Release with the signer's Release and writes
  the destination (Release.gpg, or InRelease) from the answer.
- On a refusal or a timeout it exits non-zero and writes nothing, so aptly
  aborts before renaming. The rehearsal proves that this leaves the old
  files live.

**P4. `scripts/signer_client.py`, on builder.**
- `propose <rehearsal public dir>`: collects the rehearsal publication's
  index set and posts it.
- `live`: reports the switch.
- `refresh`: fetches `/current` and writes the re-signed trio into
  `/srv/aptly/public/dists/resolute/`, after checking the signature with the
  signer's public key given in its configuration.

`publish_aptly.py` itself is not changed in this task. Its proposal step
runs a rehearsal publication, and that depends on the rehearsal proofs.
It is proposed as a follow-up once they pass.

**P5. Tests, standard library only.**
- `signer/tests/test_signer_core.py` covers every refusal case in -019's
  list. Each case starts from an approved Release and index set and changes
  exactly one thing:
  - each Release field: changed, added, removed;
  - a checksum line in each section: size or hash changed, a file added, a
    file removed;
  - each compressed variant differing from the decompressed content;
  - in a Packages or Sources entry: version, arch, sha256, size, filename,
    another control field, an entry added, an entry removed;
  - the distribution, component and prefix;
  - `Valid-Until` earlier than `Date`, or more than 3 days after it;
  - an approval used after last-live moved;
  - an approval used twice;
  - a re-sign of a set that is not last-live;
  - `InRelease` and `Release.gpg` over different bytes;
  - a `Date` earlier than the last signed one.

  The positive case: only `Date` and `Valid-Until` change, and the signer
  signs.
- The service and the stand-in are tested end to end in one process tree,
  on localhost, with a throwaway key in a temporary `GNUPGHOME` created and
  deleted by the test (never `~/.gnupg`), and a fake :8080 served from a
  temporary directory.

## 3. Open points for the Design Challenger and the coordinator

1. **Test key.** Is a throwaway key in a temporary `GNUPGHOME` acceptable
   under "no keys, no `~/.gnupg`"? It is created and deleted inside the
   test and never touches the user's keyring.
2. **Rehearsal proofs.** Running aptly with the stand-in on the rehearsal
   root proves "aptly signs temporary files before renaming them" and "the
   stand-in can overwrite Release, InRelease and Release.gpg before that
   rename". It needs an aptly publish on the rehearsal root. I propose
   doing it in this task only with the coordinator's explicit go-ahead;
   otherwise it moves to step 4.
3. **`publish_aptly.py` integration** is deferred, as P4 says.

## 4. Rehearsal proofs (pending)

The proofs, the Design Challenger's gate from -019 round 3: if either fails,
the design goes back to the Challenger.
