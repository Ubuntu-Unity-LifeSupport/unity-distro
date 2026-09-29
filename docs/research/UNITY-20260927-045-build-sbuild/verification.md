# UNITY-20260927-045 independent verification

Verifier: ephemeral `adversarial-verifier` subagent (read-only; no VM, no
edits), 2026-09-27, on branch `b/UNITY-20260927-045` at `d8861dc`.

- verification_result: **PASS** (finding: PATCH_CORRECT)
- review_status: **INDEPENDENTLY_REPRODUCED** - ran the unit tests against the
  unmodified script (30499ff: 5 of 6 fail - epoch exit 2, meta and
  unrelated-files exit 2, xorg-server exit 0 with `xserver-xorg-core`
  silently missing, log = dpkg-source line then header; control passes) and
  against the patched script (6 of 6 pass), plus its own stub cases. No real
  sbuild run.

Own stub cases on the patched script: `.changes` with CRLF, trailing spaces,
PGP signature, multi-line Description and Checksums-Sha1 - parsed correctly;
version `2:1.0~rc1+dfsg-1ubuntu1+unity1` - correct (the unmodified script
exits 2); a `.deb` whose sha256 differs from the `.changes` - exit 2 with a
message; an extra fresh `_source.changes` - exit 2 ("found 2"), loud.

Checked: the stub models sbuild's non-tty behaviour (Sbuild/Conf.pm:1918-1921,
Build.pm:3911-3930); `--verbose` keeps sbuild's own `.build` file and is not
interactive; in the real unity-gtk4-menu run the script's log is the header,
the dpkg-source lines, then a byte-identical copy of that run's `.build`
file. Binary versions carry the epoch and equal `candidate_version`, as
`publish_aptly.py:240` requires. The change is limited to the three scope
items; manifest keys unchanged.

Limits of the evidence: `check-manifest.py` uses the same parsing and the
manifest's own `.changes`, so it shows consistency, not that the `.changes`
belongs to the run; the old script's epoch failure on a real build is cited
from UNITY-20260927-021; the overlay-scrollbar runs prove nothing.

Consequences for consumers (for the coordinator):
1. `.ddeb`/`.udeb` are now `kind: binary`, so `publish_aptly.py` will require
   the `-dbgsym` packages in the gated snapshot (earlier practice sometimes
   left them out of aptly).
2. A binary built with a version other than the source's is now listed and
   `publish_aptly.py:240` rejects the build (before, it was dropped silently).
3. If sbuild were configured to include the source in the `.changes` (not
   the case here), the `.dsc` would appear twice and `.tar.xz` as kind `xz`;
   harmless to both scripts.
4. Unsupported but failing cleanly: binNMU `+bN` versions, `$build_dir` or
   `$source_only_changes` in sbuild's config (not set on builder), a stale
   `.changes` written less than 2 s before the run.
5. Source component files (`.orig`, `.debian.tar`, native `.tar.xz`) are not
   in the manifest before or after; not made worse.

Not checked: a real xorg-server build, a real publication through
`publish_aptly.py` / `create_release_gate.py`.
