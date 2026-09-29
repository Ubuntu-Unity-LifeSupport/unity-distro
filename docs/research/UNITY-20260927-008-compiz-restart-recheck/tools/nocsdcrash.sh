#!/bin/sh
# A GTK3 app shows a window, then segfaults, with gtk-nocsd preloaded the way
# environment.d does it. Prints what the crash helper does.
. ~/envt.sh
cat > /tmp/segv.py <<'PY'
import gi, os, signal, sys
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
print("pid", os.getpid(), "argv", sys.argv, flush=True)
w = Gtk.Window(title="nocsd-crash-test"); w.show_all()
GLib.timeout_add(1500, lambda: os.kill(os.getpid(), signal.SIGSEGV))
Gtk.main()
PY
LD_PRELOAD=libgtk-nocsd.so.0 timeout 20 python3 /tmp/segv.py first-run
echo "python exit=$?"
sleep 5
journalctl -k --since "-40s" --no-pager | grep -i segfault
pgrep -af "[l]ibgtk-nocsd.so.0 /usr/bin/python3" || echo "no helper left"
