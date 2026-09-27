#!/usr/bin/env python3
# Take org.gnome.Mutter.IdleMonitor from unity-settings-daemon (it owns it with
# ALLOW_REPLACEMENT), hold it for a moment and give it back: the same
# lost-then-acquired sequence two racing instances produce at login.
import gi, sys
from gi.repository import Gio, GLib
hold = float(sys.argv[1]) if len(sys.argv) > 1 else 2
loop = GLib.MainLoop()
def acquired(conn, name):
    print("stolen", name, flush=True)
    GLib.timeout_add(int(hold * 1000), lambda: (Gio.bus_unown_name(oid), print("released", flush=True), GLib.timeout_add(500, loop.quit))[-1] and False)
oid = Gio.bus_own_name(Gio.BusType.SESSION, "org.gnome.Mutter.IdleMonitor",
                       Gio.BusNameOwnerFlags.REPLACE, None, acquired, lambda c, n: print("could not take", n, flush=True))
GLib.timeout_add(10000, loop.quit)
loop.run()
