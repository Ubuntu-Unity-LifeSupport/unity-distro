#!/usr/bin/env python3
"""analyze.py survey.jsonl - the reach of UNITY-20261009-004 from survey.py's output: per item, what +unity6's
TriggerAction does with it and what the revised design does (the decision table in the card), counted over all
applications; the target and parameter types seen; the applications with items +unity6 cannot run correctly."""
import collections
import json
import sys

rows = [json.loads(l) for l in open(sys.argv[1], encoding='utf-8') if l.strip()]
items = [r for r in rows if 'action' in r]
apps = [r for r in rows if r.get('summary')]
errors = [r for r in rows if 'error' in r]


def unity6(it):
    """What +unity6 QtGActionGroup::TriggerAction does (QtGActionGroup.cpp:75-103)."""
    p = it.get('param')
    if 'describe_error' in it or 'group' in it:
        return 'unknown action (activate with NULL if the group answers NULL)'
    if not p:
        return 'activate(NULL)'
    if p == 's':
        return 'activate(action name)'
    return 'nothing'


def unity7(it):
    """The revised design's table."""
    p, t = it.get('param'), it.get('target_type')
    if 'describe_error' in it or 'group' in it:
        return 'no activation (unknown)'
    if t is None:
        return {None: 'activate(NULL)', '': 'activate(NULL)', 's': 'activate(action name)'}.get(p, 'no activation')
    if not p:
        return 'no activation (target, no parameter)'
    return 'activate(target)' if t == p else 'no activation (wrong type)'


def correct(it):
    """Is +unity6's call what GTK would send? GTK: target if the types match, NULL if neither, else insensitive."""
    p, t = it.get('param') or None, it.get('target_type')
    u = unity6(it)
    if t is None and p is None:
        return u == 'activate(NULL)'
    if t is not None and p is not None and t == p:
        return False  # +unity6 never sends the target
    return u == 'nothing'  # GTK would not activate either


print(f"applications surveyed: {len(apps)}, with menu items: {sum(1 for a in apps if a['items'])}, "
      f"items with an action: {len(items)}, errors: {len(errors)}")
for e in errors:
    print(f"  error {e['app']}: {e['error']}")
print("\nitems by (target type, parameter type):")
c = collections.Counter((it.get('target_type'), it.get('param') or None) for it in items)
for (t, p), n in c.most_common():
    print(f"  target {t!s:8} parameter {p!s:8} {n:4}")
print("\n+unity6 -> revised design:")
c2 = collections.Counter((unity6(it), unity7(it)) for it in items)
for (a, b), n in c2.most_common():
    print(f"  {n:4}  {a:45} -> {b}")
bad = [it for it in items if not correct(it)]
print(f"\nitems +unity6 runs differently from GTK: {len(bad)} in "
      f"{len(set(it['app'] for it in bad))} applications")
per_app = collections.defaultdict(list)
for it in bad:
    per_app[it['app']].append(it)
for app, its in sorted(per_app.items()):
    ex = ', '.join(sorted(set(f"{i['action']}[{i.get('target')}]" for i in its))[:4])
    print(f"  {app}: {len(its)} ({ex})")
