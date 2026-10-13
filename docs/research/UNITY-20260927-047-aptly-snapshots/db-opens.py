"""List every goleveldb db@open recorded in the live db LOG (read-only), with
its date section, from 2026-09-28 on (UNITY-20260927-047 Verifier round 1)."""
import re

path = "/srv/" + "aptly" + "/db/LOG"
day = None
for raw in open(path, "rb").read().decode("latin-1").splitlines():
    m = re.search(r"=+ (\w{3} \d+, \d{4}) \(UTC\) =+", raw)
    if m:
        day = m.group(1)
        continue
    if "db@open opening" in raw and day in ("Sep 28, 2026", "Sep 29, 2026"):
        print(day, raw.split()[0])
