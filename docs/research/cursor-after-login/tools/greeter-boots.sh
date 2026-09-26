#!/bin/bash
# Known issue #1 on non-autologin paths (agent A). Per boot:
#  G: password login of utest through the greeter on :0
#  R: utest logs out (SessionManager.Logout, no dialog) and logs in again, same boot
#  S: utest switches user (dm-tool switch-to-greeter), utest2 logs in on the new display
# Each measured with cursor-loop2.sh (plugin logs + real PS/2 input).
t() { ssh -o ConnectTimeout=5 target "$@" 2>/dev/null; }
waitc() { for i in $(seq 1 60); do t "pgrep -u $1 -x compiz >/dev/null && pgrep -u $1 -f [u]nity-panel-service >/dev/null" && return 0; sleep 3; done; return 1; }
for n in $(seq $1 $2); do
  t 'sudo systemctl reboot'; sleep 25
  for i in $(seq 1 60); do t 'pgrep -x lightdm-gtk-gre >/dev/null' && break; sleep 5; done
  t "sudo touch /tmp/mark-G$n; ~/greeter-login.sh utest :0"
  waitc utest || { echo "G$n: utest session did not come up"; continue; }
  sleep 15; t "~/cursor-loop2.sh G$n utest :0 /tmp/mark-G$n"
  t "sudo -u utest DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1001/bus gdbus call --session -d org.gnome.SessionManager -o /org/gnome/SessionManager -m org.gnome.SessionManager.Logout 1 >/dev/null"
  sleep 8; for i in $(seq 1 40); do t 'pgrep -u utest -x compiz >/dev/null' || break; sleep 3; done
  t "sudo touch /tmp/mark-R$n; ~/greeter-login.sh utest :0"
  waitc utest || { echo "R$n: utest session did not come up"; continue; }
  sleep 15; t "~/cursor-loop2.sh R$n utest :0 /tmp/mark-R$n"
  t "sudo touch /tmp/mark-S$n; sudo -u utest DISPLAY=:0 XDG_SEAT_PATH=/org/freedesktop/DisplayManager/Seat0 dm-tool switch-to-greeter"
  sleep 5; D=$(t "sudo ls /var/run/lightdm/root/ | sort -V | tail -1"); t "~/greeter-login.sh utest2 $D"
  waitc utest2 || { echo "S$n: utest2 session did not come up on $D"; continue; }
  sleep 15; t "~/cursor-loop2.sh S$n utest2 $D /tmp/mark-S$n"
done
