#!/bin/bash
# lf.sh TAG - restart the files lens daemon, search the Files lens for a file
# that was never opened, count the daemon's locate errors, screenshot /tmp/lf-TAG.png
export $(tr '\0' '\n' < /proc/$(pgrep -x compiz)/environ | grep -E '^(DBUS_SESSION_BUS_ADDRESS|XAUTHORITY)=')
pkill -f '[u]nity-files-daemon'; sleep 2
since=$(date +%s)
WAIT=12 timeout 60 bash /tmp/dash.sh super+f "b8quokka" /tmp/lf-$1.png </dev/null >/dev/null 2>&1
sleep 2
echo "$1: lens-files $(dpkg-query -W -f='${Version}' unity-lens-files), locate=$(command -v locate || echo none), locate errors in journal: $(journalctl --user --since "@$since" --no-pager -o cat | grep -c 'global search')"
