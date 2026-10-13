#!/usr/bin/env python3
"""shape.py VAR.txt... - per audit file and application: the shape of the exported menubar as audit.py
prints it. "holder": the top level is submenus only ("-" lines at the first item indent), and how many;
"flat": the top level has plain items, and how many top-level entries in all; "-": no menu.
Also counts labels that still carry a mnemonic underscore. Apostrophe is left out, as in count.py."""
import re
import sys

ITEM = re.compile(r'^( +)(ok|disabled|MISSING|-)\s+(\S*)\s*(.*)$')


def blocks(text):
    out, name, lines = {}, None, []
    for line in text.splitlines():
        m = re.match(r'=+ (\S+)', line)
        if m:
            if name:
                out[name] = lines
            name, lines = m.group(1), []
        elif name:
            lines.append(line)
    if name:
        out[name] = lines
    return out


def depth(m):
    # audit.py prints "  " * depth, then the status padded to 9 and a space; a submenu line has an empty
    # status, so its "-" sits 10 columns further; breadth-any.sh adds two spaces in front of every line
    indent = len(m.group(1)) - 2
    return (indent - 10) // 2 if m.group(2) == '-' else indent // 2


def shape(lines):
    items = [ITEM.match(l) for l in lines]
    items = [m for m in items if m]
    if not items:
        return '-', 0, 0
    tops = [m for m in items if depth(m) == 0]
    under = sum(1 for m in items if '_' in m.group(4))
    if all(m.group(2) == '-' for m in tops):
        return 'holder', len(tops), under
    return 'flat', len(tops), under


files = sys.argv[1:]
shapes = {}
for path in files:
    b = blocks(open(path).read())
    b.pop('apostrophe', None)
    shapes[path] = {a: shape(v) for a, v in b.items()}
apps = sorted(set().union(*[set(s) for s in shapes.values()]))
print('app'.ljust(22) + ''.join(p.split('/')[-1].replace('var-', '').replace('.txt', '').ljust(16) for p in files))
for a in apps:
    print(a.ljust(22) + ''.join(
        (f"{shapes[p][a][0]} {shapes[p][a][1]}" if a in shapes[p] else 'absent').ljust(16) for p in files))
for p in files:
    s = shapes[p].values()
    kinds = {k: sum(1 for x in s if x[0] == k) for k in ('holder', 'flat', '-')}
    print(f"{p.split('/')[-1]}: holder {kinds['holder']}, flat {kinds['flat']}, no menu {kinds['-']}, "
          f"labels with a mnemonic underscore {sum(x[2] for x in s)}")
