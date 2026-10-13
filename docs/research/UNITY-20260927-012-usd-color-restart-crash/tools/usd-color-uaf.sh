#!/bin/sh
# UNITY-20260927-012: the color plugin's session-proxy callback after the
# plugin was finalized. gdb makes u-s-d do what the session manager's Stop
# signal makes it do - gnome_settings_manager_stop(), which deactivates and
# unloads every plugin (the color manager is finalized) - but leaves its main
# loop running, as it runs on for the rest of the iteration in which Stop was
# dispatched. Then the session manager's properties change twice (an
# inhibitor taken and dropped), as they do when it leaves the bus at logout
# or restart. Run as mike over ssh; u-s-d's unit should have the
# zz-u012-perturb.conf drop-in.
. ~/envt.sh
P=$(pgrep -x unity-settings- | head -1)
echo "u-s-d $(dpkg-query -W -f='${Version}' unity-settings-daemon) pid $P tunables: $(sudo cat /proc/$P/environ | tr '\0' '\n' | grep ^GLIBC_TUNABLES=)"
cat > /tmp/uaf.gdb <<'G'
set pagination off
set breakpoint pending on
set confirm off
call (void) gnome_settings_manager_stop (gnome_settings_manager_new ())
echo STOP-CALLED\n
break gcm_session_active_changed_cb
commands
  silent
  printf "CB manager=%p priv=%p\n", manager, manager->priv
  continue
end
continue
echo AFTER-CONTINUE\n
bt 10
G
T=$(date +%T)
sudo -n timeout 40 gdb -q -batch -p $P -x /tmp/uaf.gdb > /tmp/uaf.txt 2>&1 &
G=$!
sleep 12
timeout 4 gdbus call --session --dest org.gnome.SessionManager --object-path /org/gnome/SessionManager \
  --method org.gnome.SessionManager.Inhibit test 0 "u012 test" 4 >/dev/null
sleep 6
wait $G
grep -E "^(CB)|STOP-CALLED|AFTER-CONTINUE|SIGSEGV|signal SIG|exited|^#[0-9]" /tmp/uaf.txt | head -24
echo "u-s-d pid $P alive: $(kill -0 $P 2>/dev/null && echo yes || echo no); journal since $T: $(journalctl --since $T --no-pager | grep -c -E 'unity-settings.*(segfault|dumped core)|Process [0-9]+ \(unity-settings-\) .*dumped core')"
journalctl --since $T --no-pager | grep -E 'unity-settings.*(segfault|dumped core|assertion|CRITICAL)' | cut -c1-200 | head -5
