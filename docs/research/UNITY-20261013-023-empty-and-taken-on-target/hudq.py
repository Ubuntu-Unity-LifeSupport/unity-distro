#!/usr/bin/python3
# hudq.py QUERY - on the desktop, in the session's D-Bus: ask hud-service what the HUD shows for QUERY for the
# focused window (com.canonical.hud StartQuery, then CloseQuery), and print the target and every result's
# description, without markup.
import re
import sys

from gi.repository import Gio, GLib

bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
reply = bus.call_sync('com.canonical.hud', '/com/canonical/hud', 'com.canonical.hud', 'StartQuery',
                      GLib.Variant('(si)', (sys.argv[1], 10)), None, Gio.DBusCallFlags.NONE, 5000, None)
target, results, key = reply.unpack()
print(f'  HUD query "{sys.argv[1]}": target "{target}", {len(results)} result(s)')
for r in results:
    texts = [re.sub(r'<[^>]+>', '', x) for x in r if isinstance(x, str) and x]
    print('    ' + ' | '.join(texts[:3]))
bus.call_sync('com.canonical.hud', '/com/canonical/hud', 'com.canonical.hud', 'CloseQuery',
              GLib.Variant('(v)', (reply.get_child_value(2).get_variant(),)), None, Gio.DBusCallFlags.NONE, 5000, None)
