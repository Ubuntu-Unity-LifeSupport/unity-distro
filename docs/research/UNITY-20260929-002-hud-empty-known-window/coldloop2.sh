#!/bin/bash
# coldloop2.sh N OUTDIR - UNITY-20260929-002 reproduction: reboot target2 N times; after each boot wait for the
# session's hud-service and window-stack-bridge, then one Writer start with lo7.sh (the first LibreOffice start
# after login). Per boot, save the user journal lines of hud-service, window-stack-bridge, bamfdaemon and
# dbus-daemon (bamf activation) since boot, plus the bamf window stack and the HUD query result, in OUTDIR/boot-N.txt.
set -u
n=${1:-10}; out=${2:?outdir}; mkdir -p "$out"
for b in $(seq "$n"); do
  ssh target2 'sudo -n systemctl reboot' 2>/dev/null
  sleep 40
  until ssh -o ConnectTimeout=5 -o BatchMode=yes target2 'pgrep -x hud-service >/dev/null && pgrep -x window-stack-br >/dev/null' 2>/dev/null; do sleep 5; done
  sleep 20
  {
    echo "# boot $b $(date -u +%FT%TZ)"
    ssh target2 'echo "boot_id=$(cat /proc/sys/kernel/random/boot_id) uptime=$(cut -d" " -f1 /proc/uptime)"; echo "hud-service pid=$(pgrep -x hud-service) window-stack-bridge pid=$(pgrep -x window-stack-br) bamfdaemon pid=$(pgrep -x bamfdaemon)"'
    echo "## run: $(ssh target2 'GAP=0 WATCH_DELAY=0 bash ~/b029/lo7.sh 1 2>&1 | tail -1')"
    echo "## GMenu window properties now, through window-stack-bridge, for the run's xid (what hud-service read once at WindowCreated)"
    xid=$(grep '^## run' "$out/boot-$b.txt" 2>/dev/null | grep -o 'xid=[0-9]*' | cut -d= -f2)
    ssh target2 "export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/\$(id -u)/bus; xid=\$(xdotool search --onlyvisible --name 'LibreOffice Writer' 2>/dev/null | tail -1); echo xid_now=\$xid; gdbus call --session --dest com.canonical.Unity.WindowStack --object-path /com/canonical/Unity/WindowStack --method com.canonical.Unity.WindowStack.GetWindowProperties \$xid '' \"['_GTK_UNIQUE_BUS_NAME','_GTK_APP_MENU_OBJECT_PATH','_GTK_MENUBAR_OBJECT_PATH','_GTK_APPLICATION_OBJECT_PATH','_GTK_WINDOW_OBJECT_PATH','_UNITY_OBJECT_PATH']\" 2>&1; DISPLAY=:0 xprop -id \$xid 2>/dev/null | grep -E '_GTK_|_UNITY_|WM_CLASS'"
    echo "## bamf window stack after the run"
    ssh target2 'export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus; gdbus call --session --dest com.canonical.Unity.WindowStack --object-path /com/canonical/Unity/WindowStack --method com.canonical.Unity.WindowStack.GetWindowStack 2>&1 | cut -c1-600'
    echo "## journal since boot: hud-service, window-stack-bridge, bamfdaemon, bamf activation"
    ssh target2 'journalctl --user -b --no-pager -o short-precise 2>/dev/null | grep -E "hud-service|window-stack-bridge|bamfdaemon|org\.ayatana\.bamf" | grep -v -E "Started|Starting|Reached" | tail -60'
    echo "## bamfwatch files of this boot"
    ssh target2 'ls -t ~/b029/bamf-*.txt 2>/dev/null | head -1 | xargs -r cat | tail -40'
  } > "$out/boot-$b.txt" 2>&1
  echo "boot $b: $(grep '^## run' "$out/boot-$b.txt")"
done
