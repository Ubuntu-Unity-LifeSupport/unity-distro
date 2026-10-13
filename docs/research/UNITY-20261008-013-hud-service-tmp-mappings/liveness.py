#!/usr/bin/env python3
"""liveness.py - UNITY-20261008-013: hud-service's deleted mappings with no query, with one HUD query open
(CreateQuery ""), and after its CloseQuery. A query builds a Matcher (three Tries): +3 while it is open; back to the
baseline after the close with the fix, +3 kept without it."""
import os
import subprocess
import time

import gi
gi.require_version('Dee', '1.0')
from gi.repository import Dee, Gio, GLib

pid = subprocess.run(["pgrep", "-x", "hud-service"], capture_output=True, text=True).stdout.split()[0]


def deleted():
    with open(f"/proc/{pid}/maps") as maps:
        return sum(1 for line in maps if line.rstrip("\n").endswith("(deleted)"))


def settle(ms=1500):
    loop = GLib.MainLoop()
    GLib.timeout_add(ms, loop.quit)
    loop.run()


bus = Gio.bus_get_sync(Gio.BusType.SESSION)
print("hud-service", pid, "baseline", deleted())
path, results, _, _ = bus.call_sync('com.canonical.hud', '/com/canonical/hud', 'com.canonical.hud', 'CreateQuery',
                                    GLib.Variant('(s)', ('',)), None, 0, 5000, None).unpack()
model = Dee.SharedModel.new(results)
settle()
print("query open", deleted())
bus.call_sync('com.canonical.hud', path, 'com.canonical.hud.query', 'CloseQuery', None, None, 0, 5000, None)
settle()
print("query closed", deleted())
