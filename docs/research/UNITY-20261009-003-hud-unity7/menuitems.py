#!/usr/bin/env python3
"""menuitems.py BUS MENUBAR_PATH APP_PATH WIN_PATH LABEL - read an application's exported GMenu (org.gtk.Menus) and
print every item whose label (underscores removed) contains LABEL, with its action and target; then describe the
action (org.gtk.Actions.Describe) on the application's group for "app." actions and the window's for "win."
actions: enabled, parameter type, state."""
import sys
from gi.repository import Gio, GLib

bus_name, path, app_path, win_path, want = sys.argv[1:6]
bus = Gio.bus_get_sync(Gio.BusType.SESSION)
groups = list(range(0, 200))
res = bus.call_sync(bus_name, path, 'org.gtk.Menus', 'Start', GLib.Variant('(au)', (groups,)),
                    GLib.VariantType('(a(uuaa{sv}))'), 0, 5000, None).unpack()[0]
found = []
for group, menu, items in res:
    for it in items:
        label = it.get('label', '')
        if want in label.replace('_', ''):
            found.append(it)
            print(f"item group {group} menu {menu}: label {label!r} action {it.get('action')!r} "
                  f"target {it.get('target')!r}")
bus.call_sync(bus_name, path, 'org.gtk.Menus', 'End', GLib.Variant('(au)', (groups,)), None, 0, 5000, None)
for it in found:
    act = it.get('action')
    if not act or '.' not in act:
        continue
    prefix, name = act.split('.', 1)
    objpath = {'app': app_path, 'win': win_path}.get(prefix)
    if not objpath:
        print(f"  action {act}: prefix {prefix} has no known group path")
        continue
    try:
        enabled, ptype, state = bus.call_sync(bus_name, objpath, 'org.gtk.Actions', 'Describe',
                                              GLib.Variant('(s)', (name,)), None, 0, 5000, None).unpack()[0]
        print(f"  action {act} on {objpath}: enabled {enabled}, parameter type {ptype!r}, state {state!r}")
    except GLib.Error as e:
        print(f"  action {act} on {objpath}: Describe failed: {e.message}")
