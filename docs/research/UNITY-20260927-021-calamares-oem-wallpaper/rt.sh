#!/bin/bash
# rt.sh DEB [ROUNDS] - regression reproduction for the OEM wallpaper stacking bug.
# Runs as root inside the b-dev chroot (Xvfb, xfwm4 4.20, Calamares 3.3.14).
# Unpacks the Ubuntu Unity oemconfig.tar.gz from DEB (calamares-settings-
# ubuntu-unity) into /tmp/rt-cfg and runs the end-user OEM session on Xvfb :7
# in the order of start-ubuntu-unity-oem-env, with that package's
# basicwallpaper. Pixel 700,200: #EFEFEF = Calamares, #464625 = wallpaper.
# Cases: 1 session start; 2 Alt+Tab twice; 3 wallpaper started 15 s after
# Calamares. Prints one line per case and the window type/state of the
# wallpaper.
set -u
deb=$1 rounds=${2:-1}
export DISPLAY=:7
rm -rf /tmp/rt-cfg /tmp/rt-deb; mkdir -p /tmp/rt-cfg /tmp/rt-deb
dpkg-deb -x "$deb" /tmp/rt-deb
tar xzf /tmp/rt-deb/etc/calamares/oemconfig.tar.gz -C /tmp/rt-cfg --strip-components=2
WP=/tmp/rt-cfg/usr/bin/basicwallpaper
# Calamares config as the OEM session sees it: the installed /etc/calamares
# with the oemconfig's etc/calamares laid over it (calamares-oemprep.sh), and
# the qml directory Calamares requires from /usr/share/calamares.
CFG=/tmp/rt-calcfg; rm -rf $CFG; mkdir -p $CFG
cp -a /etc/calamares/. $CFG/; cp -a /tmp/rt-cfg/etc/calamares/. $CFG/
[ -e $CFG/qml ] || ln -s /usr/share/calamares/qml $CFG/qml
IMG=/usr/share/backgrounds/ubuntu-unity/ubuntu-unity-default.png
pgrep -x Xvfb >/dev/null || true
echo "deb: $(basename "$deb") basicwallpaper sha256: $(sha256sum $WP | cut -c1-16)"
pgrep -x Xvfb >/dev/null || { Xvfb :7 -screen 0 1280x800x24 >/tmp/rt-xvfb.log 2>&1 & sleep 2; }
top() { import -window root -crop 1x1+700+200 txt:- | tail -1 | grep -o '#[0-9A-F]*' | cut -c1-7; }
who() { case $(top) in '#EFEFEF') echo calamares;; '#464625') echo WALLPAPER;; *) echo "other($(top))";; esac; }
wpinfo() { w=$(xdotool search --class basicwallpaper 2>/dev/null | tail -1); [ -n "$w" ] && xprop -id "$w" _NET_WM_WINDOW_TYPE _NET_WM_STATE | tr '\n' ' '; }
clean() { pkill -x calamares; pkill -x basicwallpaper; pkill -x xfwm4; sleep 2; }
for r in $(seq "$rounds"); do
  clean
  setsid dbus-run-session bash -c "xfwm4 >/dev/null 2>&1 & $WP $IMG >/dev/null 2>&1 & calamares -D8 -c $CFG >/tmp/rt-cal.log 2>&1" </dev/null >/dev/null 2>&1 &
  sleep 20; c1=$(who); info=$(wpinfo); cw=$(xdotool search --onlyvisible --class calamares 2>/dev/null | wc -l)
  xdotool key alt+Tab; sleep 2; c2a=$(who); xdotool key alt+Tab; sleep 2; c2b=$(who)
  clean
  setsid dbus-run-session bash -c "xfwm4 >/dev/null 2>&1 & sleep 1; calamares -D8 -c $CFG >/tmp/rt-cal.log 2>&1 & sleep 15; $WP $IMG >/dev/null 2>&1" </dev/null >/dev/null 2>&1 &
  sleep 20; c3=$(who); cw3=$(xdotool search --onlyvisible --class calamares 2>/dev/null | wc -l)
  clean
  echo "round $r: calamares windows visible: $cw/$cw3 | 1 start=$c1 | 2 alt+tab=$c2a,$c2b | 3 late wallpaper=$c3 | wallpaper: $info"
done
