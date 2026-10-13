#!/usr/bin/env python3
"""usage.py QUERY - execute the first HUD result for QUERY (CreateQuery, the first row of the Dee results model,
ExecuteCommand), the way the HUD does when the user presses Enter, then print hud's usage table
(~/.cache/indicator-appmenu/hud-usage-log.sqlite): under which application id the use was recorded."""
import os
import sqlite3
import sys
import time

import gi
gi.require_version('Dee', '1.0')
from gi.repository import Dee, Gio, GLib

bus = Gio.bus_get_sync(Gio.BusType.SESSION)
path, results, _, _ = bus.call_sync('com.canonical.hud', '/com/canonical/hud', 'com.canonical.hud', 'CreateQuery',
                                    GLib.Variant('(s)', (sys.argv[1],)), None, 0, 5000, None).unpack()
model = Dee.SharedModel.new(results)
loop = GLib.MainLoop()
GLib.timeout_add(2000, loop.quit)
loop.run()
it = model.get_first_iter()
if model.is_last(it):
    sys.exit("no results")
row = model.get_row(it)
print("first result:", [str(row[i])[:60] for i in range(3)])
bus.call_sync('com.canonical.hud', path, 'com.canonical.hud.query', 'ExecuteCommand',
              GLib.Variant('(vu)', (GLib.Variant('t', int(row[0])), int(time.time()))), None, 0, 5000, None)
bus.call_sync('com.canonical.hud', path, 'com.canonical.hud.query', 'CloseQuery', None, None, 0, 5000, None)
time.sleep(2)
db = sqlite3.connect(os.path.expanduser('~/.cache/indicator-appmenu/hud-usage-log.sqlite'))
print("usage rows (application, entry, count):",
      db.execute("select application, entry, count(*) from usage group by application, entry").fetchall())
