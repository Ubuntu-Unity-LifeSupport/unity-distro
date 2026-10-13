#!/usr/bin/env python3
"""fakebamf.py - UNITY-20260927-029: a deterministic stand-in for bamfdaemon,
for window-stack-bridge on a private session bus.

It owns org.ayatana.bamf and announces three windows with ViewOpened:
  101 - its parent application path is not exported (what bamf answers while
        it re-matches a LibreOffice window: DesktopFile -> UnknownMethod);
  102 - its parent application answers DesktopFile with "" (bamf's temporary
        application of a window it has not matched yet);
  103 - its parent application answers DesktopFile with a real desktop file.
Then it asks com.canonical.Unity.WindowStack for GetWindowStack and prints
which windows window-stack-bridge knows, with their application ids.
Run it with window-stack-bridge on the same bus (see fakebamf-run.sh)."""
import sys

import warnings

from gi.repository import Gio, GLib

warnings.filterwarnings("ignore", category=DeprecationWarning)

XML = """
<node>
 <interface name="org.ayatana.bamf.matcher">
  <method name="WindowPaths"><arg name="paths" type="as" direction="out"/></method>
  <method name="WindowStackForMonitor"><arg name="monitor_id" type="i" direction="in"/><arg name="window_list" type="as" direction="out"/></method>
  <method name="ActiveWindow"><arg name="window" type="s" direction="out"/></method>
  <signal name="ViewOpened"><arg name="path" type="s"/><arg name="type" type="s"/></signal>
  <signal name="ViewClosed"><arg name="path" type="s"/><arg name="type" type="s"/></signal>
  <signal name="ActiveWindowChanged"><arg name="old_win" type="s"/><arg name="new_win" type="s"/></signal>
 </interface>
 <interface name="org.ayatana.bamf.view">
  <method name="Parents"><arg name="parents_paths" type="as" direction="out"/></method>
 </interface>
 <interface name="org.ayatana.bamf.window">
  <method name="GetXid"><arg name="xid" type="u" direction="out"/></method>
  <method name="Xprop"><arg name="xprop" type="s" direction="in"/><arg name="name" type="s" direction="out"/></method>
 </interface>
 <interface name="org.ayatana.bamf.application">
  <method name="DesktopFile"><arg name="desktop_file" type="s" direction="out"/></method>
 </interface>
</node>"""
NODE = Gio.DBusNodeInfo.new_for_xml(XML)
IFACE = {i.name: i for i in NODE.interfaces}
WINDOWS = {101: "/org/ayatana/bamf/application/0x1", 102: "/org/ayatana/bamf/application/0x2",
           103: "/org/ayatana/bamf/application/103"}
APPS = {"/org/ayatana/bamf/application/0x2": "",
        "/org/ayatana/bamf/application/103": "/usr/share/applications/libreoffice-writer.desktop"}
MATCHER = "/org/ayatana/bamf/matcher"
bus = Gio.bus_get_sync(Gio.BusType.SESSION)
loop = GLib.MainLoop()


def wpath(xid):
    return f"/org/ayatana/bamf/window/{xid}"


def handler(conn, sender, path, iface, method, params, inv):
    if iface == "org.ayatana.bamf.matcher":
        if method == "WindowPaths":
            inv.return_value(GLib.Variant("(as)", ([],)))
        elif method == "WindowStackForMonitor":
            inv.return_value(GLib.Variant("(as)", ([wpath(x) for x in WINDOWS],)))
        elif method == "ActiveWindow":
            inv.return_value(GLib.Variant("(s)", (wpath(103),)))
    elif iface == "org.ayatana.bamf.view":
        inv.return_value(GLib.Variant("(as)", ([WINDOWS[int(path.rsplit("/", 1)[1])]],)))
    elif iface == "org.ayatana.bamf.window":
        if method == "GetXid":
            inv.return_value(GLib.Variant("(u)", (int(path.rsplit("/", 1)[1]),)))
        else:
            inv.return_value(GLib.Variant("(s)", ("",)))
    elif iface == "org.ayatana.bamf.application":
        inv.return_value(GLib.Variant("(s)", (APPS[path],)))


bus.register_object(MATCHER, IFACE["org.ayatana.bamf.matcher"], handler)
for xid in WINDOWS:
    bus.register_object(wpath(xid), IFACE["org.ayatana.bamf.view"], handler)
    bus.register_object(wpath(xid), IFACE["org.ayatana.bamf.window"], handler)
for app in APPS:   # 0x1 is deliberately not exported
    bus.register_object(app, IFACE["org.ayatana.bamf.application"], handler)


def announce():
    for xid in WINDOWS:
        bus.emit_signal(None, MATCHER, "org.ayatana.bamf.matcher", "ViewOpened",
                        GLib.Variant("(ss)", (wpath(xid), "window")))
    GLib.timeout_add(1500, query)
    return False


def query():
    # asynchronous: window-stack-bridge calls back into this process while it answers
    bus.call("com.canonical.Unity.WindowStack", "/com/canonical/Unity/WindowStack",
             "com.canonical.Unity.WindowStack", "GetWindowStack", None, None,
             Gio.DBusCallFlags.NONE, 5000, None, answered)
    return False


def answered(conn, res):
    try:
        r = conn.call_finish(res).unpack()[0]
        known = {w[0]: w[1] for w in r}
        for xid in WINDOWS:
            print(f"window {xid}: " + (f"known, app id '{known[xid]}'" if xid in known else "MISSING"), flush=True)
    except GLib.Error as e:
        print("GetWindowStack failed:", e.message, flush=True)
    loop.quit()


def acquired(*_):
    # give window-stack-bridge time to start and subscribe
    GLib.timeout_add(int(float(sys.argv[1]) * 1000) if len(sys.argv) > 1 else 3000, announce)


Gio.bus_own_name_on_connection(bus, "org.ayatana.bamf", Gio.BusNameOwnerFlags.NONE, acquired, None)
loop.run()
