#!/bin/bash
# xs.sh SESSION TAG: log in to SESSION through LightDM autologin, report LD_PRELOAD of session processes
S=$1
F=/etc/lightdm/lightdm.conf.d/50-autologin.conf; sudo -n sed -i "/^autologin-session=/d" $F; echo "autologin-session=$S" | sudo -n tee -a $F >/dev/null
grep -rh autologin /etc/lightdm/ 2>/dev/null | sort -u | tr '\n' ' '; echo
sudo -n systemctl restart lightdm; sleep 25
for p in compiz xfce4-session xfce4-panel xfdesktop xfwm4 ssh-agent; do
  for pid in $(pgrep -x $p -u mike); do
    echo "$2 $p: LD_PRELOAD=$(tr '\0' '\n' </proc/$pid/environ | sed -n 's/^LD_PRELOAD=//p') SSH_AUTH_SOCK=$(tr '\0' '\n' </proc/$pid/environ | grep -c ^SSH_AUTH_SOCK) nocsd-mapped=$(grep -c nocsd /proc/$pid/maps)"
  done
done
