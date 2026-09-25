#!/usr/bin/python3
"""menuapp.py - a GTK3 window with a menu bar that, every 3 s, builds and shows
another menu bar window, so the (hijacked) GtkMenuBar class keeps being used
after the gtk-modules setting changes. Prints the loaded appmenu module state."""
import gi, sys
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

def mapped():
    return any("appmenu-gtk-module" in l for l in open("/proc/self/maps"))

def window(n):
    w = Gtk.Window(title="menuapp %d" % n)
    mb = Gtk.MenuBar()
    item = Gtk.MenuItem(label="File")
    menu = Gtk.Menu(); menu.append(Gtk.MenuItem(label="Quit %d" % n))
    item.set_submenu(menu); mb.append(item)
    w.add(mb); w.show_all()
    return w

n = [0]
def tick():
    n[0] += 1
    window(n[0])
    print("tick %d gtk-modules=%r module mapped=%s" % (
        n[0], Gtk.Settings.get_default().props.gtk_modules, mapped()), flush=True)
    return True

window(0)
print("start gtk-modules=%r module mapped=%s" % (Gtk.Settings.get_default().props.gtk_modules, mapped()), flush=True)
GLib.timeout_add_seconds(3, tick)
GLib.timeout_add_seconds(int(sys.argv[1]) if len(sys.argv) > 1 else 20, Gtk.main_quit)
Gtk.main()
print("EXITED CLEANLY", flush=True)
