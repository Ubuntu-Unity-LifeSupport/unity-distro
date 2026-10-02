#!/bin/sh
# UNITY-20261002-002 (D6a): run by u002-window-toggle.service right after
# unity-settings-daemon.service starts. Waits until the power plugin has
# started (its first logind inhibitor), then switches the plugin off and on
# through the GSettings key, while the g_bus_get() result is still pending.
# Writes what it did and when to ~/u002/toggle-<boot_id>.txt; the
# bpftrace trace of the same boot shows whether STOP landed before
# ON-BUS-GOTTEN.
S=com.canonical.unity.settings-daemon.plugins.power
O=$HOME/u002/toggle-$(cat /proc/sys/kernel/random/boot_id).txt
mkdir -p "$HOME/u002"
t0=$(date +%s.%N)
i=0
while [ $i -lt 200 ]; do
  if systemd-inhibit --list --no-pager 2>/dev/null | grep -q "unity-settings"; then break; fi
  sleep 0.05; i=$((i+1))
done
t1=$(date +%s.%N)
gsettings set $S active false; t2=$(date +%s.%N)
sleep 0.3
gsettings set $S active true; t3=$(date +%s.%N)
d() { awk -v a="$1" -v b="$2" 'BEGIN { printf "%.2f", a - b }'; }
echo "u-s-d $(dpkg-query -W -f '${Version}' unity-settings-daemon) pid $(pgrep -x unity-settings-): waited $(d "$t1" "$t0") s for the first inhibitor (polls: $i); active=false at +$(d "$t2" "$t0") s; active=true at +$(d "$t3" "$t0") s" > "$O"
