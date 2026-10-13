#!/usr/bin/env python3
"""Generates dpkg_version_order.json: pairs of Debian versions with the verdict of
`dpkg --compare-versions` on this machine (lt / eq / gt). The signer's pure
version comparison (signer_core.version_compare, permission model phase 5) is
tested against this table. Rerun on builder when the table is extended.

  python3 scripts/tests/data/make_dpkg_version_order.py > scripts/tests/data/dpkg_version_order.json
"""
import itertools
import json
import subprocess

VERSIONS = [
    "1.0", "1.0+unity1", "1.0+unity2", "1.0+unity10", "1.0-1", "1.0-1ubuntu1", "1.0-1ubuntu1+unity1",
    "1.0-1ubuntu1+unity2", "1.0-1ubuntu2", "1.0-2", "1.0.1", "1.0.1-1", "1.0~rc1", "1.0~rc1+unity1", "1.0~beta",
    "1.0a", "1.0b", "1.1", "1.10", "1.9", "2.0", "1:1.0", "1:0.9", "2:1.0", "0:1.0", "1.0+dfsg-1", "1.0+dfsg-1+unity1",
    "1.0+really0.9", "7.7.0+26.04.20260101-0ubuntu1", "7.7.0+26.04.20260101-0ubuntu1+unity1",
    "7.7.0+26.04.20260101-0ubuntu1+unity2", "7.7.0+26.04.20260201-0ubuntu1", "7.7.0+26.04.20260101-0ubuntu2",
    "0.9.12.3+bzr1234-0ubuntu1", "0.9.12.3+bzr1235-0ubuntu1", "0.9.12.3+bzr1234-0ubuntu1+unity1",
    "1.0-1+b1", "1.0-1+b2", "1.0-1~bpo1", "1.0-1.1", "1.0-1.1+unity1", "3.36.0-1ubuntu1+unity3", "3.36.0-1ubuntu1+unity4",
    "1.0.", "1..0", "1.0-", "1.0+", "1.0~", "20260101", "20260102", "1e5", "1e4", "A", "a", "Z", "z", "1.0+UNITY1",
]


def dpkg(a, op, b):
    return subprocess.run(["dpkg", "--compare-versions", a, op, b], capture_output=True).returncode == 0


table = []
for a, b in itertools.product(VERSIONS, repeat=2):
    lt, eq, gt = dpkg(a, "lt", b), dpkg(a, "eq", b), dpkg(a, "gt", b)
    if lt + eq + gt != 1:
        continue  # dpkg rejects the version syntax; the signer refuses such versions by grammar
    table.append([a, b, "lt" if lt else "eq" if eq else "gt"])
print(json.dumps({"generated_with": subprocess.run(["dpkg", "--version"], capture_output=True, text=True).stdout.splitlines()[0],
                  "pairs": table}, indent=0))
