#!/usr/bin/python3
"""mnemo.py - a GTK4 application with its own menubar carrying Latin mnemonics (_File, _Edit, _Help), so that Alt+F
on the Unity panel can be tested with the guest's gb/us layouts. Each activated item prints a line on stdout."""
import sys

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gio, Gtk  # noqa: E402

MENUS = (("_File", (("_New", "new"), ("_Open", "open"), ("_Quit", "quit"))),
         ("_Edit", (("_Copy", "copy"), ("_Paste", "paste"))),
         ("_Help", (("_About", "about"),)))


class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.unitydistro.MnemoTest", flags=Gio.ApplicationFlags.NON_UNIQUE)

    def do_startup(self):
        Gtk.Application.do_startup(self)
        bar = Gio.Menu()
        for top, items in MENUS:
            sub = Gio.Menu()
            for label, name in items:
                sub.append(label, "app." + name)
                action = Gio.SimpleAction.new(name, None)
                action.connect("activate", lambda a, p, n=name: print("activated", n, flush=True))
                self.add_action(action)
            bar.append_submenu(top, sub)
        self.set_menubar(bar)

    def do_activate(self):
        win = Gtk.ApplicationWindow(application=self, title="MnemoTest")
        win.set_show_menubar(True)
        win.set_default_size(400, 300)
        win.present()


sys.exit(App().run(sys.argv))
