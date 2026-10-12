#!/usr/bin/env python3
"""hudexec.py QUERY [--key-string | --key-zero] - the legacy HUD path Unity 7 uses: StartQuery(QUERY, 5), print
the suggestions, then ExecuteQuery for the first suggestion whose label contains QUERY (underscores and <b> tags
removed) with its own key, the way Unity does. --key-string sends a string key instead (UNITY-20261009-003, the
non-integer key); --key-zero sends uint64 0 whatever the suggestions are (for the no-window case). Then CloseQuery."""
import sys
import time
from gi.repository import Gio, GLib

query = sys.argv[1]
mode = sys.argv[2] if len(sys.argv) > 2 else ''
bus = Gio.bus_get_sync(Gio.BusType.SESSION)
H = ('com.canonical.hud', '/com/canonical/hud', 'com.canonical.hud')


def call(method, args, reply=None):
    return bus.call_sync(*H, method, args, reply, 0, 5000, None)


target, suggestions, querykey = call('StartQuery', GLib.Variant('(si)', (query, 5))).unpack()
print(f"StartQuery {query!r}: target {target!r}, {len(suggestions)} suggestions, querykey {querykey!r}")
key = None
for s in suggestions:
    name = s[0].replace('<b>', '').replace('</b>', '')
    print(f"  {name!r} {s[1]!r} key {s[5]!r}")
    if key is None and query and query in name.replace('_', ''):
        key = s[5]
if mode == '--key-string':
    item = GLib.Variant('s', 'not-a-number')
elif mode == '--key-struct':
    # a key no QVariant conversion turns into a number (a D-Bus structure arrives as QDBusArgument)
    item = GLib.Variant('(ss)', ('not', 'a-number'))
elif mode == '--key-zero':
    item = GLib.Variant('t', 0)
elif key is None:
    sys.exit('no matching suggestion')
else:
    item = GLib.Variant('t', key)
print(f"ExecuteQuery with key {item}")
try:
    call('ExecuteQuery', GLib.Variant('(vu)', (item, int(time.time()))))
    print("  ExecuteQuery returned")
except GLib.Error as e:
    print(f"  ExecuteQuery error: {e.message}")
try:
    call('CloseQuery', GLib.Variant('(v)', (GLib.Variant('s', ''),)))
    print("  CloseQuery returned")
except GLib.Error as e:
    print(f"  CloseQuery error: {e.message}")
