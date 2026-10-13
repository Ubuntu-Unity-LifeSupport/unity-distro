#!/bin/bash
# envtools.sh TAG - on target2 in the Unity session (as mike over ssh): ways a value of LD_PRELOAD gets rebuilt from
# another form, starting from the session's own value (compiz's environment). For each case: the value that
# results (cat -A, so a literal $LIB, an empty expansion "/usr//" or "$'" quotes are visible), then t64 run with it:
# the dynamic loader's stderr lines and whether the two libraries are mapped.
set -u
B=~/b1302
tag=$1
cp=$(pgrep -x compiz | head -1)
export $(tr '\0' '\n' < /proc/$cp/environ | grep -E '^(DISPLAY|XAUTHORITY|DBUS_SESSION_BUS_ADDRESS|XDG_RUNTIME_DIR)=')
S=$(tr '\0' '\n' < /proc/$cp/environ | sed -n 's/^LD_PRELOAD=//p')
probe() {  # probe LABEL VALUE [set|unset]
  local v=$2 err out
  if [ "${3:-set}" = unset ]; then
    echo "  $1: LD_PRELOAD unset"; return
  fi
  out=$(LD_PRELOAD="$v" $B/t64 0 2>/tmp/env.err)
  echo "  $1: $(printf '%s' "$v" | cat -A | sed 's/\$$//' | head -1)"
  echo "      t64: ld.so lines $(grep -c 'ld.so' /tmp/env.err), $(printf '%s\n' "$out" | grep -o 'nocsd [-0-9]* gtk4-menu [-0-9]*')"
  grep 'ld.so' /tmp/env.err | sed 's/^/        /' | head -2
}
from_child() {  # the LD_PRELOAD a command prints, as the next probe's value; "unset" when the variable is absent
  local out; out=$("$@" 2>/dev/null)
  case $out in __UNSET__) echo unset ;; *) printf '%s' "$out" ;; esac
}
echo "== $tag at $(date -u +%FT%TZ), boot $(uptime -s); $(dpkg-query -W -f='libgtk-nocsd0 ${Version}, ' libgtk-nocsd0)$(dpkg-query -W -f='libunity-gtk4-menu0 ${Version}' libunity-gtk4-menu0)"
probe "0 the session's own value (compiz)" "$S"
SE=$(systemctl --user show-environment | grep '^LD_PRELOAD=')
echo "  (systemctl --user show-environment prints: $(printf '%s' "$SE" | cat -A | sed 's/\$$//'))"
v=$(env $SE sh -c 'printf %s "${LD_PRELOAD-__UNSET__}"');                       probe "1 env \$(systemctl --user show-environment)" "$v"
v=$(sh -c 'eval "export $1"; printf %s "${LD_PRELOAD-__UNSET__}"' sh "$SE");    probe "2a eval \"export <show-environment line>\" in dash" "$v"
v=$(bash -c 'eval "export $1"; printf %s "${LD_PRELOAD-__UNSET__}"' sh "$SE");  probe "2b eval \"export <show-environment line>\" in bash" "$v"
v=$(sh -c "LD_PRELOAD=$S; printf %s \"\$LD_PRELOAD\"");                         probe "3 a script that splices the value into code unquoted (sh -c \"X=\$LD_PRELOAD\")" "$v"
v=$(systemctl --user show-environment --output=json 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin).get("LD_PRELOAD",""), end="")' 2>/dev/null)
[ -n "$v" ] && probe "4 systemctl --user show-environment --output=json" "$v" || echo "  4 show-environment --output=json: not supported"
v=$(systemd-run --user --quiet --wait --pipe --collect sh -c 'printf %s "${LD_PRELOAD-__UNSET__}"' 2>/dev/null);  probe "5 a unit of the user manager (systemd-run --user)" "$v"
dbus-update-activation-environment --systemd LD_PRELOAD="$S" 2>/tmp/duae.err; echo "  6 dbus-update-activation-environment --systemd LD_PRELOAD=<session value>: rc $? $(cat /tmp/duae.err)"
v=$(systemd-run --user --quiet --wait --pipe --collect sh -c 'printf %s "${LD_PRELOAD-__UNSET__}"' 2>/dev/null);  probe "6 then a unit of the user manager" "$v"
LD_PRELOAD="$S" systemctl --user import-environment LD_PRELOAD; echo "  7 systemctl --user import-environment LD_PRELOAD: rc $?"
v=$(systemd-run --user --quiet --wait --pipe --collect sh -c 'printf %s "${LD_PRELOAD-__UNSET__}"' 2>/dev/null);  probe "7 then a unit of the user manager" "$v"
v=$(LD_PRELOAD="$S" sudo -n -E sh -c 'printf %s "${LD_PRELOAD-__UNSET__}"' 2>/dev/null); [ "$v" = __UNSET__ ] && probe "8 sudo -E" "" unset || probe "8 sudo -E" "$v"
v=$(LD_PRELOAD="$S" sudo -n --preserve-env=LD_PRELOAD sh -c 'printf %s "${LD_PRELOAD-__UNSET__}"' 2>/tmp/sudo.err); [ "$v" = __UNSET__ ] && probe "9 sudo --preserve-env=LD_PRELOAD" "" unset || probe "9 sudo --preserve-env=LD_PRELOAD" "$v"
grep -v '^$' /tmp/sudo.err | head -2 | sed 's/^/      sudo: /'
v=$(LD_PRELOAD="$S" sudo -n su -s /bin/sh -c 'printf %s "${LD_PRELOAD-__UNSET__}"' "$(id -un)" 2>/dev/null); [ "$v" = __UNSET__ ] && probe "10 su <user> -c (from root)" "" unset || probe "10 su <user> -c (from root)" "$v"
v=$(LD_PRELOAD="$S" sudo -n su - "$(id -un)" -s /bin/sh -c 'printf %s "${LD_PRELOAD-__UNSET__}"' 2>/dev/null); [ "$v" = __UNSET__ ] && probe "11 su - <user> (login shell, from root)" "" unset || probe "11 su - <user> (login shell, from root)" "$v"
tmux kill-server 2>/dev/null; LD_PRELOAD="$S" tmux new-session -d -s b1302 "sh -c 'printf %s \"\${LD_PRELOAD-__UNSET__}\" > /tmp/tmux.out; sleep 2'"; sleep 1
v=$(cat /tmp/tmux.out 2>/dev/null); probe "12 tmux new-session (server started with the value)" "$v"
echo "      tmux show-environment -g LD_PRELOAD: $(tmux show-environment -g LD_PRELOAD 2>&1 | cat -A | sed 's/\$$//')"
tmux kill-server 2>/dev/null
v=${LD_PRELOAD-__UNSET__}; [ "$v" = __UNSET__ ] && probe "13 this ssh session (sshd, PAM, no session environment)" "" unset || probe "13 this ssh session" "$v"
