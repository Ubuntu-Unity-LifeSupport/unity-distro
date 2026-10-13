"""Compare two sha256sum-format lists: count changed/added/removed paths per
top-level directory. Usage: r047_listdiff.py BEFORE AFTER"""
import collections
import sys


def load(p):
    return {line[66:]: line[:64] for line in open(p).read().splitlines() if line}


a, b = load(sys.argv[1]), load(sys.argv[2])
kinds = collections.Counter()
for path in set(a) | set(b):
    top = path.split("/", 1)[0]
    if path not in a:
        kinds[(top, "added")] += 1
    elif path not in b:
        kinds[(top, "removed")] += 1
    elif a[path] != b[path]:
        kinds[(top, "changed")] += 1
print(f"before {len(a)} files, after {len(b)} files")
for (top, kind), n in sorted(kinds.items()):
    print(f"  {top}/: {n} {kind}")
print("pool/ unchanged:", not any(top == "pool" for top, _ in kinds))
