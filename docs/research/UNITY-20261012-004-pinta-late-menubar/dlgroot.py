#!/usr/bin/python3
# dlgroot.py - where an AdwDialog presented over an AdwApplicationWindow ends up: inside the window, or in a toplevel
# of its own (as gtk-nocsd may make it). Prints the type of the dialog button's root and whether it is the window.
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gio, GLib, Gtk  # noqa: E402
gi.require_version('Adw', '1')
from gi.repository import Adw  # noqa: E402


def spin(ms):
    end = GLib.get_monotonic_time() + ms * 1000
    while GLib.get_monotonic_time() < end:
        GLib.MainContext.default().iteration(False)


def run(app):
    win = Adw.ApplicationWindow(application=app)
    win.set_content(Adw.ToolbarView())
    win.present()
    spin(300)
    dialog = Adw.Dialog()
    view = Adw.ToolbarView()
    header = Adw.HeaderBar()
    b = Gtk.MenuButton()
    header.pack_end(b)
    view.add_top_bar(header)
    dialog.set_child(view)
    dialog.present(win)
    spin(800)
    root = b.get_root()
    print(f'button mapped={b.get_mapped()} root={type(root).__name__} root-is-window={root is win}', flush=True)
    app.quit()


app = Adw.Application(application_id='org.unitydistro.DlgRoot', flags=Gio.ApplicationFlags.NON_UNIQUE)
app.connect('activate', run)
app.run([])
