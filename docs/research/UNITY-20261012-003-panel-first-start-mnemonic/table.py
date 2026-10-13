#!/usr/bin/env python3
"""table.py LOG... - the results table from trial.sh logs (logs/04, logs/05): for every attempt the times of
_NET_ACTIVE_WINDOW becoming the application's window, unity-panel-service's first org.gtk.Menus Start to the
application, compiz's first SyncOne of libappmenu.so after that (when unity takes the entries), compiz's ShowEntry, the panel service's EntryActivated with a non-empty entry, and the popup map (the
first popwatch line with more than 0 visible windows, and the line where the count reaches its maximum)."""
import re
import sys


def secs(t):
    h, m, s = t.split(':')
    return int(h) * 3600 + int(m) * 60 + float(s)


for path in sys.argv[1:]:
    text = open(path, encoding='utf-8').read()
    for block in re.split(r'^#### ', text, flags=re.M)[1:]:
        tag = block.split('\n', 1)[0].strip()
        audit = 'audit.py runs' in block
        win = re.search(r'window (\d+) mapped', block)
        win = int(win.group(1)) if win else None
        act = [secs(t) for t, w in re.findall(r'^\s+(\S+) _NET_ACTIVE_WINDOW\(WINDOW\): window id # (0x[0-9a-f]+)', block, re.M)
               if win is not None and int(w, 16) == win]
        start = re.search(r'^\s+(\S+) call\s+\S+\(unity-panel-ser\) -> \S+\((?!unity)[^)]*\) Start', block, re.M)
        syncs = [secs(t) for t in re.findall(r'^\s+(\S+) call\s+\S+\(compiz\) -> \S+ SyncOne \| string "libappmenu.so"', block, re.M)]
        show = re.findall(r'^\s+(\S+) call\s+\S+\(compiz\) -> \S+ ShowEntry', block, re.M)
        ent = re.findall(r'^\s+(\S+) signal \S+\(unity-panel-ser\) -> \S+ EntryActivated \| string "Unity', block, re.M)
        pop = [(secs(t), int(n)) for t, n in re.findall(r'^\s+(\S+) panel-service visible windows (\d+)', block, re.M)]
        first = next((t for t, n in pop if n > 0), None)
        full = next((t for t, n in pop if n == max(c for _, c in pop)), None) if pop else None
        s = secs(show[0]) if show else None
        row = [tag, 'audit' if audit else 'noaudit', f'ShowEntry x{len(show)}', f'EntryActivated x{len(ent)}']
        if act and start:
            row.append(f'active->Start {secs(start.group(1)) - act[0]:.3f}s')
        after = [t for t in syncs if act and t >= act[0]]
        if after:
            row.append(f'active->SyncOne {after[0] - act[0]:.3f}s')
        if s is not None and ent:
            row.append(f'->EntryActivated {(secs(ent[0]) - s) * 1000:.0f}ms')
        if s is not None and first is not None:
            row.append(f'->popup first {first - s:.3f}s, full {full - s:.3f}s')
        print('  '.join(row))
