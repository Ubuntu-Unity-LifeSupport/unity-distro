#!/bin/bash
# live.sh TAG - in the Unity session: start GIMP, LibreOffice Writer and Chromium
# (snap) without GTK_MODULES, so appmenu-gtk-module comes only from the
# gtk-modules XSETTING (u-s-d xsettings overrides; enabled-gtk-modules only
# takes modules u-s-d knows); drop the module, add it
# back; report which apps mapped it and which survived.
sp=$(pgrep -x compiz); mapfile -d '' envs < /proc/$sp/environ
export $(tr '\0' '\n' < /proc/$sp/environ | grep -E '^(DBUS_SESSION_BUS_ADDRESS|DISPLAY|XAUTHORITY)=')
K=com.canonical.unity.settings-daemon.plugins.xsettings
sudo -n rm -f /var/crash/*.crash
gsettings set $K overrides "{'Gtk/Modules': <'appmenu-gtk-module'>}"; sleep 2
run() { env -i "${envs[@]}" GTK_MODULES= "$@" >/dev/null 2>&1 & }
run gimp; run libreoffice --writer --norestore; run /snap/bin/chromium --no-first-run --user-data-dir=/tmp/b8-chrome about:blank
sleep 25
declare -A P
for n in gimp soffice.bin chrome; do P[$n]=$(pgrep -x -n $n); done
for n in "${!P[@]}"; do p=${P[$n]}; [ -n "$p" ] && echo "$1 $n pid=$p appmenu mapped: $(grep -c libappmenu-gtk-module /proc/$p/maps 2>/dev/null)"; done
gsettings set $K overrides "{'Gtk/Modules': <''>}"; echo "$1 --- module dropped"; sleep 10
gsettings set $K overrides "{'Gtk/Modules': <'appmenu-gtk-module'>}"; echo "$1 --- module added back"; sleep 10
for n in "${!P[@]}"; do p=${P[$n]}; [ -n "$p" ] && { [ -d /proc/$p ] && echo "$1 $n ALIVE" || echo "$1 $n DEAD"; }; done
ls /var/crash/*.crash 2>/dev/null | sed "s|^|$1 crash: |"
pkill -x gimp; pkill -x soffice.bin; pkill -f '[c]hromium'; sleep 3
gsettings reset $K overrides
