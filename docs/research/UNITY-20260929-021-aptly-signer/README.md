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

## 5. aptly 1.6.2 source: one design assumption is refuted

The coordinator allowed reading aptly's source for the installed version on
GitHub (aptly-dev/aptly, tag v1.6.2) with WebFetch. It is read code, not an
aptly call.

- **`pgp/gnupg.go`** confirms the argument order in section 1.
  - `DetachedSign`: `-o <dest> --digest-algo SHA256 --armor --yes`, then
    `gpgArgs()`, then `--detach-sign <src>`.
  - `ClearSign`: the same without `--armor`, ending `--clearsign <src>`.
  - `gpgArgs()` gives, in order: keyring options, `-u`, passphrase options,
    and `--no-tty --batch`, plus `--pinentry-mode loopback` for gpg 2.1 and
    later.
- **`pgp/gnupg_finder.go`**: the binary is looked up on PATH as `gpg` or
  `gpg1` for gpg 1, then `gpg` or `gpg2`. The version comes from
  `<bin> --version`, matched against the regex `\(GnuPG.*\) (2).(\d)`.
- **`deb/publish.go`**: aptly writes no `Valid-Until`, and it has a
  `SkipContents` option. On re-publishing, a switch included, the file
  suffix is `.tmp`, and `indexes.RenameFiles()` runs at the end.
- **`deb/index_files.go`, `indexFile.Finalize`**, for the Release: it runs
  in this order.
  1. First, a loop runs `publishedStorage.PutFile(<basePath>/Release<suffix><ext>, tempFilename<ext>)`.
     **The plain Release is already in the published storage.**
  2. Then `signer.DetachedSign(tempFilename, tempFilename+".gpg")` and
     `PutFile(... Release<suffix>.gpg)`.
  3. Then `signer.ClearSign(tempFilename, <dir>/InRelease)` and
     `PutFile(... InRelease<suffix>)`.
  4. A signing error returns at once, before `RenameFiles`.

**Consequence.** Round 2 item 2 of the design assumed that the stand-in
writes the signer's rewritten Release (the new Date and Valid-Until) over
aptly's temporary file before aptly publishes it. In aptly 1.6.2 the Release
is put into storage *before* gpg is called. The stand-in can still write
`InRelease` and `Release.gpg`, which are put into storage after signing,
but not the published Release.

The other assumption holds from the source, still to be confirmed in
rehearsal: signing happens before the rename, and a signing failure aborts
before any rename.

Per -019 round 3 ("if a rehearsal proof fails, the design goes back to the
Design Challenger instead of being patched during implementation"), this
goes back to the design. No code is written.

Options for the design, not decided here:

- **(a) Leave aptly's published Release as it is, and sign the signer's
  Release.** At the switch, the stand-in writes the signer's `InRelease`
  (with Valid-Until inside) and `Release.gpg` over the signer's Release. A
  refresh step right after the switch (the same `/current` path the
  cadence uses) replaces `Release`, `InRelease` and `Release.gpg` with the
  signer's trio.
  - Between the switch and the refresh, the published `Release` (aptly's,
    without Valid-Until) does not match `Release.gpg`. `InRelease` is
    valid and carries Valid-Until. apt reads `InRelease` first.
  - This costs a short window where the detached pair does not verify.
- **(b) The stand-in also overwrites the storage copy.** It writes
  `public/dists/resolute/Release.tmp`, which aptly has just put there on a
  switch, before signing. This depends on local storage, the suffix and
  the path, which are internals, and a rehearsal would have to prove it.
- **(c) aptly publishes no signature at all** (signing off), and builder
  installs the signer's trio after the switch. There is then a window with
  a new unsigned Release and the old signatures, so apt refuses the
  repository until the install.

## 6. Design review of the implementation plan: REVISE

Blocking:

1. **Checksum matching.** The rehearsal's compressed bytes need not equal
   the live ones, yet the Release lists them. Either `/sign` also receives
   the live index files, and the signer checks and uses their bytes, or a
   proof shows that rehearsal and live compression are byte-identical.
2. **Per-component Release files** (`main/binary-*/Release`,
   `main/source/Release`). They must be built by the signer from its
   template, and checked byte for byte.
3. **`/live` and `/sign`.** They accept only an unconsumed approval whose
   base is still last-live. A valid old signature must not move last-live,
   which would be a rollback without May.
4. **Builder text on the console.**
   - Package fields are validated against Debian grammar.
   - For other control fields, only the field name and hashes are shown.
   - The task ID is shown only if it matches `^UNITY-\d{8}-\d{3}$`,
     labelled "claimed by builder".
   - The logs are sanitised.

Required: the rest of the review's list, including the rules for the
two-call flow, the stand-in, the template committed and hashed, flock and
atomic state, HTTP limits, the :8080 fetch hardening, `--local-user <fpr>!`
and a gpgv check. It also said the rehearsal is an aptly publish that
agent A must not run, and belongs to C or May. The coordinator's answer
(below) sets the rehearsal procedure: May's GO and C's marker, within this
task.

## 7. Coordinator's answers (2026-09-29)

- **The throwaway test key is allowed:**
  - `GNUPGHOME` via `mktemp -d`, mode 0700;
  - an explicit `--homedir` for gpg and for gpgconf;
  - in teardown, `gpgconf --homedir X --kill all`, then remove the
    directory with `${X:?}`;
  - the test checks that `~/.gnupg` and its agent are untouched (mtime and
    the key list, before and after).
- **Rehearsal on the rehearsal root.** It is an aptly publish under the
  rehearsal allowance, and needs May's GO and C's marker (section 6 of
  ENGINEERING-PROCESS). The order is code and tests first, then the
  rehearsal within -021, before merge. If it refutes an assumption, the
  design returns to the Design Challenger.
- **aptly's source** may be read on GitHub (section 5).

## 8. Design amendment (coordinator's decision, 2026-09-29): option (a)

This amends UNITY-20260929-019 round 2 item 2, "the stand-in writes all
three over aptly's temporary files before aptly renames them into place",
which aptly 1.6.2 refutes (section 5). The -019 design task stays with B,
in BLOCKED, and is not changed; the amendment lives here.

- **At the switch.** aptly has already put its own Release into storage.
  When aptly calls gpg, the stand-in:
  - sends that Release, and the live index files (A1 below), to the
    signer;
  - receives the signer's Release, `InRelease` and `Release.gpg`;
  - writes aptly's destinations: `InRelease` (the signer's clearsigned
    Release, carrying `Valid-Until`) and `Release.gpg` (the signer's
    detached signature over the signer's Release).
- **Right after the switch, in the same `publish_aptly.py` run,** a refresh
  installs the signer's trio into `dists/resolute/`. The window in which the
  published `Release` (aptly's) does not match `Release.gpg` is therefore
  bounded by one call. `InRelease`, which apt reads first, is valid from
  the moment of the switch.
- **If the refresh fails:**
  - the publication is marked: the publish record gets
    `refresh: FAILED`, and a marker file
    `~/coordinator/publish-records/<task>.refresh-failed` is written;
  - C gets a signal: a `REFRESH-FAILED <task>` line in `~/AGENTS-LOG.md`,
    and a non-zero exit with the reason;
  - `InRelease` stays valid until `Valid-Until`, and the next cadence
    refresh repairs it.
- **Rejected:**
  - (b) overwriting `Release.tmp` in storage: it depends on aptly
    internals;
  - (c) publishing unsigned and installing afterwards: it opens a window in
    which apt refuses the repository.

## 9. Revised plan (the plan review's blocking points)

A1. **Checksums of the compressed variants: `/sign` receives the live index
files.** aptly writes its index temporary files in the same temporary
directory as the Release it asks gpg to sign. The file names are the
relative path with `/` replaced by `_` (`BufWriter` in
`deb/index_files.go`). The stand-in sends every file the Release lists,
read from that directory. The rehearsal must confirm that they are there
when gpg is called. The signer:
- checks that each file decompresses to the approved content;
- refuses any listed file it did not receive, and any unlisted file;
- builds its Release from those exact bytes and the template.

So the signed checksums are those of bytes the signer checked.

A2. **Per-component Release files** (`main/binary-*/Release`,
`main/source/Release`). The signer builds them from its template (Archive,
Component, Origin, Label, Architecture, and the other template fields) and
requires the received bytes to equal them exactly. Refusal tests cover each
of their fields.

A3. **`/sign` and `/live` take only an unconsumed approval whose base is
still last-live**, checked at both.
- `/live` moves last-live only when the `InRelease` served on :8080 is
  byte-identical to the one the signer produced for that approval.
- A valid signature from the signer's own history, over an older Release,
  is refused. Otherwise it would be a rollback without May.

A4. **No builder text reaches the console unvalidated.**
- Package name, version and arch are checked against Debian grammar,
  sha256 must be hex, and size must be digits; a set that fails is
  refused.
- For any other changed control field, the console shows only the field
  name and the old and new hashes.
- The task ID is shown only if it matches `^UNITY-\d{8}-\d{3}$`, labelled
  "claimed by builder". Otherwise it is not shown.
- Logs apply the same rule. No control characters are printed.

**The review's other required points, all taken:**
- **Two calls.** The first `/sign` signs once and stores the detached and
  clearsigned pair over the same bytes. The second call must present
  exactly those bytes (aptly's Release with the same index files), in
  either order, and receives the stored pair: no new signing and no new
  Date. Each new Date is strictly greater than the last one signed.
- **Stand-in.**
  - It refuses unknown options and any positional count other than one.
  - It never forwards or logs `--passphrase`.
  - `--version` prints `gpg (GnuPG) 2.4.8`, which matches aptly's regex.
  - The argv seen in the rehearsal is recorded, and the tests use it.
  - aptly operations in this project that call gpg are listed. The
    provider is global, and only publish signs.
- **SkipContents.** The step-4 precondition states how the live
  publication and the rehearsal are set to skip Contents (aptly's
  `SkipContents`), since `publish switch` keeps the existing setting.
  The signer refuses any `Contents-*`.
- **Template.** It is committed at `signer/release-template.json` and
  reviewed. The console shows its sha256 when May installs it. It is
  never taken from builder.
- **State.**
  - One JSON state file on the signer, guarded by `flock` across the
    `serve`, `console` and `resign` processes.
  - Atomic writes: a temporary file, fsync, `os.replace`, then fsync of the
    directory.
  - Missing or corrupt state refuses everything and never reinitialises.
    First initialisation is an explicit console command.
- **HTTP.**
  - It binds only to the configured host-only address.
  - `Content-Length` is capped, and chunked bodies are refused.
  - Every socket has a timeout.
  - Pending proposals are capped in number and in total size.
  - Decompressed sizes are capped.
- **The :8080 fetch.**
  - No redirects, and a fixed base URL.
  - `Filename` is normalised, with no `..`, absolute paths or
    percent-encoding.
  - The download is capped at the Packages `Size`.
  - A 404, a sha256 mismatch, or a malformed ar or control archive (gz, xz
    or zst) refuses the proposal. It is never shown as "no scripts".
- **Signing.**
  - `gpg --homedir <configured> --batch --local-user <fpr>!`.
  - Each output is checked with `gpgv` against the pinned public key
    before it is returned.
  - The pinned fingerprint refuses any other key, the test key included,
    in production configuration.
- **Scope.** The `publish_aptly.py` integration is a follow-up: the
  proposal step, the switch, the refresh right after it, and round 3's
  "repository has expired" reporting. In this task, `signer_client.py
  refresh` implements the refresh with the marking and signal above, and
  `publish_aptly.py` will call it.

**Tests** (standard library; the throwaway key per section 7): everything
in section 2 P5, plus:
- per-component Release fields;
- `/live` refusals: a foreign key, an older signed Release, a set that is
  not approved, extra data after the signature;
- `.deb` failures, each of which refuses the proposal;
- index paths with `..`, an absolute path or percent-encoding;
- decompression limits;
- duplicate fields or entries;
- aptly's Release already carrying a `Valid-Until`;
- a Date equal to the last one;
- a stand-in timeout or refusal, with nothing written;
- approving a proposal whose base is stale.

For the amendment:
- after the simulated switch, `InRelease` is valid over the signer's
  Release;
- the refresh closes the window: `Release` and `Release.gpg` match;
- a failed refresh leaves the marker and the log line and exits non-zero.

**Rehearsal: the coordinator's answer to the review.** The rehearsal
allowance exists so that the agent in a named session runs aptly publish
on the rehearsal root under C's marker, after May's GO. See
ENGINEERING-PROCESS section 6 and UNITY-20260927-057; B did the same for
UNITY-20260927-047 R. The procedure in section 7 stands: code and tests
first, then the rehearsal within -021, before merge, and back to the Design
Challenger if an assumption fails. The rehearsal proves:
- signing before the rename;
- a refusal leaving the old files live;
- the index temporary files present in aptly's temporary directory when gpg
  is called (A1);
- the argv aptly passes.
