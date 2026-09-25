#!/bin/sh
# A/B screenshots of GTK apps: old gtk-nocsd (/tmp/nocsd-u2) vs the installed one.
# nocsd-ab.sh <outdir>
. ~/envt.sh
OUT=$1; rm -rf $OUT; mkdir -p $OUT
APPS="nemo:nemo --no-desktop /usr/share
yelp:yelp
seahorse:seahorse
ucc:unity-control-center
gte:gnome-text-editor
chars:gnome-characters
disks:gnome-disks
froller:file-roller
scan:simple-scan
transm:transmission-gtk
zen-chooser:zenity --file-selection
zen-question:zenity --question --text=Test
upd:software-properties-gtk"
echo "$APPS" | while IFS=: read tag cmd; do
  for v in old new; do
    LIB=libgtk-nocsd.so.0; [ $v = old ] && LIB=/tmp/nocsd-u2/libgtk-nocsd.so.0
    systemd-run --user -q --unit=ab-$tag-$v -E LD_PRELOAD=libunity-gtk4-menu.so.0:$LIB $cmd
    sleep 6
    P=$(systemctl --user show -p MainPID --value ab-$tag-$v)
    M=$(grep -m1 -o '/[^ ]*nocsd[^ ]*' /proc/$P/maps 2>/dev/null)
    echo "$tag $v pid=$P lib=$M active=$(xdotool getactivewindow getwindowname 2>/dev/null)"
    gnome-screenshot -f $OUT/$tag-$v.png 2>/dev/null
    systemctl --user stop ab-$tag-$v 2>/dev/null; systemctl --user reset-failed ab-$tag-$v 2>/dev/null
    sleep 2
  done
done
