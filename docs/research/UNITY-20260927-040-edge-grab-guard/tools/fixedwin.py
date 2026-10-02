#!/usr/bin/env python3
# UNITY-20260927-040 (agent A): a non-resizable (so non-maximizable) window,
# "fixedwin", 300x200 at 700,450: its title bar drag goes straight to
# Edge::ButtonDownEvent (GrabEdge, no grab-wait timer).
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
w = Gtk.Window(title="fixedwin"); w.set_default_size(300, 200); w.set_resizable(False); w.move(700, 450)
w.connect("destroy", Gtk.main_quit); w.add(Gtk.Label(label="fixedwin")); w.show_all(); Gtk.main()
