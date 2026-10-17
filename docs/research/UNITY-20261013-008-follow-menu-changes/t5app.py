#!/usr/bin/python3
# t5app.py MODE - a GTK 4 application whose header-bar menu changes every 2 s, for target 5 (an open panel menu
# while the menu changes). Its menu, as the panel shows it under the "T5app" holder:
#     section: "Tick N", "Sibling"
#     "Sub" (a submenu): "Inner N", "Inner B"
#     "Outside N"
# MODE says what changes every 2 s (N counts up; each change prints a timestamped line):
#   a        "Tick N", a sibling in the menu that is open (open the holder's menu)
#   b        "Inner N", inside the submenu that is open (open "Sub")
#   c        "Outside N", outside the submenu that is open (open "Sub")
#   sub      "Sub" itself, relabelled "Sub N", with "Sub" open: the item whose submenu is open is replaced, so the
#            open submenu must collapse - the oracle that a collapse is seen at all
#   all      every item removed and added again (remove_all) with only "Tick N" new, the menu open: 0.13 must
#            replace one item
import sys
import time

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gio, GLib, Gtk

mode = sys.argv[1]
n = 0
app = Gtk.Application(application_id='org.unitydistro.T5app', flags=Gio.ApplicationFlags.NON_UNIQUE)


def noop(*a):
    pass


def item(menu, label):
    menu.append(label, 'app.noop')


def build():
    top, sec, sub = Gio.Menu(), Gio.Menu(), Gio.Menu()
    item(sec, f'Tick {n if mode in ("a", "all") else 0}')
    item(sec, 'Sibling')
    item(sub, f'Inner {n if mode == "b" else 0}')
    item(sub, 'Inner B')
    top.append_section(None, sec)
    top.append_submenu(f'Sub {n}' if mode == 'sub' and n else 'Sub', sub)
    item(top, f'Outside {n if mode == "c" else 0}')
    return top, sec, sub


def relabel(menu, i, label, submenu=None):
    menu.remove(i)
    if submenu is None:
        menu.insert(i, label, 'app.noop')
    else:
        menu.insert_submenu(i, label, submenu)


def tick():
    global n
    n += 1
    if mode == 'a':
        relabel(sec, 0, f'Tick {n}')
    elif mode == 'b':
        relabel(sub, 0, f'Inner {n}')
    elif mode == 'c':
        relabel(top, 2, f'Outside {n}')
    elif mode == 'sub':
        relabel(top, 1, f'Sub {n}', sub)
    elif mode == 'all':
        t, s, u = build()
        top.remove_all()
        for i in range(t.get_n_items()):
            top.append_item(Gio.MenuItem.new_from_model(t, i))
    print(f'{time.strftime("%H:%M:%S", time.gmtime())}.{int(time.time() * 1000) % 1000:03d} change {n} ({mode})',
          flush=True)
    return True


def activate(a):
    act = Gio.SimpleAction.new('noop', None)
    act.connect('activate', noop)
    a.add_action(act)
    win = Gtk.ApplicationWindow(application=a, title=f't5app {mode}')
    header = Gtk.HeaderBar()
    button = Gtk.MenuButton(menu_model=top)
    header.pack_end(button)
    win.set_titlebar(header)
    win.set_default_size(400, 250)
    win.present()
    GLib.timeout_add(2000, tick)


top, sec, sub = build()
app.connect('activate', activate)
app.run([sys.argv[0]])
