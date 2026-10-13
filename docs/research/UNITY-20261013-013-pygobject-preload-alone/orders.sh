#!/bin/bash
# orders.sh TAG - on target2 (as mike over ssh): the installed libunity-gtk4-menu (M) in every preload order next to
# Ubuntu's gtk-nocsd (N, 4.8-1+unity4) and gtk-nocsd built by its own make (N0, codeberg 6b1f70a in ~/b/nocsd-head,
# the issue #1 build), and alone; under Xvfb with XDG_CURRENT_DESKTOP=Unity and the library's debug log.
#   - Python programs: a GLib-only import, apps.py 3 and 4, meld, gnome-tweaks, unity-indicator-appearance. rc 124 =
#     alive at the 10 s timeout; also the AssertionError/Traceback lines and the library's lookup line.
#   - the local-scope plugin (localplugin.c): the libgtk-4 fallback of gtk_widget_action_set_enabled
#   - the 0.9 card's own regression set, docs/research/nocsd-order/order-0.9.sh, unchanged (copied to ~/b)
set -u
tag=$1; B=~/b1313
L=/usr/lib/x86_64-linux-gnu; M=$L/libunity-gtk4-menu.so.0; N=$L/libgtk-nocsd.so.0; N0=$HOME/b/nocsd-head/libgtk-nocsd.so.0
echo "== $tag at $(date -u +%FT%TZ); $(dpkg-query -W -f='libunity-gtk4-menu0 ${Version}' libunity-gtk4-menu0)"
Xvfb :78 -screen 0 1280x800x24 >/dev/null 2>&1 & XV=$!; sleep 2
export DISPLAY=:78 XDG_CURRENT_DESKTOP=Unity UNITY_GTK4_MENU_DEBUG=1
eval "$(dbus-launch --sh-syntax)"
cc -shared -fPIC -o $B/localplugin.so $B/localplugin.c $(pkg-config --cflags --libs gtk4) 2>/dev/null
cc -o $B/localhost $B/localplugin.c -DHOST -ldl 2>/dev/null
for ord in "" "$M" "$M:$N" "$N:$M" "$M:$N0" "$N0:$M"; do
  echo "-- LD_PRELOAD=[${ord//$L\//}]"
  for a in "python3 -c 'from gi.repository import GLib; GLib.MainLoop()'" "python3 $B/apps.py 3" "python3 $B/apps.py 4" \
           meld gnome-tweaks unity-indicator-appearance "$B/localhost $B/localplugin.so"; do
    log=/tmp/ord-$$.log; rm -f $log
    out=$(UNITY_GTK4_MENU_LOG=$log LD_PRELOAD=$ord timeout -s TERM 10 bash -c "$a" 2>&1); rc=$?
    tb=$(printf '%s\n' "$out" | grep -cE 'AssertionError|Traceback')
    look=$(grep -hoE 'not in the global scope; taking [^ ]+|no g_module_symbol[^.]*|no gtk_widget_action_set_enabled[^.]*|the next [a-z_]+ is our own' $log 2>/dev/null | sort -u | tr '\n' ' ')
    extra=$(printf '%s\n' "$out" | grep -E '^(activations|libgtk-4 in)' | tr '\n' ' ')
    printf '  %-48s rc=%-3s tracebacks=%s %s%s\n' "$(echo "$a" | cut -c1-48)" $rc $tb "${look:+[$look] }" "$extra"
  done
done
kill $XV $DBUS_SESSION_BUS_PID 2>/dev/null; wait 2>/dev/null
echo "-- the 0.9 card's order-0.9.sh, unchanged (M = the installed library, N0 = ~/b/nocsd-head)"
bash ~/b/order-0.9.sh
