#!/usr/bin/env python3
"""survey.py NAME PID - for one running application, read its windows' _GTK_* properties, walk every GMenu it
exports (org.gtk.Menus on the menubar and app-menu paths), and for every item with an action print one JSON line:
the app, the action, the target's GVariant type string (or null) and value, and the action's parameter type and
state type as its group describes them (org.gtk.Actions.Describe on the application or window group).
This is what hud's libqtgmenu imports for the HUD. The reply is walked with the GVariant API, so the type strings
are GLib's own ("s", "b", "(ss)", ...), not Python's."""
import json
import subprocess
import sys
from gi.repository import Gio, GLib

name, pid = sys.argv[1], sys.argv[2]
bus = Gio.bus_get_sync(Gio.BusType.SESSION)
wids = subprocess.run(['xdotool', 'search', '--onlyvisible', '--pid', pid], capture_output=True, text=True).stdout.split()
GROUPS = GLib.Variant('(au)', (list(range(0, 400)),))


def props(wid):
    out = subprocess.run(['xprop', '-id', wid], capture_output=True, text=True).stdout
    p = {}
    for line in out.splitlines():
        if line.startswith('_GTK_') and '=' in line:
            k, v = line.split('=', 1)
            p[k.split('(')[0].strip()] = v.strip().strip('"')
    return p


seen, items, groups_paths, describes = set(), [], {}, {}
for wid in wids:
    p = props(wid)
    busname = p.get('_GTK_UNIQUE_BUS_NAME')
    if not busname:
        continue
    for key, prefix in (('_GTK_APPLICATION_OBJECT_PATH', 'app'), ('_GTK_WINDOW_OBJECT_PATH', 'win')):
        if key in p:
            groups_paths.setdefault((busname, prefix), p[key])
    for key in ('_GTK_MENUBAR_OBJECT_PATH', '_GTK_APP_MENU_OBJECT_PATH'):
        path = p.get(key)
        if not path or (busname, path) in seen:
            continue
        seen.add((busname, path))
        try:
            reply = bus.call_sync(busname, path, 'org.gtk.Menus', 'Start', GROUPS,
                                  GLib.VariantType('(a(uuaa{sv}))'), 0, 5000, None)
            bus.call_sync(busname, path, 'org.gtk.Menus', 'End', GROUPS, None, 0, 5000, None)
        except GLib.Error as e:
            print(json.dumps({'app': name, 'error': f'{key} {path}: {e.message[:100]}'}, ensure_ascii=False))
            continue
        arr = reply.get_child_value(0)
        for i in range(arr.n_children()):
            entries = arr.get_child_value(i).get_child_value(2)
            for j in range(entries.n_children()):
                entry = entries.get_child_value(j)
                action = entry.lookup_value('action', GLib.VariantType('s'))
                if action is None:
                    continue
                label = entry.lookup_value('label', GLib.VariantType('s'))
                target = entry.lookup_value('target', None)
                items.append({'app': name, 'bus': busname, 'menu': path,
                              'label': label.get_string() if label else '',
                              'action': action.get_string(),
                              'target_type': target.get_type_string() if target is not None else None,
                              'target': target.print_(False) if target is not None else None})


def describe(busname, action):
    if '.' not in action:
        return {'group': 'no prefix'}
    prefix, aname = action.split('.', 1)
    path = groups_paths.get((busname, prefix))
    if not path:
        return {'group': f'no exported {prefix} group'}
    k = (busname, path, aname)
    if k not in describes:
        try:
            r = bus.call_sync(busname, path, 'org.gtk.Actions', 'Describe', GLib.Variant('(s)', (aname,)),
                              None, 0, 5000, None).get_child_value(0)
            state = r.get_child_value(2)
            describes[k] = {'enabled': r.get_child_value(0).get_boolean(), 'param': r.get_child_value(1).get_string(),
                            'state_type': state.get_child_value(0).get_variant().get_type_string()
                            if state.n_children() else None}
        except GLib.Error as e:
            describes[k] = {'describe_error': e.message[:80]}
    return describes[k]


for it in items:
    it.update(describe(it['bus'], it['action']))
    print(json.dumps(it, ensure_ascii=False))
print(json.dumps({'app': name, 'summary': True, 'windows': len(wids), 'menus': sorted(p for _, p in seen),
                  'items': len(items)}, ensure_ascii=False))
