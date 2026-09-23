#!/bin/sh
# Xorg + dummy driver: nux needs XFree86-VidModeExtension, which Xvfb lacks.
export HOME=/tmp LIBGL_ALWAYS_SOFTWARE=1 DISPLAY=:99
Xorg :99 -config /dummy.conf -noreset -nolisten tcp -logfile /tmp/Xorg.log >/dev/null 2>&1 &
X=$!
for i in $(seq 50); do xdpyinfo >/dev/null 2>&1 && break; sleep 0.2; done
xdpyinfo -queryExtensions | grep -c VidMode
cd /src/obj/tests
timeout 900 dbus-run-session -- ./test-gnome-session-manager "$@"
rc=$?; kill $X; exit $rc
