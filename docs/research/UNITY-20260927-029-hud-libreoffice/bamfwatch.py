#!/usr/bin/env python3
"""bamfwatch.py - UNITY-20260927-029: log bamf's matcher ViewOpened/ViewClosed with
timestamps, and for every opened window ask Parents() and then the parent's
DesktopFile(), the same two calls window-stack-bridge makes. A plain
subscriber (a match rule on the matcher's signals), not a bus monitor."""
import time

from gi.repository import Gio, GLib

bus = Gio.bus_get_sync(Gio.BusType.SESSION)
T0 = time.monotonic()


def log(*a):
    print(f"{time.monotonic() - T0:9.3f}", *a, flush=True)


def call(path, iface, method):
    try:
        r = bus.call_sync("org.ayatana.bamf", path, iface, method, None, None,
                          Gio.DBusCallFlags.NONE, 2000, None)
        return r.unpack()[0]
    except GLib.Error as e:
        return f"ERROR {e.message.split(':')[-1].strip()[:80]}"


def on_signal(conn, sender, path, iface, member, params):
    view, kind = params.unpack()
    log(member, kind, view)
    if member == "ViewOpened" and kind == "window":
        parents = call(view, "org.ayatana.bamf.view", "Parents")
        log("   Parents ->", parents)
        if isinstance(parents, list) and parents:
            log("   DesktopFile ->", call(parents[0], "org.ayatana.bamf.application", "DesktopFile"))


bus.signal_subscribe("org.ayatana.bamf", "org.ayatana.bamf.matcher", None,
                     "/org/ayatana/bamf/matcher", None, Gio.DBusSignalFlags.NONE, on_signal)
GLib.MainLoop().run()
