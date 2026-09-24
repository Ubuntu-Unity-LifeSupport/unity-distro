#!/usr/bin/python3
# Print Unity's introspection state of every DecoratedWindow.
import sys, dbus
bus = dbus.SessionBus()
o = bus.get_object("com.canonical.Unity", "/com/canonical/Unity/Debug")
st = o.GetState("//DecoratedWindow", dbus_interface="com.canonical.Autopilot.Introspection")
keys = ["xid", "title", "active", "framed", "fully_decorated", "shadow_decorated", "shadow_rect", "frame_geo", "should_be_decorated"]
for path, props in st:
    p = {k: props[k][1:] if k in props else None for k in keys}
    def v(x):
        if x is None: return "-"
        x = list(x); return x[0] if len(x) == 1 else tuple(int(i) for i in x)
    print(" ".join(f"{k}={v(p[k])}" for k in keys))
