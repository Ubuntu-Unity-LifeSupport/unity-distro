#!/bin/bash
# crash081.sh N - which preload makes showtime and Apostrophe write a crash report: each app is started N times
# per condition, as breadth-any.sh starts it (session environment, audit after 7 s, then SIGTERM), and after
# each start the app's own stderr is searched for a Python traceback and /var/crash for a new or updated report.
# Conditions: no preload (LD_PRELOAD emptied), the packaged library, S (our series, GTK_NOCSD_GLOBAL_MENU=1),
# U (b76f3fb, GTK_NOCSD_MENU=1), U without the variable. The packaged library is put back at the end.
set -u
n=${1:-3}
S=~/b081/nocsd-60ec176/libgtk-nocsd.so.0
U=~/b081/nocsd-b76f3fb/libgtk-nocsd.so.0
PKG=~/b081/libgtk-nocsd.so.0.pkg
T=/usr/lib/x86_64-linux-gnu/libgtk-nocsd.so.0
export DISPLAY=:0
mapfile -d '' e < /proc/$(pgrep -x compiz)/environ
export $(tr '\0' '\n' < /proc/$(pgrep -x compiz)/environ | grep '^DBUS_SESSION_BUS_ADDRESS=')
stamp() { stat -c '%Y' /var/crash/_usr_bin_$1.1000.crash 2>/dev/null || echo 0; }
# keep the reports of the earlier runs, and start with none for these two apps, so every new one shows
mkdir -p ~/b081/crash-before
for a in showtime apostrophe; do
  f=/var/crash/_usr_bin_$a.1000.crash
  [ -f "$f" ] && sudo -n cp -p "$f" ~/b081/crash-before/ && sudo -n rm -f "$f"
done
for v in "none:$PKG:LD_PRELOAD=" "pkg:$PKG:" "S-on:$S:GTK_NOCSD_GLOBAL_MENU=1" "U-on:$U:GTK_NOCSD_MENU=1" "U-off:$U:"; do
  IFS=: read name lib extra <<<"$v"
  sudo -n cp "$lib" $T.new && sudo -n mv $T.new $T
  for app in showtime apostrophe; do
    tb=0; rep=0
    for i in $(seq "$n"); do
      pkill -x "$app"; sleep 1
      s0=$(stamp $app)
      setsid env -i "${e[@]}" $extra $app > /tmp/c081-$app.out 2>&1 < /dev/null & pid=$!
      sleep 7
      python3 ~/b/audit.py $pid > /dev/null 2>&1
      kill $pid 2>/dev/null; sleep 3; kill -9 $pid 2>/dev/null
      grep -q "Traceback" /tmp/c081-$app.out && tb=$((tb+1)) && grep -m1 -E "Error|error:" /tmp/c081-$app.out | cut -c1-120 > /tmp/c081-$app-$name.err
      [ "$(stamp $app)" != "$s0" ] && rep=$((rep+1))
    done
    echo "$name $app: traceback in stderr $tb/$n, crash report written $rep/$n $(cat /tmp/c081-$app-$name.err 2>/dev/null)"
  done
done
for a in showtime apostrophe; do pkill -x $a; done
sudo -n cp "$PKG" $T.new && sudo -n mv $T.new $T
echo "packaged library restored: $(sha256sum $T | cut -c1-16); dpkg -V: $(dpkg -V libgtk-nocsd0 | wc -l) lines"
