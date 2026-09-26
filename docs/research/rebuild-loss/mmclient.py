#!/usr/bin/python3
"""mmclient.py DESKTOP_ID SECONDS - a messaging-menu client through 26.04's
libmessaging-menu (Ayatana, the library Geary and Pidgin use): register the
application, add an "Inbox" source with 3 new messages that draws attention,
print activations, and stay for SECONDS."""
import sys, gi
gi.require_version('MessagingMenu', '1.0')
from gi.repository import MessagingMenu, GLib
app = MessagingMenu.App(desktop_id=sys.argv[1])
app.register()
app.append_source('inbox', None, 'Inbox')
app.set_source_count('inbox', 3)
app.draw_attention('inbox')
app.connect('activate-source', lambda a, s: print('ACTIVATED source', s, flush=True))
print('registered', sys.argv[1], flush=True)
loop = GLib.MainLoop()
GLib.timeout_add_seconds(int(sys.argv[2]), loop.quit)
loop.run()
