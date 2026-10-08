#!/usr/bin/env python3
"""ids.py - every .desktop file in the XDG applications directories, with the id window-stack-bridge gives it
(QFileInfo::baseName(): the name up to the FIRST dot) and the full desktop-file id (completeBaseName: up to the
last dot). Prints the bridge ids that more than one application shares (key collisions), and which of those
applications have a menu bar the HUD could index (they are shown, not filtered: the HUD also offers window
actions for every application)."""
import collections
import configparser
import os

dirs = [os.path.expanduser('~/.local/share')] + os.environ.get('XDG_DATA_DIRS', '/usr/local/share:/usr/share').split(':')
seen = {}
for d in dirs:
    a = os.path.join(d, 'applications')
    if not os.path.isdir(a):
        continue
    for root, _, files in os.walk(a):
        for f in files:
            if not f.endswith('.desktop') or f in seen:
                continue
            p = os.path.join(root, f)
            c = configparser.ConfigParser(interpolation=None, strict=False)
            try:
                c.read(p, encoding='utf-8')
                e = c['Desktop Entry']
            except Exception:
                continue
            if e.get('Type', 'Application') != 'Application':
                continue
            hidden = e.get('NoDisplay', 'false') == 'true' or e.get('Hidden', 'false') == 'true'
            seen[f] = (p, e.get('Name', ''), hidden)
groups = collections.defaultdict(list)
for f, (p, name, hidden) in seen.items():
    groups[f.split('.')[0]].append((f[:-len('.desktop')], name, hidden))
print('applications: %d; with a dot before .desktop: %d' % (len(seen), sum(1 for f in seen if f[:-8].count('.'))))
print('bridge ids shared by more than one application:')
for k in sorted(groups, key=lambda k: -len(groups[k])):
    if len(groups[k]) > 1:
        print('  %r: %d -> %s' % (k, len(groups[k]), ', '.join('%s (%s)%s' % (i, n, ' [NoDisplay]' if h else '') for i, n, h in sorted(groups[k]))))
print('cut but alone under their bridge id:')
for k in sorted(groups):
    if len(groups[k]) == 1 and groups[k][0][0] != k:
        i, n, h = groups[k][0]
        print('  %r <- %s (%s)%s' % (k, i, n, ' [NoDisplay]' if h else ''))
