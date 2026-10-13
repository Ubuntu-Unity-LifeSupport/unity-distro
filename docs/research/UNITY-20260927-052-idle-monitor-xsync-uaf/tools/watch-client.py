#!/usr/bin/env python3
# UNITY-20260927-052 (agent A): an org.gnome.Mutter.IdleMonitor client that
# adds a watch on the Core monitor and exits WITHOUT RemoveWatch - what any
# client that quits or crashes does. unity-settings-daemon then sees the
# client's bus name vanish and runs name_vanished_callback.
# usage: watch-client.py [idle MSEC | active] [--keep SECONDS] [--remove]
# --remove: call RemoveWatch before exiting (the well-behaved client).
import sys, time
from gi.repository import Gio, GLib
kind = sys.argv[1] if len(sys.argv) > 1 else "active"
bus = Gio.bus_get_sync(Gio.BusType.SESSION)
path, iface = "/org/gnome/Mutter/IdleMonitor/Core", "org.gnome.Mutter.IdleMonitor"
if kind == "idle":
    r = bus.call_sync("org.gnome.Mutter.IdleMonitor", path, iface, "AddIdleWatch",
                      GLib.Variant("(t)", (int(sys.argv[2]),)), GLib.VariantType("(u)"), 0, 5000, None)
else:
    r = bus.call_sync("org.gnome.Mutter.IdleMonitor", path, iface, "AddUserActiveWatch",
                      None, GLib.VariantType("(u)"), 0, 5000, None)
wid = r.unpack()[0]
print("watch id %d from %s" % (wid, bus.get_unique_name()), flush=True)
if "--keep" in sys.argv:
    time.sleep(float(sys.argv[sys.argv.index("--keep") + 1]))
if "--remove" in sys.argv:
    bus.call_sync("org.gnome.Mutter.IdleMonitor", path, iface, "RemoveWatch",
                  GLib.Variant("(u)", (wid,)), None, 0, 5000, None)
    print("removed watch %d" % wid, flush=True)
