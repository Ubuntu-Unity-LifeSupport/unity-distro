#!/bin/bash
# add the appmenu plugin to Xfce panel-1 right after the applications menu
export DISPLAY=:0
export $(tr '\0' '\n' < /proc/$(pgrep -x xfce4-session)/environ | grep -E '^(DBUS_SESSION_BUS_ADDRESS|XAUTHORITY)=')
for p in $(pgrep -x xfce4-panel); do
	grep -q -- '--add' /proc/$p/cmdline 2>/dev/null && kill $p
done
sleep 1
ids=$(xfconf-query -c xfce4-panel -p /panels/panel-1/plugin-ids | grep -E '^[0-9]+$')
echo "before: $(echo $ids)"
xfconf-query -c xfce4-panel -p /plugins/plugin-30 -n -t string -s appmenu
args=()
for i in $ids; do
	args+=(-t int -s "$i")
	[ "$i" = 1 ] && args+=(-t int -s 30)
done
xfconf-query -c xfce4-panel -p /panels/panel-1/plugin-ids -r
xfconf-query -c xfce4-panel -p /panels/panel-1/plugin-ids -n -a "${args[@]}"
echo "after: $(xfconf-query -c xfce4-panel -p /panels/panel-1/plugin-ids | grep -E '^[0-9]+$' | tr '\n' ' ')"
setsid xfce4-panel -r >/dev/null 2>&1 < /dev/null &
sleep 5
pgrep -a xfce4-panel
