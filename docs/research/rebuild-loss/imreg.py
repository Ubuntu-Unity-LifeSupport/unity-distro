#!/usr/bin/python3
"""imreg.py - register an application with com.canonical.indicator.messages
directly (26.04's only libmessaging-menu is Ayatana's, which talks to
org.ayatana.indicator.messages), stay on the bus for 15 s, print the
indicator's root action state."""
import time
from gi.repository import Gio, GLib
bus = Gio.bus_get_sync(Gio.BusType.SESSION)
bus.call_sync('com.canonical.indicator.messages', '/com/canonical/indicator/messages/service',
              'com.canonical.indicator.messages.service', 'RegisterApplication',
              GLib.Variant('(so)', ('org.gnome.Terminal.desktop', '/b9/messages')),
              None, 0, 3000, None)
ctx = GLib.MainContext.default()
end = time.time() + 4
while time.time() < end:
    ctx.iteration(False); time.sleep(0.05)
st = bus.call_sync('com.canonical.indicator.messages', '/com/canonical/indicator/messages',
                   'org.gtk.Actions', 'Describe', GLib.Variant('(s)', ('messages',)),
                   None, 0, 3000, None).unpack()[0][2][0]
print('visible after register:', st.get('visible'))
open('/tmp/imreg.ready', 'w').close()
end = time.time() + 11
while time.time() < end:
    ctx.iteration(False); time.sleep(0.05)
