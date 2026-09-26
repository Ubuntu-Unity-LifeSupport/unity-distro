#!/usr/bin/env python3
# A small window that records every button press it receives, to tell whether a
# click from a real input device reaches applications (known issue #3, agent A).
# usage: clicksensor.py [logfile]   window "clicksensor" at 100,100 200x150
import sys, time, gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
log = open(sys.argv[1] if len(sys.argv) > 1 else "/tmp/clicks.log", "a", buffering=1)
w = Gtk.Window(title="clicksensor"); w.set_default_size(200, 150); w.move(100, 100)
w.set_keep_above(True)
def press(widget, ev):
    log.write("%.3f press %d %d %d\n" % (time.time(), ev.button, ev.x_root, ev.y_root)); return False
w.connect("button-press-event", press); w.connect("destroy", Gtk.main_quit)
w.add(Gtk.Label(label="clicksensor")); w.show_all(); Gtk.main()
