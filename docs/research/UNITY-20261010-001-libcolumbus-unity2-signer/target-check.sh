#!/bin/bash
# target-check.sh - on target2 (as mike over ssh, in the Unity session) after a cold boot with libcolumbus +unity2:
#   1. versions; hud-service and the applications scope (unity-scope-loader) map the installed libcolumbus.so.1.1.0
#      (same inode as the file on disk), no "(deleted)" library mappings
#   2. a HUD query gives results (frequent.py: the empty query's first rows), liveness.py (+3 open, back after close)
#   3. leak.sh (UNITY-20261008-013): deleted /tmp files in hud-service stay 0 over queries and application starts
#   4. lens.sh 4: the scope's deleted mappings stay constant over 4 re-indexes
set -u
export DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus
L=/usr/lib/x86_64-linux-gnu/libcolumbus.so.1.1.0
scope_pid() { for p in $(pgrep -x unity-scope-loa); do tr '\0' ' ' < /proc/$p/cmdline | grep -q 'applications/applications.scope' && echo $p; done | head -1; }
echo "== 1 versions and mappings ($(date -u +%FT%TZ), boot $(uptime -s))"
dpkg-query -W libcolumbus1v5 libcolumbus1-common hud unity unity-lens-applications 2>&1 | sed 's/^/  /'
echo "  installed $L inode $(stat -c %i $L) sha256 $(sha256sum < $L | cut -c1-16)"
H=$(pgrep -x hud-service | head -1)
P=$(scope_pid)
if [ -z "$P" ]; then
  gdbus call --session --dest com.canonical.Unity.Scope.Applications --object-path /com/canonical/unity/scope/applications \
    --method org.freedesktop.DBus.Peer.Ping > /dev/null 2>&1; sleep 3; P=$(scope_pid); fi
for x in "hud-service $H" "unity-scope-loader(applications) $P"; do set -- $x
  echo "  $1 pid $2: $(grep -F libcolumbus /proc/$2/maps | awk '{print $5, $6, $7}' | sort -u | xargs), deleted libraries $(grep '(deleted)' /proc/$2/maps | grep -vc ' /tmp/')"
done
echo "== 2 HUD query"
python3 ~/b013/frequent.py 2>&1 | head -3 | sed 's/^/  /'
python3 ~/b013/liveness.py 2>&1 | sed 's/^/  /'
echo "== 3 leak.sh"
bash ~/b013/leak.sh 2>&1 | sed 's/^/  /'
echo "== 4 lens.sh 4"
bash ~/b013/lens.sh 4 2>&1 | sed 's/^/  /'
echo "== end: hud-service pid $(pgrep -x hud-service | head -1) (was $H), scope pid $(scope_pid) (was $P)"
