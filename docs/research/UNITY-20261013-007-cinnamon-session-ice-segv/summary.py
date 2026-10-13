#!/usr/bin/env python3
"""summary.py TRACE - per connection address in a bpftrace log from observe.sh: how many times it was accepted,
closed and freed, in order. A connection is fine if every accept is followed by exactly one close and at most one
free before the address is accepted again, and no close comes after a free of the same lifetime."""
import collections
import sys

events = []
for line in open(sys.argv[1], encoding='utf-8', errors='replace'):
    parts = line.split()
    if len(parts) == 3 and parts[1] in ('accept', 'close', 'free') and parts[0].isdigit():
        events.append((int(parts[0]), parts[1], parts[2]))

life = collections.defaultdict(list)    # address -> list of lifetimes, each a list of events
for t, kind, addr in events:
    if kind == 'accept' or not life[addr]:
        life[addr].append([])
    life[addr][-1].append(kind)

bad = 0
for addr, lifetimes in life.items():
    for lt in lifetimes:
        closes, frees = lt.count('close'), lt.count('free')
        after_free = 'free' in lt and 'close' in lt[lt.index('free') + 1:]
        ok = closes <= 1 and frees <= 1 and not after_free
        if not ok:
            bad += 1
        print(f'  {addr}: {" ".join(lt)}  -> closes {closes} frees {frees}{"" if ok else "  NOT OK"}')
print(f'events {len(events)}, connections {sum(len(v) for v in life.values())}, not ok {bad}')
