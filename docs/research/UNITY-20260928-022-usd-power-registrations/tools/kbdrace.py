#!/usr/bin/python3
# Verifier UNITY-20260928-022: keep N Keyboard.StepUp calls in flight to the
# power object for D seconds, count reply kinds. Usage: kbdrace.py N D [method]
import sys, time, collections
import gi
gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib
N, D = int(sys.argv[1]), float(sys.argv[2])
IFACE, METHOD = (sys.argv[3].rsplit(".", 1) if len(sys.argv) > 3
                 else ("org.gnome.SettingsDaemon.Power.Keyboard", "StepUp"))
bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
loop = GLib.MainLoop()
counts = collections.Counter()
end = time.monotonic() + D
inflight = [0]
def done(conn, res, _):
    inflight[0] -= 1
    try:
        conn.call_finish(res); counts["reply"] += 1
    except GLib.Error as e:
        m = e.message
        for k in ("not running", "UnknownMethod", "NoReply", "Timeout", "timed out",
                  "ServiceUnknown", "NameHasNoOwner", "Disconnected"):
            if k in m:
                counts[k] += 1
                if k in ("Timeout","timed out","NoReply") and counts[k] in (1,): print("  first %s at %s" % (k, time.strftime("%T")), flush=True)
                break
        else: counts["other:" + m[:80]] += 1
    fire()
def fire():
    if time.monotonic() < end:
        inflight[0] += 1
        bus.call("org.gnome.SettingsDaemon.Power", "/org/gnome/SettingsDaemon/Power",
                 IFACE, METHOD, None, None, Gio.DBusCallFlags.NONE, 10000, None, done, None)
    elif inflight[0] == 0:
        loop.quit()
for _ in range(N): fire()
loop.run()
print("  calls by result:", dict(counts))

