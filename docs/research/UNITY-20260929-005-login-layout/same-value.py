#!/usr/bin/env python3
"""UNITY-20260929-005: does GSettings (dconf backend) emit "changed" when a
key is written with the value it already has? Uses the same schema and calls
as indicator-keyboard (org.gnome.desktop.input-sources, set_value("sources"),
set_uint("current")), in-process, as the running user. Restores the original
values at the end."""

import gi
from gi.repository import Gio, GLib

s = Gio.Settings.new("org.gnome.desktop.input-sources")
events = []
s.connect("changed", lambda _s, key: events.append(key))
loop = GLib.MainLoop()


def settle(ms=500):
    GLib.timeout_add(ms, loop.quit)
    loop.run()


orig_sources, orig_current = s.get_value("sources"), s.get_uint("current")
print("backend:", type(Gio.SettingsBackend.get_default()).__name__)
print("start:", orig_sources.print_(False), orig_current)
settle()
events.clear()

s.set_value("sources", orig_sources); settle()
print("same sources written -> changed signals:", events); events.clear()
s.set_uint("current", orig_current); settle()
print("same current written -> changed signals:", events); events.clear()

other = GLib.Variant("a(ss)", [("xkb", "fr")])
s.set_value("sources", other); settle()
print("different sources written -> changed signals:", events); events.clear()
s.set_value("sources", other); settle()
print("that value again -> changed signals:", events); events.clear()

s.set_value("sources", orig_sources); s.set_uint("current", orig_current); settle()
events.clear()
print("restored:", s.get_value("sources").print_(False), s.get_uint("current"))
