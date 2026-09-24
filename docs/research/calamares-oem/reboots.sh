#!/bin/bash
# reboots.sh TAG N - reboot oemtest N times, probe the OEM session after each boot.
for n in $(seq 1 $2); do
  ssh oemtest 'sudo systemctl reboot' >/dev/null 2>&1; sleep 30
  for i in $(seq 1 40); do ssh -o ConnectTimeout=3 -o BatchMode=yes oemtest 'pgrep -x calamares >/dev/null' 2>/dev/null && break; sleep 5; done
  ssh oemtest "bash ~/probe.sh $1-$n" 2>&1 | grep -E '^==|pixel|focus'
done
