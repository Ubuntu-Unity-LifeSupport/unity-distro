#!/bin/bash
# check.sh TAG - on target2 (as mike over ssh), after a cold boot with autologin: what the X session start did.
#   - how the session was started: lightdm's log (the command it ran), the Xsession trace (the shell that sourced
#     Xsession.d and the LD_PRELOAD it held at the end), ~/.xsession-errors
#   - the user manager's LD_PRELOAD (systemctl --user show-environment) and the generator's view
#   - the session leader (the session's top process under lightdm) and compiz, unity-panel-service: LD_PRELOAD in
#     /proc/PID/environ, printed with cat -A so a literal $LIB, spaces or "$'" are visible; the two libraries in maps
#   - a GTK3 (gnome-disks) and a GTK4 (gnome-calculator) application started through the user manager
#     (systemd-run --user, like the dash/launcher does) and one started from the session leader's environment
#   - sudo -n true, su -c true, ping -c1, pkexec true run with the session's LD_PRELOAD: ld.so lines on stderr
#   - ld.so lines in the journals of this boot
set -u
tag=$1
cp=$(pgrep -x compiz | head -1)
export $(tr '\0' '\n' < /proc/$cp/environ | grep -E '^(DISPLAY|XAUTHORITY|DBUS_SESSION_BUS_ADDRESS|XDG_RUNTIME_DIR)=')
show() {  # show LABEL PID
  local e; e=$(tr '\0' '\n' < /proc/$2/environ | grep '^LD_PRELOAD=' | cat -A | sed 's/\$$//')
  echo "  $1 pid $2 ($(tr '\0' ' ' < /proc/$2/cmdline | cut -c1-60)): ${e:-LD_PRELOAD unset}"
  echo "    maps: $(grep -oE 'lib(gtk-nocsd|unity-gtk4-menu)\.so\.0' /proc/$2/maps | sort -u | xargs)"
}
echo "== $tag at $(date -u +%FT%TZ), boot $(uptime -s); $(dpkg-query -W -f='libgtk-nocsd0 ${Version}, ' libgtk-nocsd0)$(dpkg-query -W -f='libunity-gtk4-menu0 ${Version}' libunity-gtk4-menu0)"
echo "-- how the session was started"
sudo lightdm --show-config 2>&1 | grep -i 'session-wrapper' | sed 's/^/  lightdm config: /'
sudo grep -hE 'Running command|session-wrapper|Session pid=.*: Started|Session.*exited' /var/log/lightdm/lightdm.log | tail -5 | sed 's/^/  lightdm.log: /'
if [ -f /tmp/b1301-xsession-trace ]; then sed 's/^/  trace: /' /tmp/b1301-xsession-trace | cat -A | sed 's/\$$//'; else echo "  trace: none (Xsession.d trace file not sourced)"; fi
echo "  ~/.xsession-errors: $(stat -c '%y %s bytes' ~/.xsession-errors 2>&1)"; grep -iE 'ld\.so|gtk-nocsd|preload|error' ~/.xsession-errors 2>/dev/null | head -5 | sed 's/^/    /'
echo "-- user manager"
echo "  started $(ps -o lstart= -p "$(pgrep -u "$(id -u)" -x systemd | head -1)")"
systemctl --user show-environment | grep '^LD_PRELOAD=' | cat -A | sed 's/\$$//; s/^/  show-environment: /'
/usr/lib/systemd/user-environment-generators/30-systemd-environment-d-generator 2>/dev/null | grep '^LD_PRELOAD=' | sed 's/^/  generator now: /'
echo "-- session processes"
# the graphical session of this user (loginctl Type=x11) and its leader, the process lightdm started
for s in $(loginctl list-sessions --no-legend | awk -v u="$(id -un)" '$3 == u {print $1}'); do
  [ "$(loginctl show-session "$s" -p Type --value)" = x11 ] && { xs=$s; lead=$(loginctl show-session "$s" -p Leader --value); }
done
# logind's Leader is lightdm's session child (root); the session itself is its child, the process the wrapper
# (lightdm-session or /etc/X11/Xsession) became by exec
kid=$(pgrep -P "${lead:?no x11 session}" -u "$(id -u)" | head -1)
echo "  logind session ${xs:-?}: Leader $lead ($(tr '\0' ' ' < /proc/$lead/cmdline | cut -c1-40)), its child $kid"
show "session process (the wrapper's exec)" "${kid:?no session process}"
lead=$kid
show compiz "$cp"
show unity-panel-service "$(pgrep -x unity-panel-ser | head -1)"
echo "-- applications"
for a in gnome-disks gnome-calculato; do pkill -x "$a"; done; sleep 1
systemd-run --user --quiet --collect --unit=b1301-disks gnome-disks; sleep 6
show "gnome-disks (GTK3, via the user manager)" "$(pgrep -x gnome-disks | head -1)"
env -i $(tr '\0' '\n' < /proc/$lead/environ | grep -E '^[A-Z_]+=' | tr '\n' ' ') gnome-calculator > /dev/null 2>&1 & sleep 6
show "gnome-calculator (GTK4, from the session leader's environment)" "$(pgrep -x gnome-calculato | head -1)"
w=$(xdotool search --onlyvisible --class gnome-calculator | tail -1); echo "  gnome-calculator window $w: $(xprop -id "$w" _GTK_MENUBAR_OBJECT_PATH 2>&1)"
echo "-- privileged programs with the session's LD_PRELOAD"
LP=$(tr '\0' '\n' < /proc/$lead/environ | sed -n 's/^LD_PRELOAD=//p')
for c in "sudo -n true" "su -c true" "ping -c1 -W1 127.0.0.1" "pkexec true"; do
  err=$(LD_PRELOAD="$LP" timeout 5 $c 2>&1 >/dev/null < /dev/null); echo "  $c: ld.so lines $(printf '%s\n' "$err" | grep -c 'ld.so')"
done
echo "-- journals of this boot"
echo "  system: $(sudo journalctl -b --no-pager -q | grep -c 'ld.so: object'), user: $(journalctl --user -b --no-pager -q | grep -c 'ld.so: object') lines 'ld.so: object'"
pkill -x gnome-disks; pkill -x gnome-calculato; true
