#!/usr/bin/env python3
"""count.py VAR.txt... - per audit file: applications that export a menu, and
items that cannot be activated (MISSING), as research/nocsd-reply2 counted
them. With EPI=FILE:SECTION, the epiphany block is taken from that section of
a separate run (### SECTION headers), for runs where a leftover epiphany took
over the launch. Apostrophe opens no window and is not counted, as before."""
import os
import re
import sys


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


def exported(lines):
    return any(re.match(r'\s+(ok|disabled|MISSING)\s', l) for l in lines)


def missing(lines):
    return [l.split()[1] for l in lines if re.match(r'\s+MISSING\s', l)]


epi = None
if os.environ.get('EPI'):
    path, section = os.environ['EPI'].rsplit(':', 1)
    text = open(path).read()
    part = text.split('### ' + section + '\n', 1)[1].split('\n###', 1)[0]
    epi = blocks(part).get('epiphany')

for path in sys.argv[1:]:
    b = blocks(open(path).read())
    b.pop('apostrophe', None)
    if epi is not None:
        b['epiphany'] = epi
    apps = sorted(b)
    exp = [a for a in apps if exported(b[a])]
    miss = {a: missing(b[a]) for a in apps if missing(b[a])}
    exited = [a for a in apps if any(l.strip() == 'EXITED' for l in b[a])]
    print(f"{os.path.basename(path)}: {len(apps)} apps, export a menu {len(exp)}, "
          f"MISSING {sum(len(v) for v in miss.values())} in {len(miss)} apps, EXITED {exited}")
    print(f"  no menu: {[a for a in apps if a not in exp]}")
    for a, v in miss.items():
        print(f"  MISSING {a}: {v}")
