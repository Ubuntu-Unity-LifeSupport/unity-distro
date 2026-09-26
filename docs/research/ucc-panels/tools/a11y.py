#!/usr/bin/env python3
# List (or act on) accessible widgets of unity-control-center through AT-SPI -
# the same signals a real click produces. A-7, agent A.
# usage: a11y.py list [ROLE...] | a11y.py click NAME [ROLE] | a11y.py toggle NAME
import sys, gi
gi.require_version("Atspi", "2.0")
from gi.repository import Atspi
def walk(o, d=0):
    try: n = o.get_child_count()
    except Exception: return
    yield o, d
    for i in range(n):
        c = o.get_child_at_index(i)
        if c: yield from walk(c, d + 1)
app = None
desk = Atspi.get_desktop(0)
for i in range(desk.get_child_count()):
    a = desk.get_child_at_index(i)
    if a and "control-center" in (a.get_name() or ""): app = a
if not app: sys.exit("unity-control-center not on the accessibility bus")
roles = {"check box", "toggle button", "radio button", "combo box", "slider", "push button", "spin button", "page tab", "switch", "menu item"}
cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
for o, d in walk(app):
    r = o.get_role_name(); n = (o.get_name() or "").strip()
    if cmd == "list" and r in roles and n:
        st = o.get_state_set(); chk = "on" if st.contains(Atspi.StateType.CHECKED) else "off"
        val = ""
        try:
            v = o.get_value(); val = " value=%s" % v.get_current_value() if v else ""
        except Exception: pass
        print("%-14s %-4s %s%s" % (r, chk if r in ("check box","toggle button","radio button","switch") else "", n, val))
    elif cmd in ("click", "toggle") and n == sys.argv[2] and (len(sys.argv) < 4 or r == sys.argv[3]):
        act = o.get_action_iface() if hasattr(o, "get_action_iface") else o
        print("acting on", r, n, o.get_action_name(0)); o.do_action(0); break
