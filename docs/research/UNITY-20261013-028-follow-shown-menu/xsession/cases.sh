#!/bin/bash
# cases.sh - the 52unity-gtk4-menu prototype sourced by dash after the installed 51gtk-nocsd, as Xsession runs them
# (STARTUP as 50x11-common_determine-startup leaves it), on target2 as mike. Opt-outs go through a scratch
# XDG_CONFIG_HOME, so ~/.config is not touched. `cases.sh PROTOTYPE removed` adds the removal cases R and R2. Prints LD_PRELOAD and STARTUP after each script.
P=${1:-$HOME/b039/52unity-gtk4-menu}
run() { # $1 name, $2 LD_PRELOAD ("-" = unset), $3 with51 (1/0), $4 opt-outs in the scratch config (50, 60)
  local cfg; cfg=$(mktemp -d); mkdir -p "$cfg/environment.d"
  for o in $4; do : > "$cfg/environment.d/$o-$( [ $o = 50 ] && echo gtk-nocsd || echo unity-gtk4-menu).conf"; done
  echo "== $1"
  env -i HOME="$HOME" XDG_CONFIG_HOME="$cfg" XDG_RUNTIME_DIR="$XDG_RUNTIME_DIR" PATH=/usr/bin:/bin \
    DBUS_SESSION_BUS_ADDRESS="$DBUS_SESSION_BUS_ADDRESS" PRE="$2" W51="$3" P="$P" dash -c '
    [ "$PRE" = - ] || { LD_PRELOAD=$PRE; export LD_PRELOAD; }
    STARTUP=x-session-manager
    if [ "$W51" = 1 ]; then . /etc/X11/Xsession.d/51gtk-nocsd; echo "  after 51: LD_PRELOAD=${LD_PRELOAD-<unset>} | STARTUP=$STARTUP"; fi
    . "$P"
    echo "  after 52: LD_PRELOAD=${LD_PRELOAD-<unset>} | STARTUP=$STARTUP"
    env | grep -q "^LD_PRELOAD=" && echo "  exported: yes" || echo "  exported: no"
    set | grep -E "^_(ugm|nocsd)_" | sed "s/^/  leftover: /"'
  rm -rf -- "${cfg:?}"
}
echo "user manager: $(systemctl --user show-environment | sed -n 's/^LD_PRELOAD=//p')"
run "A control: no session LD_PRELOAD" - 1 ""
run "B the -039 case: ~/.xsessionrc libm" libm.so.6 1 ""
run "C libm, gtk-nocsd turned off by the user" libm.so.6 1 "50"
run "D libm, no 51gtk-nocsd (gtk-nocsd not installed)" libm.so.6 0 ""
run "E libm, unity-gtk4-menu turned off by the user" libm.so.6 1 "60"
run "F ours already there, bare, from an old ~/.xsessionrc" libunity-gtk4-menu.so.0:libm.so.6 1 ""
run "G two entries separated by a space" "libm.so.6 libdl.so.2" 1 ""
run "H no session LD_PRELOAD, no 51gtk-nocsd" - 0 ""
run "I ours twice, once behind gtk-nocsd" "libm.so.6:/usr/\$LIB/libunity-gtk4-menu.so.0:libunity-gtk4-menu.so.0" 1 ""
run "J ours first already, no 51gtk-nocsd" "/usr/\$LIB/libunity-gtk4-menu.so.0:libm.so.6" 0 ""
# R, R2: the package removed (not purged). The environment.d file is moved away for these two runs and put back;
# R2's entry of ours comes from 51 importing the running user manager, started while the file existed.
if [ "${2-}" = removed ]; then
  f=/usr/lib/environment.d/60-unity-gtk4-menu.conf
  sudo mv $f /tmp/60.saved && {
    run "R removed (no 60-unity-gtk4-menu.conf), libm" libm.so.6 1 ""
    run "R2 removed, no session LD_PRELOAD" - 1 ""
    sudo mv /tmp/60.saved $f; }
  ls -l $f
fi
