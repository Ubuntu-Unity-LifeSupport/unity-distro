---
name: package-version-safety
description: Check Ubuntu/Debian package version ordering and update behavior before building or publishing a carried package.
---

# Package version safety

Run before the first build and again, as part of the gate, before publishing.
Follow the gates in [`docs/ENGINEERING-PROCESS.md`](../../../docs/ENGINEERING-PROCESS.md)
section 6. The verdict comes from a measurement made by
`scripts/apt_view.py`; do not type archive versions or apt candidates into a
record - `scripts/version_safety.py` rejects anything that is not
`apt_view.py` output.

Before building (ordering only, never `SAFE`):

```sh
python3 scripts/apt_view.py --source-package <source> --write /tmp/pockets.json
python3 scripts/version_safety.py --view /tmp/pockets.json --pre-build \
  --candidate-version <planned version> --source-commit <commit>
```

For the gate, after the build and after the snapshot exists:

```sh
python3 scripts/apt_view.py --manifest <build manifest> --snapshot <snapshot> \
  --write docs/research/<task>/version-check.json
python3 scripts/version_safety.py --view docs/research/<task>/version-check.json \
  --manifest <build manifest>
```

`apt_view.py` measures, in an isolated apt state (never the host's apt
configuration, never as root):

- the source package's highest version in each pocket of
  `docs/apt/target.sources` (resolute, -updates, -security, -backports, and
  -proposed as deb-src only), from the `Sources` indices;
- with `--snapshot`/`--manifest`, apt's candidate for every binary of the
  build, with the Ubuntu archive as the reference target uses it and our
  repository as the gated snapshot will publish it;
- the snapshot's package-list hash and each fetched Release's hash and Date.

Pass `--aptly-config` to measure a scratch aptly; the live aptly is the
default. Any fetch failure refuses.

`version_safety.py` returns exactly one result:

```text
SAFE
UNSAFE
REPLACES_SECURITY_UPDATE
BLOCKS_FUTURE_UPDATE
UNKNOWN
```

- `REPLACES_SECURITY_UPDATE`: the candidate is not newer than the version in
  -updates or -security.
- `BLOCKS_FUTURE_UPDATE`: a version pending in -proposed is not older than the
  candidate; when it migrates, Ubuntu's version supersedes ours.
- `UNSAFE`: not newer than resolute or -backports, or apt selects another
  version of a built binary.
- `UNKNOWN`: not a valid measurement, an unknown pocket, binaries that do not
  match the manifest, or a pre-build check (ordering only).

Only `SAFE` passes. A binNMU binary is judged by its own version. A source
that is in no archive pocket is recorded "not in archive". Re-run both steps
after rebuilding or recreating the snapshot; the publisher repeats them right
before the switch and refuses if the snapshot content or the archive changed
backwards.
