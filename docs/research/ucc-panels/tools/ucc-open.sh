#!/bin/bash
# Open one u-c-c panel with the session's environment (needed: OnlyShowIn=Unity7).
. ~/envt.sh; E=$(pgrep -u mike -x nemo-desktop | head -1)
while IFS= read -r -d "" kv; do case "$kv" in XDG_CURRENT_DESKTOP=*|XDG_SESSION_DESKTOP=*|DESKTOP_SESSION=*|XDG_DATA_DIRS=*|GTK_MODULES=*|UBUNTU_MENUPROXY=*|LANG=*|LANGUAGE=*|AT_SPI_BUS_ADDRESS=*) export "$kv";; esac; done < /proc/$E/environ
for p in $(pgrep -x unity-control-c); do kill $p; done; sleep 1
(setsid nohup unity-control-center $1 >/tmp/ucc-$1.out 2>&1 </dev/null &); sleep 6
