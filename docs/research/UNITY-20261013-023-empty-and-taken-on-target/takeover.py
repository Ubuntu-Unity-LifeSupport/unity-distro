#!/usr/bin/python3
# takeover.py - design test 5 of UNITY-20261012-004 on a desktop: a GTK4 application whose window has a header bar
# and no menu at realize (so unity-gtk4-menu 0.12 sets its empty menubar and the window waits), and which sets a
# menubar of its own DELAY seconds after the window is presented: _File (New, Quit), _Edit (Copy), _Help (About).
# Prints the time it set its menubar. The window stays open until it is closed.
import sys
import time

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gio, GLib, Gtk  # noqa: E402

delay = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0


def own_menubar():
    bar = Gio.Menu()
    for label, items in (('_File', [('_New', 'app.new'), ('_Quit', 'app.quit')]),
                         ('_Edit', [('_Copy', 'app.copy')]),
                         ('_Help', [('_About', 'app.about')])):
        sub = Gio.Menu()
        for text, action in items:
            sub.append(text, action)
        bar.append_submenu(label, sub)
    return bar


def take_over(app):
    app.set_menubar(own_menubar())
    print(f'{time.strftime("%H:%M:%S", time.gmtime())}Z the application set its own menubar', flush=True)
    return False


def activate(app):
    for name in ('new', 'quit', 'copy', 'about'):
        action = Gio.SimpleAction.new(name, None)
        action.connect('activate', lambda a, p, n=name: print(f'ACTIVATED app.{n}', flush=True))
        app.add_action(action)
    win = Gtk.ApplicationWindow(application=app, title='takeover')
    win.set_titlebar(Gtk.HeaderBar())
    win.set_default_size(420, 240)
    win.present()
    print(f'{time.strftime("%H:%M:%S", time.gmtime())}Z window presented, own menubar in {delay} s', flush=True)
    GLib.timeout_add(int(delay * 1000), take_over, app)


app = Gtk.Application(application_id='org.unitydistro.TakeOver', flags=Gio.ApplicationFlags.NON_UNIQUE)
app.connect('activate', activate)
app.run([sys.argv[0]])
