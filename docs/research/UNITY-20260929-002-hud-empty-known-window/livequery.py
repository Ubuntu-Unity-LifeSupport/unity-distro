#!/usr/bin/env python3
"""livequery.py QUERY OUT - UNITY-20260929-002 round 3: open a HUD query the way Unity's HUD client does
(com.canonical.hud CreateQuery, results in a Dee shared model), as soon as it is called, and read the live
results model at +0, +1, +2, +5, +10 and +20 s: the number of rows and how many mention "Файл" (the Writer File
menu). At +12 s it changes the query text through UpdateQuery and back, as typing would. Also prints the
unique bus names of hud-service and unity-panel-service, and one legacy StartQuery snapshot at +0."""
import sys
import time

import gi
gi.require_version('Dee', '1.0')
from gi.repository import Dee, Gio, GLib

query, out = sys.argv[1], sys.argv[2]
bus = Gio.bus_get_sync(Gio.BusType.SESSION)
log = open(out, 'w')
t0 = time.time()


def say(msg):
    log.write(f"{time.time() - t0:7.2f} {msg}\n")
    log.flush()


def owner(name):
    try:
        return bus.call_sync('org.freedesktop.DBus', '/org/freedesktop/DBus', 'org.freedesktop.DBus', 'GetNameOwner',
                             GLib.Variant('(s)', (name,)), GLib.VariantType('(s)'), 0, 2000, None).unpack()[0]
    except GLib.Error as e:
        return f"none ({e.message})"


say(f"before: hud-service {owner('com.canonical.hud')}; unity-panel-service {owner('com.canonical.Unity.Panel.Service.Desktop')}")
legacy = bus.call_sync('com.canonical.hud', '/com/canonical/hud', 'com.canonical.hud', 'StartQuery',
                       GLib.Variant('(si)', (query, 5)), None, 0, 5000, None).unpack()
say(f"legacy StartQuery: {len(legacy[1])} suggestions, {sum('Файл' in str(s) for s in legacy[1])} with Файл")
say(f"after: hud-service {owner('com.canonical.hud')}")
path, results, appstack, rev = bus.call_sync('com.canonical.hud', '/com/canonical/hud', 'com.canonical.hud', 'CreateQuery',
                                             GLib.Variant('(s)', (query,)), None, 0, 5000, None).unpack()
say(f"CreateQuery: {path} results={results} revision={rev}")
model = Dee.SharedModel.new(results)
loop = GLib.MainLoop()


def rows():
    n, f = 0, 0
    it = model.get_first_iter()
    while not model.is_last(it):
        n += 1
        if 'Файл' in ' '.join(str(v) for v in model.get_row(it)):
            f += 1
        it = model.next(it)
    return n, f


def check(label):
    n, f = rows()
    say(f"{label}: synchronized={model.is_synchronized()} rows={n} with Файл={f}")
    return False


def update(text):
    r = bus.call_sync('com.canonical.hud', path, 'com.canonical.hud.query', 'UpdateQuery',
                      GLib.Variant('(s)', (text,)), None, 0, 5000, None).unpack()
    say(f"UpdateQuery({text!r}) -> revision {r[0]}")
    return False


model.connect('row-added', lambda *a: None)
for sec in (0, 1, 2, 5, 10):
    GLib.timeout_add(int(sec * 1000) + 50, check, f"+{sec}s")
GLib.timeout_add(12000, update, query[:-1])
GLib.timeout_add(12500, update, query)
GLib.timeout_add(13500, check, "+13.5s after UpdateQuery back")
GLib.timeout_add(20000, check, "+20s")
GLib.timeout_add(20500, loop.quit)
loop.run()
bus.call_sync('com.canonical.hud', path, 'com.canonical.hud.query', 'CloseQuery', None, None, 0, 5000, None)
say("closed")
