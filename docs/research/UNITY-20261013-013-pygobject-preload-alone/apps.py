#!/usr/bin/python3
# apps.py 3|4 - a minimal PyGObject window with GTK 3 or GTK 4, the smallest program that starts the way any
# PyGObject application does: "import gi", a GLib main loop, one window. Prints "window shown" once it is mapped.
import sys
import gi

v = sys.argv[1]
gi.require_version("Gtk", v + ".0")
from gi.repository import GLib, Gtk  # noqa: E402

GLib.timeout_add_seconds(1, lambda: print("window shown", flush=True) and False)
if v == "3":
    w = Gtk.Window(title="b1313 gtk3")
    w.connect("destroy", Gtk.main_quit)
    w.show_all()
    Gtk.main()
else:
    app = Gtk.Application(application_id="org.unitydistro.B1313")
    app.connect("activate", lambda a: Gtk.ApplicationWindow(application=a, title="b1313 gtk4").present())
    app.run([])
