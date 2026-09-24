#!/bin/bash
# stack.sh DISPLAY - print the WM stacking order (bottom first), the active window,
# and each client's class, state and type.
export DISPLAY=$1
act=$(xprop -root _NET_ACTIVE_WINDOW | awk '{print $NF}')
echo "active: $act"
for w in $(xprop -root _NET_CLIENT_LIST_STACKING | sed 's/.*# //; s/,//g'); do
  printf '%-10s %-40s %s | %s\n' "$w" "$(xprop -id $w WM_CLASS | sed 's/.*= //')" \
    "$(xprop -id $w _NET_WM_STATE | sed 's/.*= //; s/_NET_WM_STATE_//g')" \
    "$(xprop -id $w _NET_WM_WINDOW_TYPE | sed 's/.*= //; s/_NET_WM_WINDOW_TYPE_//g')"
done
