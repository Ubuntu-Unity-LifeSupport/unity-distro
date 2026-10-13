#!/bin/sh
# UNITY-20260928-019 test T6: make the greeter's PAM close block, to see what
# bounds a cleanup that hangs. Run as root on target.
#   stall-close.sh on   - pam_exec close_session hook in lightdm-greeter only,
#                         sleeping 60 s (pam_exec waits for it)
#   stall-close.sh off  - remove it again
set -eu
HOOK=/usr/local/sbin/ld019-stall
PAM=/etc/pam.d/lightdm-greeter
LINE="session optional pam_exec.so type=close_session $HOOK"
case "${1:?on|off}" in
on)
  printf '#!/bin/sh\nlogger -t ld019-stall "greeter close hook: sleeping 60 s"\nsleep 60\nlogger -t ld019-stall "greeter close hook: done"\n' > $HOOK
  chmod 755 $HOOK
  grep -qF "$LINE" $PAM || echo "$LINE" >> $PAM ;;
off)
  sed -i "\|$HOOK|d" $PAM
  rm -f $HOOK ;;
esac
grep -n pam_exec $PAM || echo "no pam_exec line in $PAM"
