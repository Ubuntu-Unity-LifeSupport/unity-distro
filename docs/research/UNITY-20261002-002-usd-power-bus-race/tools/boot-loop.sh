#!/bin/bash
# UNITY-20261002-002 (runs on builder): N natural boots of target; after each,
# wait for the session, record whether org.gnome.SettingsDaemon.Power has an
# owner and copy that boot's u002-trace file. Stops at the first boot that does
# not come back within 4 minutes (check the VM from the host then).
# usage: boot-loop.sh N OUTDIR
N=${1:?count}; O=${2:?outdir}; mkdir -p "$O"
for i in $(seq 1 "$N"); do
  ssh target 'sudo systemctl reboot' 2>/dev/null
  sleep 30
  ok=
  for t in $(seq 1 40); do
    if timeout 6 ssh -o ConnectTimeout=4 target 'pgrep -x unity-settings- >/dev/null && pgrep -x compiz >/dev/null' 2>/dev/null; then ok=1; break; fi
    sleep 5
  done
  [ -n "$ok" ] || { echo "boot $i: target did not come back"; exit 1; }
  sleep 25
  ssh target '. ~/envt.sh; b=$(cat /proc/sys/kernel/random/boot_id)
    o=$(gdbus call --session --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus --method org.freedesktop.DBus.GetNameOwner org.gnome.SettingsDaemon.Power 2>&1 | cut -c1-60)
    echo "boot_id $b u-s-d $(dpkg-query -W -f "\${Version}" unity-settings-daemon) pid $(pgrep -x unity-settings-) drop-ins: $(ls ~/.config/systemd/user/unity-settings-daemon.service.d/ 2>/dev/null | tr "\n" " ") power-owner: $o"
    [ -f ~/u002/toggle-$b.txt ] && { echo "toggle: $(cat ~/u002/toggle-$b.txt)"; }
    sudo cat /var/tmp/u002/trace-$b.txt' > "$O/boot-$i.txt" 2>&1
  echo "boot $i: $(head -1 "$O/boot-$i.txt" | sed 's/.*power-owner: //'); stops: $(grep -c ' STOP$' "$O/boot-$i.txt")$(grep -q '^toggle:' "$O/boot-$i.txt" && echo '; toggled')"
done
