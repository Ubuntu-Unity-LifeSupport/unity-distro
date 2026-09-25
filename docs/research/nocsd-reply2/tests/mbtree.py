import gi, sys
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio, GLib
app = Gtk.Application(application_id="org.unitydistro.MbTree")
def walk(w, d=0):
    out = []
    c = w.get_first_child()
    while c:
        out.append("  " * d + type(c).__name__ + ("" if c.get_visible() else " (hidden)"))
        out += walk(c, d + 1)
        c = c.get_next_sibling()
    return out
def act(a):
    m = Gio.Menu(); f = Gio.Menu(); f.append("Quit", "app.quit"); m.append_submenu("File", f)
    a.set_menubar(m)
    w = Gtk.ApplicationWindow(application=a); w.present()
    def dump():
        print("shell-shows-menubar", Gtk.Settings.get_default().props.gtk_shell_shows_menubar, "show-menubar", w.get_show_menubar())
        print("\n".join(walk(w))); a.quit(); return False
    GLib.timeout_add(1500, dump)
app.connect("activate", act); app.run(None)
