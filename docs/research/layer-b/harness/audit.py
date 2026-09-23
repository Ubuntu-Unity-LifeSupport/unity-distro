#!/usr/bin/python3
"""audit.py PID - read a GTK4 window's global menu the way Unity does.

Finds the process's visible window, reads the _GTK_* properties from X11, walks
the exported menubar over org.gtk.Menus, and classifies every item's action:
  ok        exported and enabled
  disabled  exported, currently disabled (the app says so - correct grey)
  MISSING   not exported at all - Unity shows it greyed and cannot activate it
"""
import subprocess, sys
from gi.repository import Gio, GLib

pid = sys.argv[1]
wids = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", pid],
                      capture_output=True, text=True).stdout.split()
props = {}
for wid in wids:
    out = subprocess.run(["xprop", "-id", wid], capture_output=True, text=True).stdout
    p = {}
    for line in out.splitlines():
        if line.startswith("_GTK_") and "=" in line:
            k, v = line.split("=", 1)
            p[k.split("(")[0].strip()] = v.strip().strip('"')
    if "_GTK_UNIQUE_BUS_NAME" in p:
        props = p
        break

if not props:
    print("NO-GTK-PROPS (no window exports _GTK_UNIQUE_BUS_NAME)")
    sys.exit(0)
if "_GTK_MENUBAR_OBJECT_PATH" not in props:
    print("NO-MENUBAR bus=%s" % props["_GTK_UNIQUE_BUS_NAME"])
    sys.exit(0)

bus = Gio.bus_get_sync(Gio.BusType.SESSION)
name = props["_GTK_UNIQUE_BUS_NAME"]

def call(path, iface, method, args, rtype):
    return bus.call_sync(name, path, iface, method, args,
                         GLib.VariantType(rtype), 0, 3000, None).unpack()

groups = {}
if "_GTK_APPLICATION_OBJECT_PATH" in props:
    groups["app"] = call(props["_GTK_APPLICATION_OBJECT_PATH"], "org.gtk.Actions",
                         "DescribeAll", None, "(a{s(bgav)})")[0]
if "_GTK_WINDOW_OBJECT_PATH" in props:
    groups["win"] = call(props["_GTK_WINDOW_OBJECT_PATH"], "org.gtk.Actions",
                         "DescribeAll", None, "(a{s(bgav)})")[0]

menus = {}
res = call(props["_GTK_MENUBAR_OBJECT_PATH"], "org.gtk.Menus", "Start",
           GLib.Variant("(au)", (list(range(64)),)), "(a(uuaa{sv}))")[0]
for g, m, items in res:
    menus[(g, m)] = items

def walk(g, m, depth, seen):
    if (g, m) in seen or (g, m) not in menus:
        return
    seen.add((g, m))
    for it in menus[(g, m)]:
        label = it.get("label", "")
        action = it.get("action")
        if action:
            prefix, _, short = action.partition(".")
            grp = groups.get(prefix, {})
            if short in grp:
                status = "ok" if grp[short][0] else "disabled"
            else:
                status = "MISSING"
            print("%s%-9s %-40s %s" % ("  " * depth, status, action, label))
        elif label:
            print("%s%-9s %-40s %s" % ("  " * depth, "", "-", label))
        for key in (":section", ":submenu"):
            if key in it:
                walk(it[key][0], it[key][1], depth + (key == ":submenu"), seen)

walk(0, 0, 0, set())
