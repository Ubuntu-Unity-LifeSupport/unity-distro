#!/bin/bash
# stop.sh TAG - end the dbus-monitor that start.sh TAG began and print its org.gtk.Menus / org.gtk.Actions calls,
# one line each (UTC time, sender, destination, member, first argument line), with the session bus names mapped to
# their processes, so the panel's own calls (unity-panel-service) are told apart from audit.py's.
set -u
tag=$1
sp=$(pgrep -x compiz)
export $(tr '\0' '\n' < /proc/$sp/environ | grep -E '^DBUS_SESSION_BUS_ADDRESS=')
names=$(busctl --user list --no-legend 2>/dev/null | awk '$1 ~ /^:/ {print $1, $3}')
kill "$(cat /tmp/mon-$tag.pid)" 2>/dev/null; kill "$(cat /tmp/act-$tag.pid)" 2>/dev/null; pkill -x xprop; sleep 0.5
echo "== $tag: _NET_ACTIVE_WINDOW changes (hex window id)"
sed 's/^/  /' /tmp/act-$tag.txt
echo "== $tag: org.gtk.Menus / org.gtk.Actions calls"
awk -v names="$names" '
  BEGIN { n = split(names, a, "\n"); for (i = 1; i <= n; i++) { split(a[i], f, " "); proc[f[1]] = f[2] } }
  /^(method call|signal|method return|error)/ {
    if (line != "") print line
    t = ""; s = ""; d = ""; m = ""
    for (i = 1; i <= NF; i++) {
      if ($i ~ /^time=/) t = substr($i, 6)
      if ($i ~ /^sender=/) s = substr($i, 8)
      if ($i ~ /^destination=/) d = substr($i, 13)
      if ($i ~ /^member=/) m = substr($i, 8)
    }
    kind = $1 == "method" ? $2 : $1
    cmd = "date -u -d @" t " +%T.%N"; cmd | getline ts; close(cmd)
    line = sprintf("  %s %-6s %s(%s) -> %s(%s) %s", substr(ts, 1, 12), kind, s, proc[s], d, proc[d], m)
    args = 0; next
  }
  line != "" && args < 2 { gsub(/^ +/, ""); line = line " | " $0; args++ }
  END { if (line != "") print line }
' /tmp/mon-$tag.txt | grep -v ' return \| error ' | grep -E 'Start|End|Changed|Activate|DescribeAll|Sync|ReSync|ShowEntry' | head -60
