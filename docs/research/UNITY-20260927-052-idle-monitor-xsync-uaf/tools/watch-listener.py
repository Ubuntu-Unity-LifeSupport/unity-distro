#!/usr/bin/env python3
# UNITY-20260927-052 (agent A): the client that STAYS. Adds a user-active
# watch and an idle watch (MSEC) on the Core monitor, listens for WatchFired
# for SECONDS and prints every firing with its time. Used to check that the
# remaining clients' watches keep working after other clients left.
# usage: watch-listener.py MSEC SECONDS
import sys, time
from gi.repository import Gio, GLib
msec, secs = int(sys.argv[1]), float(sys.argv[2])
bus = Gio.bus_get_sync(Gio.BusType.SESSION)
N, P, I = "org.gnome.Mutter.IdleMonitor", "/org/gnome/Mutter/IdleMonitor/Core", "org.gnome.Mutter.IdleMonitor"
t0 = time.time()
def fired(conn, sender, path, iface, signal, params, data):
    wid = params.unpack()[0]
    print("%6.1fs WatchFired id=%d (%s)" % (time.time() - t0, wid, names.get(wid, "?")), flush=True)
bus.signal_subscribe(None, I, "WatchFired", P, None, 0, fired, None)
names = {}
a = bus.call_sync(N, P, I, "AddUserActiveWatch", None, GLib.VariantType("(u)"), 0, 5000, None).unpack()[0]
names[a] = "user-active"
b = bus.call_sync(N, P, I, "AddIdleWatch", GLib.Variant("(t)", (msec,)), GLib.VariantType("(u)"), 0, 5000, None).unpack()[0]
names[b] = "idle %d ms" % msec
print("listener %s: user-active id=%d, idle id=%d" % (bus.get_unique_name(), a, b), flush=True)
loop = GLib.MainLoop(); GLib.timeout_add(int(secs * 1000), loop.quit); loop.run()
