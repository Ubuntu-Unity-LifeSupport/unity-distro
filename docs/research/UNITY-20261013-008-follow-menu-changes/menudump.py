#!/usr/bin/python3
# menudump.py WINDOW-ID - read the menubar a GTK application window exports (_GTK_UNIQUE_BUS_NAME and
# _GTK_MENUBAR_OBJECT_PATH on the window) as a D-Bus client, the way the panel does: a GDBusMenuModel, walked
# recursively. Every submenu and section proxy is kept referenced while the walk runs, so its subscription is not
# ended before the reply arrives. Prints one line per item: indentation, label, action, and "(section)"/"(submenu)".
import subprocess
import sys

from gi.repository import Gio, GLib


def prop(win, name):
    out = subprocess.run(['xprop', '-id', win, name], capture_output=True, text=True).stdout
    return out.split('"')[1] if '"' in out else None


def spin(ms):
    end = GLib.get_monotonic_time() + ms * 1000
    ctx = GLib.MainContext.default()
    while GLib.get_monotonic_time() < end:
        ctx.iteration(False)


keep = []


def items(model):
    keep.append(model)
    n = model.get_n_items()
    for _ in range(40):          # up to 2 s for the subscription's reply
        if n > 0:
            break
        spin(50)
        n = model.get_n_items()
    spin(50)
    return model.get_n_items()


def walk(model, depth):
    for i in range(items(model)):
        label = model.get_item_attribute_value(i, 'label', GLib.VariantType.new('s'))
        action = model.get_item_attribute_value(i, 'action', GLib.VariantType.new('s'))
        target = model.get_item_attribute_value(i, 'target', None)
        line = '  ' * depth + (label.get_string() if label else '(no label)')
        if action:
            line += f'  [{action.get_string()}{"(" + target.print_(False) + ")" if target else ""}]'
        print(line)
        for kind in ('section', 'submenu'):
            sub = model.get_item_link(i, kind)
            if sub is not None:
                if kind == 'section':
                    print('  ' * (depth + 1) + '(section)')
                walk(sub, depth + 2 if kind == 'section' else depth + 1)


win = sys.argv[1]
bus_name, path = prop(win, '_GTK_UNIQUE_BUS_NAME'), prop(win, '_GTK_MENUBAR_OBJECT_PATH')
print(f'window {win}: {bus_name} {path}')
if bus_name and path:
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    walk(Gio.DBusMenuModel.get(bus, bus_name, path), 0)
