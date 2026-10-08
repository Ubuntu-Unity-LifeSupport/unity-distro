#!/usr/bin/env python3
"""frequent.py - open an empty HUD query (CreateQuery ""), the way the HUD does when it is opened before typing,
and print its first results: the "most used" list for the focused application."""
import gi
gi.require_version('Dee', '1.0')
from gi.repository import Dee, Gio, GLib

bus = Gio.bus_get_sync(Gio.BusType.SESSION)
path, results, _, _ = bus.call_sync('com.canonical.hud', '/com/canonical/hud', 'com.canonical.hud', 'CreateQuery',
                                    GLib.Variant('(s)', ('',)), None, 0, 5000, None).unpack()
model = Dee.SharedModel.new(results)
loop = GLib.MainLoop()
GLib.timeout_add(2000, loop.quit)
loop.run()
names = []
it = model.get_first_iter()
while not model.is_last(it) and len(names) < 5:
    row = model.get_row(it)
    names.append("%s %s" % (row[1], row[3]))
    it = model.next(it)
print("empty query, %d rows, first: %s" % (model.get_n_rows(), " | ".join(names)))
bus.call_sync('com.canonical.hud', path, 'com.canonical.hud.query', 'CloseQuery', None, None, 0, 5000, None)
