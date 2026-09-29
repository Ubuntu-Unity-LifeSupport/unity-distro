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

## 10. Design review 2: REVISE, and the changes

The review accepts amendment (a), A1 (it fails closed) and May's invariant,
which is unchanged. It found the refresh path as written in section 8
wrong: `/current` serves last-live, and last-live moves only at `/live`. So
a refresh before a successful `/live` would put the old set's trio over the
new indexes. Section 8 is corrected as follows.

R1. **The refresh right after the switch installs the switch-time trio.**
- The stand-in stores the trio it received at the switch in a 0600 file,
  named by the sha256 of aptly's Release, under
  `~/.cache/aptly-signer/switch/`.
- The run is: switch, then refresh with that stored trio (no `/current`),
  then `/live`.
- The one-call window does not depend on `/live`.

R2. **Every refresh checks before writing**, the cadence refresh included.
The trio's checksums must equal the index files served under
`dists/resolute/`. On a mismatch it writes nothing, marks the publication
and signals C.

R3. **Section 8's "the next cadence refresh repairs it" is corrected.** It
holds only if `/live` succeeded. If `/live` failed, the cadence re-signs
the previous set. R2 refuses to install it, and the repository expires at
`Valid-Until`. That is reported as expiry (the "repository has expired"
report from -019 round 3), with the refresh marker.

R4. **The marker.** In this task, `signer_client.py refresh` writes only
the marker file `~/coordinator/publish-records/<task>.refresh-failed` and
the `REFRESH-FAILED <task>` log line; the publish record is write-once. In
the `publish_aptly.py` follow-up, the refresh runs before the write-once
record, so the record carries the refresh result.

R5. **Write order.** `Release` and `Release.gpg` are each written through a
temporary file and a rename, then `InRelease`.

R6. **The stand-in's inputs (A1).**
- It reads only regular files, with no symlinks, from aptly's temporary
  directory.
- The names are mapped strictly from the Release's file list (`/` becomes
  `_`).
- The rehearsal records the directory listing at the moment gpg is
  called. If the rehearsal refutes the temporary-directory assumption, the
  design goes back to the Challenger. There is no quiet switch to storage
  `.tmp` paths.

Tests added:
- a refresh with the old set's trio over new indexes is refused, and
  nothing is written;
- the ordering: the refresh after the switch uses the stored switch-time
  trio, and works without `/current` and before `/live`;
- the cadence refresh before `/live` is refused by R2;
- the write order;
- a symlink or an unlisted file in the temporary directory is refused by
  the stand-in.

## 11. Design review 3: APPROVE

R1-R6 close round 2; May's invariant unchanged. Notes taken into the
implementation: the stand-in sends only the listed files and explicitly
allows the signing source and its `.gpg` (aptly writes `<tmp>.gpg` into the
same directory before ClearSign), refusing only symlinks, non-regular
files or a missing listed file; the stored switch-time trio is checked on
install (key = sha256 of aptly's Release, signer Release equal to aptly's
apart from Date/Valid-Until) and deleted after a successful install or at
the next switch; a test that a stored trio from an earlier switch fails R2.

## 12. Implementation (before the rehearsal)

Code on branch `a/UNITY-20260929-021`:

- `signer/signer_core.py`: pure logic, as in sections 2 and 9-11.
  - It checks the index set: allowed paths, variants equal once
    decompressed, component Releases exactly the template's, size limits,
    no Contents.
  - It validates entries: Debian grammar, hex sha256, digit sizes,
    normalised `Filename`, duplicates refused.
  - It builds the Release from the template, and compares it with aptly's,
    naming the field or checksum file that differs.
  - It computes the signer-side diff shown on the console, where other
    fields appear by name and hash only.
  - The state machine: an approval bound to its base and used once; the
    two calls, where the same bytes return the stored pair and other bytes
    are refused; `/live` only for the InRelease of a signed, unconsumed
    approval on the current base; a re-sign of last-live only, from its
    stored files; Dates strictly increasing.
- **`Date` is backdated.** The coordinator reported that target2's clock
  was about 4.5 minutes behind, so apt refused a fresh InRelease as "not
  yet valid". The signer therefore backdates `Date` by the template's
  `date_backdate_seconds`, 300 seconds, and `Valid-Until` is
  `Date` + 3 days. Clock sync on the targets is UNITY-20260929-022.
- `signer/release-template.json`: the fields and order of aptly 1.6.2's
  Release and component Release, taken from the live
  `/srv/aptly/public/dists/resolute/`. It adds `Valid-Until`, and sets
  `valid_days` 3 and the backdate.
- `signer/aptly_signer.py`: the service.
  - One JSON state file, with `flock` across processes and atomic writes.
    Missing or corrupt state refuses everything, and `init` refuses to
    overwrite existing state.
  - `GpgBackend`: `--homedir`, `--local-user <fpr>!`, and every output
    checked with `gpgv` against a keyring holding only the pinned key.
  - The maintainer-script flag: the `.deb` is fetched from the repository
    (no redirects, a normalised `Filename`, capped at `Size`), its sha256
    and size checked, and its ar and control archive (tar, gz, xz, zst)
    read. Any failure refuses the proposal.
  - HTTP: `Content-Length` required and capped, no chunked bodies, socket
    timeouts, JSON only, and errors reduced to printable text.
  - The console (`init`, `template-hash`, `list`, `show`, `approve`, which
    needs "approve" typed, `reject`, `log`) and `resign`.
- `scripts/gpg_standin.py`:
  - It implements aptly 1.6.2's calls (`--version`, detached and
    clearsign) and refuses unknown options, a positional count other than
    one, a symlink and a missing listed file.
  - It never sends `--passphrase`.
  - It reads the listed index files from aptly's temporary directory
    (`/` becomes `_`), writes its destination through a temporary file
    and a rename, and stores the trio 0600 under the sha256 of aptly's
    Release.
- `scripts/signer_client.py`:
  - `propose`: the rehearsal index set.
  - `refresh --switch`: the stored switch-time trio. `refresh --current`:
    the signer's latest re-signed trio.
  - Both run the R2 check before writing: the trio's Release lists exactly
    the served files and checksums, InRelease and Release.gpg verify with
    the pinned key over it, and, for `--switch`, it equals aptly's served
    Release apart from Date and Valid-Until. Then the write order of R5,
    and the stored trio is deleted. A failure writes the marker and the
    log line.
  - `live`.

Tests:

- `scripts/tests/test_signer_core.py`, 21 tests with a fake signing
  backend. They cover every refusal case in -019's list and in design
  reviews 3 and 4, plus the plan reviews' additions:
  - Release fields changed, added or removed, including Valid-Until,
    NotAutomatic, ButAutomaticUpgrades, Acquire-By-Hash and Signed-By;
  - checksum lines in all four sections: size, hash, a file added, a file
    removed;
  - compressed variants differing;
  - Packages entries: version, arch, sha256, size, filename, another field,
    an entry added or removed;
  - distribution, codename, prefix (Origin and Label) and component;
  - component Release fields;
  - paths, Contents, by-hash and i18n;
  - duplicates and malformed entries, including control characters;
  - decompression limits;
  - an approval used twice, with the two-call pair returned without
    signing again;
  - an approval after last-live moved;
  - a stale proposal;
  - `/live` refusals: foreign, extra data after the signature, Release.gpg
    instead, and an older signed Release, which cannot roll back;
  - content that was not approved;
  - strictly increasing Dates;
  - InRelease and Release.gpg over different bytes;
  - a re-sign of last-live only, from stored files that must still match;
  - corrupt state;
  - the console showing only validated text;
  - a `.deb` check failure refusing the proposal.

  The positive case checks the backdated `Date` and `Valid-Until`
  = `Date` + 3 days.
- `scripts/tests/test_signer_end_to_end.py`, 10 tests. They use the real
  service with a throwaway gpg key under the coordinator's conditions,
  the real stand-in called with aptly's exact argv as a subprocess, the
  real client, and a fake `:8080` with real `.deb`s, one of them with a
  postinst.
  - The full cycle:
    - propose;
    - the console shows "scripts: postinst" and the claimed task;
    - approve;
    - the switch, with live gzip bytes different from the rehearsal's;
    - InRelease valid with Valid-Until while the detached pair fails
      closed;
    - `refresh --switch` closes the window and deletes the stored trio;
    - `/live`;
    - `resign`, then `refresh --current`, with the Date increasing.
  - The passphrase never reaches the signer or its state, and `--version`
    matches aptly's regex.
  - Stand-in refusals write nothing: not approved, an unknown option, two
    files, a missing listed file, a symlink, and the signer unreachable.
  - A failed refresh writes nothing and leaves the marker and the
    `REFRESH-FAILED` line.
  - A cadence refresh before `/live` is refused by R2, and a stale stored
    trio is refused.
  - The pinned fingerprint refuses another key.
  - HTTP limits and corrupt state.
  - `.deb` problems: a 404, a sha256 mismatch, a malformed control
    archive.
  - `~/.gnupg` is untouched (file list and mtimes before and after).
- Full suite: 263 OK (1 skipped).

**Still open, in the rehearsal** (May's GO and C's marker, sections 7 and
9):
- signing before the rename;
- a refusal leaving the old files live;
- the index temporary files present when gpg is called, with the
  directory listing recorded;
- the argv aptly actually passes, recorded, with the tests adjusted to it;
- the SkipContents setting.

**Not in this task:**
- the `publish_aptly.py` integration (follow-up);
- installation on the signer, the key, and the cut-over (May, steps 3
  and 4).

## 13. Rehearsal (window 2026-09-29 22:29-00:29Z, May's GO, C's marker)

Deviations at step 0, before any aptly command, each handled by the
coordinator's rule (remove the symlink, stop, report) and resumed with the
coordinator's go-ahead in the same window (`rehearsal/00-symlink.txt`):

1. **The stand-in was not executable.** At 22:29:08Z the symlink
   `~/.local/bin/gpg` pointed to `scripts/gpg_standin.py`, which was mode
   644 from git, so `command -v gpg` still gave `/usr/bin/gpg`. The symlink
   was removed at 22:29:20Z. Fix: the stand-in is mode 755, committed.
2. **The signer called gpg by name.** After step 0 succeeded (22:29:49Z:
   `command -v gpg` gave `~/.local/bin/gpg`, `--version` from the stand-in),
   the local signer's `GpgBackend` called `gpg` by name, which would have
   resolved to the stand-in. The symlink was removed and the signer stopped
   at 22:30:13Z. The temporary GnuPG home was removed and `~/.gnupg`
   unchanged.

   Fix: the service calls gpg and gpgv only by absolute path, from its
   configuration (`gpg`, `gpgv`, defaulting to `/usr/bin/gpg` and
   `/usr/bin/gpgv`), and refuses a relative path. The client's gpgv call and
   the rehearsal helper's gpgconf call are absolute too. The stand-in calls
   no program. A test checks that a `gpg` placed first on PATH does not
   reach the signer's signing. Suite: 265 OK (2 skipped; the second is the
   guard test "denied without marker", skipped while a rehearsal
   authorization is active).

Further deviations, each handled the same way: symlink removed, stop,
report, and resumed with the coordinator's go-ahead.

3. **Directory permissions.** The guard refused the first publish because
   the rehearsal trees were group-writable (mkdir and aptly create 775).
   The fix is the same as in UNITY-20260927-047: `chmod -R go-w` on
   `021/` and `021p/` after every aptly command.
4. **Design gap: the `.deb` is not on `:8080` before the switch.**
   `/propose` was refused because the signer fetches each added `.deb`
   from the live repository, but aptly links pool files into `public/` only
   when it publishes. The same failure would happen in production for every
   new package.
   - The coordinator decided a temporary, rehearsal-only setting: the local
     repository server serves `021/state/public` first and the proposal
     root `021p/state/public` second, on 127.0.0.1 only. It is not part of
     the product.
   - The product fix is amendment (b), in section 15.
5. **aptly's initialisation probe and the config path.** aptly's
   `GpgSigner.Init()` runs `gpg --list-keys --dry-run --no-auto-check-trustdb`
   and refuses empty output (from its source). Also, the aptly command can
   carry no environment prefix, so the stand-in reads its config only from
   its default path.
   - Fix: the stand-in answers exactly that probe with a fixed line
     carrying `key_id` from its config, with exit 0 and without contacting
     the signer. Any other unknown call is still refused.
   - For the window, the config was placed at
     `~/.config/aptly-signer/standin.json` and deleted afterwards.
6. **Code bug: several versions of one package.** The proposal for B was
   refused as "listed twice": entries were keyed by (package, arch), but a
   repository lists several versions; the live one has nine unity
   versions.
   - Fix: the key is (index, package, version, arch), and a duplicate is
     only a full match.
   - The diff works per version, with the other versions shown.
   - Tests: several versions, and the live fragment with nine unity
     entries (`scripts/tests/fixtures/live-packages-unity.txt`).
   - The signer was restarted with a fresh rehearsal state; A's proofs
     were already recorded.

**Results on aptly 1.6.2** (`rehearsal/`, stand-in trace in
`rehearsal/standin-trace.jsonl`):

1. **argv.** The detached call is
   `-o <tmp>/Release.gpg --digest-algo SHA256 --armor --yes --detach-sign <tmp>/Release`,
   then the clearsign call is
   `-o <tmp>/InRelease --digest-algo SHA256 --yes --clearsign <tmp>/Release`.
   At initialisation aptly runs `--list-keys --dry-run --no-auto-check-trustdb`.
   Without `-keyring` or `-gpg-key`, no keyring or `-u` options are passed.
   The tests use this argv plus the optional options.
2. **The temporary directory** at the moment gpg is called holds
   `Release` and every listed index (`main_binary-amd64_Packages`, `.gz`,
   `.bz2`, `_Release`). At the second call it also holds `Release.gpg`.
   A1 is confirmed.
3. **The window.** After the signed publish of A (`03-*.txt`) and the
   switch to B (`04-switch-B.txt`), `InRelease` verifies with the signer's
   key and carries `Date`, backdated by 5 minutes, and `Valid-Until` =
   `Date` + 3 days. aptly's published `Release` has no `Valid-Until`, and
   `Release.gpg` over it is BAD, so the window fails closed.
   `refresh --switch` makes the pair good and deletes the stored trio.
   `/live` moves last-live.
4. **Signing before the rename** (`05-refusal-C.txt`). At the switch to
   C, which was never approved:
   - the stand-in was refused ("this content was not approved on the signer
     console");
   - aptly aborted with "unable to detached sign file";
   - `Release.tmp` and `Packages.tmp*` are in storage, put there before
     signing and never renamed.
5. **A refusal leaves the old files live.** `Release`, `Release.gpg`,
   `InRelease` and `Packages` are byte-identical to B's and still verify.
   Observation: after a refusal aptly leaves `*.tmp` files in storage,
   which the next switch overwrites. The `publish_aptly.py` follow-up
   should know this.

Teardown at 22:47:47Z (`06-teardown.txt`):
- the symlink removed, with `command -v gpg` = `/usr/bin/gpg`;
- the window config deleted;
- the signer and both servers stopped;
- the temporary GnuPG home removed, with `~/.gnupg` unchanged.

The rehearsal log has 21 lines, 6 of them from this task. The roots `021/`
and `021p/` are kept for the Verifier.

## 15. Design amendments after the rehearsal (for the Design Challenger)

**(b) The added `.deb`s travel in `/propose`.** This is the coordinator's
decision; deviation 4 refuted -019 round 2 item 5, "the signer fetches it
from :8080", before the switch.
- `signer_client.py propose` reads each added `.deb` from the proposal
  (rehearsal) publication's pool, at the `Filename` its Packages gives,
  and sends it in the request.
- The signer:
  - accepts only `.deb`s whose `Filename` it validated in the Packages it
    checked itself;
  - requires the bytes to match that entry's `SHA256` and `Size`;
  - reads the control archive from those bytes.

  A missing, extra or mismatched `.deb` refuses the proposal.
- Integrity does not depend on where the bytes come from: the signer
  checks them against its own validated Packages.
- `max_body` bounds the request.
- The `:8080` fetch is dropped for proposals. It stays only for `/live`,
  which fetches `InRelease`.

**The stand-in's default config path is a product decision for the
cut-over.** The aptly command can carry no environment prefix, so the
stand-in reads `~/.config/aptly-signer/standin.json` of the user who runs
aptly. That file is 0600 and holds the signer's URL, the timeout, the
store and `key_id`. `APTLY_SIGNER_STANDIN_CONFIG` remains for tests only.

## 16. Design review 4: APPROVE, and the amendments in code

The Design Challenger's round 4 approved (b) and (c) and settled (d):
- The rehearsal confirmed the gates, and the step-0 code fixes (executable
  stand-in, absolute gpg paths, the exact Init probe, and keys that include
  the version) are sound as design changes.
- May's invariant is unchanged.

**(b) In code.**
- `signer_core.DebSet` takes the `.deb`s from `/propose`.
  - A `.deb` is required for every Packages entry whose SHA256 is not in
    last-live: an added entry, or one changed under the same name, version
    and arch.
  - Each must match the `Size` and `SHA256` of the entry in the Packages
    the signer checked itself.
  - A missing, mismatched or extra `.deb` refuses the proposal.
- `aptly_signer.script_scanner` reads the control archive in memory
  (`bounded_decompress` for tar, gz, xz and zst, capped by `max_control`,
  16 MiB), lists member names only and extracts nothing.
- The `:8080` fetch of `.deb`s is removed. `/live` still fetches
  `InRelease` from the repository.
- `signer_client.py propose` sends every `.deb` whose SHA256 is not in the
  live Packages under `public_root`, read from the proposal publication's
  pool.
- **Effective limit.** `max_body` is 96 MiB, and the `.deb`s travel base64
  inside it, so a proposal can carry at most about 72 MiB of `.deb`s. A
  larger one is refused (fail closed).
- Tests:
  - missing, extra and mismatched `.deb`;
  - a changed entry under the same key needs its `.deb`, and the console
    shows "changed libdemo1 ... scripts: postinst";
  - the decompression cap;
  - the end-to-end flow now proposes with the pool, as a real rehearsal
    publication has.

**(c) The stand-in's config.**
- The default path `~/.config/aptly-signer/standin.json` stays as the
  fallback. `APTLY_SIGNER_STANDIN_CONFIG` stays as an override.
- **Product mechanism, recorded for the `publish_aptly.py` follow-up and
  May's step 4:** `publish_aptly.py` passes aptly its own `env`, with
  `PATH=<stand-in dir>:...` and the config variable, in its
  `subprocess.run`.
- It does not use a global `~/.local/bin/gpg`, which would shadow gpg for
  everything `claude` runs: debsign, git, and the key removal in the
  rotation. That was acceptable only for the rehearsal window, with B on
  hold.

**(d) The leftover `*.tmp`: nothing more in this task.** They are
unsigned, no Release references them, and the next switch overwrites them.
For the follow-up:
- report them as "the last switch was refused";
- no agent deletes them behind aptly;
- R2 ignores them. It already does, since it compares only the files the
  trio's Release lists.

The follow-up also sets or checks `go-w` on its trees, as the guard
requires (deviation 3).

## 17. Verification

**Round 1** on `1748caf`: **FAIL** (FIX_PARTIAL, TEST_INVALID), REVIEWED.

The Verifier confirmed that the invariant holds on the paths it probed:
- the signer signs only its own Release, after a clean comparison;
- a two-call replay works only with the same bytes;
- the approval base is checked at `approve` and at `sign`;
- `/live` refuses a used, revoked or re-signed InRelease;
- a refusal leaves the state unchanged;
- the console and logs are printable only.

It re-checked the rehearsal claims byte for byte from the recorded files.

Findings:
- **FIX_PARTIAL: maintainer scripts could be hidden.** `bounded_decompress`
  read `control.tar.gz` with one `zlib.decompressobj`, which stops after
  the first gzip member. dpkg reads every member. A `.deb` with `control`
  in one member and `postinst` in a second showed "no scripts" on the
  console, while `dpkg-deb -e` extracts the executable `postinst`
  (reproduced). `tarfile` accepted the first member's tar without its end
  blocks.
- **TEST_INVALID:**
  - no test of the R5 write order;
  - the `resign_set` assertion was vacuous (the function is not used in
    production);
  - the "404" case was refused by the client, not the signer;
  - no multi-stream archive tests;
  - a stale comment.

Remarks:
- bz2 and xz index files accepted a second stream or trailing bytes;
- `str.isdigit` accepted non-ASCII digits, and `\d` in the task ID did too;
- a non-object JSON body dropped the connection;
- R2 did not check that every served index file is listed;
- a slow client can hold the single-threaded service (denial of service
  only);
- the 3-day window in which an older approved set can be served is by
  design.

**Fixes** (code `aa76007`):
- **The control archive must be exactly one complete compressed stream**
  (gz, xz or zst) with no trailing data (`eof`, and empty `unused_data`),
  within `max_control`. The tar inside must end with its two zero
  end-of-archive blocks. Anything else refuses the proposal. The
  Verifier's crafted gz, xz and zst `.deb`s are refused.
- **bz2 and xz index files** must be exactly one complete stream. gzip is
  read in full, as apt reads it.
- `Size` and the task ID accept ASCII digits only.
- A non-object JSON body is refused with 409.
- R2 also refuses a served index file that the trio's Release does not
  list.
- `resign_set` is removed. The test now checks that a re-sign covers
  last-live only, even while another approval is signed but not live.
- New tests:
  - the hidden postinst in a second gzip or xz stream is refused;
  - a single-stream control archive with a postinst is reported;
  - a tar without its end marker is refused;
  - bz2 and xz with a second stream, trailing bytes or truncation are
    refused;
  - ASCII digits;
  - the R5 write order (Release, then Release.gpg, then InRelease);
  - an unlisted served index is refused;
  - a non-object JSON body is refused.
- The 404 case is dropped from the end-to-end `.deb` test, because the
  missing `.deb` is covered by the signer-side test. The stale comment is
  corrected.
- Suite: 276 OK (1 skipped).

Not changed, and stated: the per-read timeout (a slow client can hold the
service; the signer is on the host-only network and signs nothing without
May), and the design's 3-day window.

**Round 2** on `aa76007`: **FAIL** (FIX_PARTIAL), REVIEWED.

The round-1 fixes hold: the crafted gz, xz and zst `.deb`s and the
multi-stream index files are refused. The Verifier built its suggested
bypasses and compared the signer's flag with what `dpkg-deb -e` extracts.
They agree, or the case is harmless:
- two control members;
- control after data;
- `_x` first;
- `./postinst/`;
- `x/../postinst`;
- `sub/postinst`;
- a symlink or hardlink named postinst;
- the gzip FNAME header;
- `DEBIAN/postinst` in `data.tar`.

**Finding:** a control tar with `./control`, then `./x` as a symlink to
`.`, then `./x/preinst`.
- The signer saw no script name.
- GNU tar, as run by `dpkg-deb --control` for `dpkg --unpack`, writes
  `preinst` through the symlink, so an executable `preinst` would run as
  root while the console said "no scripts".

**Fix** (code `bba2542`): `control_member_name`
accepts only regular files directly at the top level. The name has one
optional leading `./`, no `/`, and characters `[A-Za-z0-9][A-Za-z0-9_.+-]*`.
The only directory allowed is `.` itself. Symlinks, hardlinks,
subdirectories, devices, `..` and odd names refuse the `.deb`.
- Tests: the symlinked directory case, a symlink or hardlink named
  postinst, a subdirectory, `x/../postinst`, a device and a trailing space
  are refused. A clean archive is accepted.
- The Verifier's `pre.deb` is refused.
- **No false refusals:** all 280 `.deb`s in the live pool are accepted, 74
  of them flagged with maintainer scripts
  (`rehearsal/07-live-pool-control-check.txt`).
- Suite: 277 OK (1 skipped).

**Round 3** on `bba2542`: **FAIL** (FIX_PARTIAL), REVIEWED.

The round-2 fix holds. The Verifier's header battery found the signer and
dpkg agreeing, or the signer refusing, for:
- a pax or global pax `path`;
- a GNU `L` long name;
- a ustar prefix;
- a pax `size`;
- member types 7, S, NUL, Z and V.

**Finding:** Python's `tarfile` and GNU tar pick different headers for the
name when several extended headers precede one member. Two cases hid a
`preinst` that `dpkg-deb --control` extracts:
- two pax `x` headers, where tarfile takes the first and GNU tar the last;
- a GNU `L` name followed by a pax `path`.

**Fix** (code `4d26be9`): the signer no longer uses
`tarfile` for control archives. `control_tar_names` walks the raw 512-byte
headers itself and accepts only plain ustar:
- a valid header checksum;
- `ustar` magic, and no POSIX name prefix;
- typeflag `0`/NUL for a regular file, and `5` only for `./` itself, with
  size 0;
- plain octal sizes, and ASCII names under the top-level rule;
- the two zero end blocks.

Any pax (`x`/`g`), GNU long-name (`L`/`K`), link, device or other header
refuses the `.deb`.
- **Measured before the rule was set:** every control archive in the live
  pool, 280 `.deb`s, uses only typeflags `0` (954) and `5` (280), with GNU
  `ustar` magic.
- **After the fix:**
  - all 280 live `.deb`s are accepted, the same 74 flagged with scripts;
  - every crafted `.deb` from rounds 1-3 is refused (`twox`,
    `Lctl2_xpreinst`, `pre`, and the gz, xz and zst hide);
  - tests cover the pax and GNU long-name headers, a broken checksum, and
    the Verifier's crafted `.deb`s when present.
- Suite: 278 OK (1 skipped).
