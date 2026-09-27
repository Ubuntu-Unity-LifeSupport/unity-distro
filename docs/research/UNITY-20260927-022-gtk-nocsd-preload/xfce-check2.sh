#!/bin/bash
# xfce-check2.sh - gnome-text-editor (GTK4, client-side decorations by default)
# started with the Xfce session environment and with LD_PRELOAD removed;
# compare the decoration properties the window sets.
export DISPLAY=:0
P=$(pidof -s xfwm4)
for mode in session no-preload; do
  f='^$'; [ $mode = no-preload ] && f='^LD_PRELOAD='
  tr '\0' '\n' < /proc/$P/environ | grep -v "$f" | tr '\n' '\0' > ~/.xc-env
  xargs -0 -a ~/.xc-env sh -c 'exec env -i "$@" setsid gnome-text-editor' _ > ~/xc2-$mode.log 2>&1 < /dev/null &
  sleep 8
  G=$(pidof -s gnome-text-editor); w=$(xdotool search --onlyvisible --class gnome-text-editor | tail -1)
  echo "$mode: nocsd_mapped=$(grep -c libgtk-nocsd /proc/$G/maps) $(xprop -id "$w" _GTK_FRAME_EXTENTS _MOTIF_WM_HINTS | tr '\n' ' ')"
  gnome-screenshot -f ~/xc2-$mode.png 2>/dev/null
  pkill -x gnome-text-edit; sleep 2
done
