#!/bin/sh
# UNITY-20260927-012: the natural trigger of the logout/restart crash. As
# usd-color-uaf.sh, gdb makes u-s-d run gnome_settings_manager_stop() (every
# plugin finalized) and leaves its main loop running; then, instead of an
# inhibitor, the session manager itself goes away: cinnamon-session is killed,
# org.gnome.SessionManager vanishes from the bus, and the shared session
# proxy emits g-properties-changed with nothing in `changed` (its cached
# properties invalidated). Ends the session - run as root through systemd-run,
# lightdm is restarted at the end. Output: /var/tmp/u012-namevanish.txt.
O=/var/tmp/u012-namevanish.txt
P=$(pgrep -x unity-settings- | head -1)
C=$(pgrep -x cinnamon-sessio | head -1)
echo "u-s-d $(dpkg-query -W -f='${Version}' unity-settings-daemon) pid $P; cinnamon-session pid $C; $(tr '\0' '\n' < /proc/$P/environ | grep ^GLIBC_TUNABLES=)" > $O
cat > /tmp/nv.gdb <<'G'
set pagination off
set breakpoint pending on
set confirm off
handle SIGTERM nostop noprint pass
handle SIGPIPE nostop noprint pass
handle SIGCONT nostop noprint pass
call (void) gnome_settings_manager_stop (gnome_settings_manager_new ())
echo STOP-CALLED\n
break engine_session_properties_changed_cb
commands
  silent
  printf "POWER-CB manager=%p\n", manager
  continue
end
break gcm_session_active_changed_cb
commands
  silent
  printf "COLOR-CB manager=%p\n", manager
  continue
end
continue
echo AFTER-CONTINUE\n
bt 8
G
timeout 60 gdb -q -batch -p $P -x /tmp/nv.gdb > /tmp/nv-gdb.txt 2>&1 &
G=$!
sleep 12
logger -t u012 "killing cinnamon-session $C"
kill -9 "$C"
sleep 15
kill $G 2>/dev/null; wait $G 2>/dev/null
grep -E "STOP-CALLED|POWER-CB|COLOR-CB|AFTER-CONTINUE|SIGSEGV|signal SIG|^#[0-9]" /tmp/nv-gdb.txt | cut -c1-200 >> $O
echo "u-s-d pid $P alive after: $(kill -0 $P 2>/dev/null && echo yes || echo no); crash reports: $(ls /var/crash | grep -c unity-settings)" >> $O
systemctl restart lightdm
