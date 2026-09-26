---
name: package-version-safety
description: Check Ubuntu/Debian package version ordering and update behavior before building or publishing a carried package.
---

# Package version safety

Run before the first build and repeat immediately before publication. Follow
the gates in [`docs/ENGINEERING-PROCESS.md`](../../../docs/ENGINEERING-PROCESS.md).

Record these inputs:

```text
source_package:
target_series:
archive_source_version:
archive_binary_version:
candidate_source_version:
candidate_binary_version:
security_and_update_versions:
newer_series_or_Debian_versions:
candidate_source_commit:
```

Check the exact versions in the target archive, updates/security pockets,
proposed pocket where relevant, development series, Debian, and the release
that contains the candidate fix. Use `rmadison` and source changelogs/history
for discovery, `dpkg --compare-versions` for Debian version ordering, and
`apt-cache policy` against the actual configured target repositories to see
which binary apt will select. Do not infer installability from a suffix or
from a successful `dpkg -i`.

Return exactly one result:

```text
SAFE
UNSAFE
REPLACES_SECURITY_UPDATE
BLOCKS_FUTURE_UPDATE
UNKNOWN
```

Only `SAFE` passes. Use `UNSAFE` if the package cannot be installed or the
candidate does not select the intended source/binaries; use
`REPLACES_SECURITY_UPDATE` if the candidate is older than a relevant security
or update package; use `BLOCKS_FUTURE_UPDATE` if archive version ordering would
prevent the intended future Ubuntu update; use `UNKNOWN` if the version set or
repository candidate cannot be established. Stop on every result except
`SAFE` and explain the measured comparison. Re-run the check after rebuilding
if the candidate version or source changes.
