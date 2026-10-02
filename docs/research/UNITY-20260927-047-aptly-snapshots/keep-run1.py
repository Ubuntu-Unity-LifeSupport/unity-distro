#!/usr/bin/env python3
"""UNITY-20260927-047, repeat of phase R (2026-09-29): move everything the
first preparation and run 1 left in the rehearsal root into ROOT/run1/,
inside the same root (May: keep them). Moves only, deletes nothing, runs no
aptly, does not touch the live repository. Prints what moved where."""

import os
from pathlib import Path
import sys

ROOT = Path("/var/tmp/" + "aptly-rehearsal")
KEEP = ROOT / "run1"
EXPECTED = {"aptly.conf", "incoming", "state", "backup-r4", "backup-r4.sha256", "aside-r8b"}

entries = set(os.listdir(ROOT))
if entries - EXPECTED - {"run1"}:
    sys.exit(f"unexpected entries in {ROOT}: {sorted(entries - EXPECTED - {'run1'})}")
if KEEP.exists():
    sys.exit(f"{KEEP} exists already; not moving anything")
os.umask(0o077)
KEEP.mkdir(mode=0o700)
for name in sorted(entries & EXPECTED):
    os.rename(ROOT / name, KEEP / name)
    print(f"moved {ROOT / name} -> {KEEP / name}")
print(f"{ROOT} now: {sorted(os.listdir(ROOT))}; {KEEP}: {sorted(os.listdir(KEEP))}")
