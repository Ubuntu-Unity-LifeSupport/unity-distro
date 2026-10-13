#!/bin/bash
# sync.sh LABEL - on target2: the panel service's own entry table for the application menus, as unity reads it
# (com.canonical.Unity.Panel.Service.Sync, a(sssusbbusbbi): indicator, entry id, name hint, parent window, label,
# label sensitive, label visible, image type, image data, image sensitive, image visible, priority), and the
# active window, at one moment.
set -u
export $(tr '\0' '\n' < /proc/$(pgrep -x compiz)/environ | grep -E '^(DBUS_SESSION_BUS_ADDRESS|XAUTHORITY)=') DISPLAY=:0
echo "== $1 at $(date -u +%T.%N | cut -c1-12)Z, active window $(xdotool getactivewindow) ($(printf '0x%x' "$(xdotool getactivewindow)"))"
gdbus call --session -d com.canonical.Unity.Panel.Service.Desktop -o /com/canonical/Unity/Panel/Service \
  -m com.canonical.Unity.Panel.Service.Sync | python3 -c '
import ast, sys
s = sys.stdin.read().strip()
s = s.replace("uint32 ", "").replace("true", "True").replace("false", "False")
rows = ast.literal_eval(s)[0]
for r in rows:
    if "appmenu" not in r[0]:
        continue
    ind, eid, hint, win, label, lsens, lvis, itype, idata, isens, ivis, prio = r
    print(f"  {ind} id={eid} win={win} label={label!r} sensitive={lsens} visible={lvis} prio={prio}")
'
