#!/usr/bin/env python3
# Press the N-th unnamed toggle button of the open u-c-c window (AT-SPI). A-7.
import sys, gi
gi.require_version("Atspi", "2.0"); from gi.repository import Atspi
d = Atspi.get_desktop(0)
app = [d.get_child_at_index(i) for i in range(d.get_child_count()) if "control-center" in (d.get_child_at_index(i).get_name() or "")][0]
def walk(o):
    yield o
    for i in range(o.get_child_count()):
        c = o.get_child_at_index(i)
        if c: yield from walk(c)
t = [o for o in walk(app) if o.get_role_name() == "toggle button" and not (o.get_name() or "").strip()]
t[int(sys.argv[1])].do_action(0)
