#!/bin/bash
# fakebamf-run.sh [WSB] - UNITY-20260927-029: fakebamf.py and a window-stack-bridge (default: the
# installed one) on a private session bus; prints which of the three announced windows it keeps.
WSB=${1:-/usr/lib/x86_64-linux-gnu/hud/window-stack-bridge}
HERE=$(cd "$(dirname "$0")" && pwd)
exec dbus-run-session -- bash -c '
python3 "$0/fakebamf.py" 3 & fb=$!
sleep 1
QT_QPA_PLATFORM=offscreen "$1" > /tmp/wsb-fake.log 2>&1 & wsb=$!
wait $fb
kill $wsb 2>/dev/null
grep -h "Could not get" /tmp/wsb-fake.log | cut -c1-160
' "$HERE" "$WSB"
