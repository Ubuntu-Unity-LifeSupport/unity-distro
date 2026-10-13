#!/bin/bash
# testfiles.sh trace|on|off|optout-on|optout-off - on target2 (as mike over ssh, sudo): the test files of this task.
#   on:  /etc/lightdm/lightdm.conf.d/99-b1301-xsession.conf  [Seat:*] session-wrapper=/etc/X11/Xsession
#        /etc/X11/Xsession.d/98zzb1301trace  (sourced by /etc/X11/Xsession after 95dbus_update-activation-env and before 99x11-common_start, which execs the session: records the shell executable that
#        sources it, its own LD_PRELOAD and the date into /tmp/b1301-xsession-trace)
#   trace: only the Xsession.d trace file (a control session through lightdm's default wrapper)
#   off: removes both, and prints what is left in lightdm.conf.d and Xsession.d
#   optout-on / optout-off: the user's opt-out file ~/.config/environment.d/50-gtk-nocsd.conf (empty), as in
#        UNITY-20261012-005 gate/target-test.txt step 6
set -u
D=/etc/lightdm/lightdm.conf.d/99-b1301-xsession.conf
T=/etc/X11/Xsession.d/98zzb1301trace
O=~/.config/environment.d/50-gtk-nocsd.conf
case $1 in
  trace|on)
    if [ "$1" = on ]; then
      sudo mkdir -p /etc/lightdm/lightdm.conf.d
      printf '[Seat:*]\nsession-wrapper=/etc/X11/Xsession\n' | sudo tee $D > /dev/null
    fi
    # shellcheck disable=SC2016
    printf '%s\n' '# UNITY-20261013-001 test trace, sourced by /etc/X11/Xsession; removed after the test' \
      'echo "$(date -u +%FT%T.%NZ) pid=$$ exe=$(readlink /proc/$$/exe) LD_PRELOAD=${LD_PRELOAD-<unset>}" >> /tmp/b1301-xsession-trace' \
      | sudo tee $T > /dev/null
    sudo chmod 644 $T; [ -f $D ] && sudo chmod 644 $D
    echo "  $1: drop-in $(sed -n 2p $D 2>/dev/null || echo none) | trace file $(wc -l < $T) lines"
    sudo lightdm --show-config 2>&1 | grep -i 'session-wrapper' | sed 's/^/  lightdm: /'
    ;;
  off)
    sudo rm -f -- "$D" "$T"
    echo "  off: lightdm.conf.d: $(ls /etc/lightdm/lightdm.conf.d/ 2>&1 | xargs); Xsession.d has b1301: $(ls /etc/X11/Xsession.d | grep -c b1301)"
    sudo lightdm --show-config 2>&1 | grep -i 'session-wrapper' | sed 's/^/  lightdm: /'
    ;;
  optout-on) mkdir -p ~/.config/environment.d && : > "$O" && echo "  opt-out file: $(ls -l "$O")" ;;
  optout-off) rm -f -- "$O"; echo "  opt-out file removed: $(ls "$O" 2>&1)" ;;
esac
