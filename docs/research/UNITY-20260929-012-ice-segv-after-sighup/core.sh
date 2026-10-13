#!/bin/bash
# core.sh - on builder: the stack of the UNITY-20260929-012 core, without debug symbols (+unity3's were never
# published) and without gdb: the build-ids in the core, the deb they match, eu-stack, the caller found by the strings
# its code references, and the faulting instruction in libICE.
set -u
CRASH=~/work/a/040-build/crash/_usr_lib_x86_64-linux-gnu_cinnamon-session_cinnamon-session-binary.1000.crash
W=/srv/build/B-0929-012
BIN=$W/root/usr/lib/x86_64-linux-gnu/cinnamon-session/cinnamon-session-binary
echo "== crash file $CRASH (UNITY-20260927-040)"
grep -a -E "^(Date|ExecutablePath|ProcCmdline|Signal|SignalName|Uname|DistroRelease):" "$CRASH"
[ -f "$W/unpacked/CoreDump" ] || apport-unpack "$CRASH" "$W/unpacked"
echo; echo "== build-ids in the core (eu-unstrip -n --core)"
eu-unstrip -n --core="$W/unpacked/CoreDump" 2>/dev/null | grep -E "cinnamon-session-binary|libICE"
echo; echo "== cinnamon-session-binary build-id per published deb"
for d in $(find /srv/aptly/pool -name "*cinnamon-session_6.4.2*_amd64.deb" | sort); do
  rm -rf -- "${W:?}/x"; mkdir "$W/x"; dpkg-deb -x "$d" "$W/x"
  echo "  $(basename "$d" | sed 's/^[0-9a-f]*_//') $(readelf -n "$W/x/usr/lib/x86_64-linux-gnu/cinnamon-session/cinnamon-session-binary" | awk '/Build ID/{print $3}')"
done
rm -rf -- "${W:?}/x"
echo "  builder libICE.so.6 $(readelf -n /usr/lib/x86_64-linux-gnu/libICE.so.6 | awk '/Build ID/{print $3}') ($(dpkg-query -W -f='${Version}' libice6))"
if [ ! -f "$BIN" ]; then
  rm -rf -- "${W:?}/root"; mkdir "$W/root"
  dpkg-deb -x "$(find /srv/aptly/pool -name '*cinnamon-session_6.4.2-1+unity3_amd64.deb' | head -1)" "$W/root"
fi
echo; echo "== eu-stack, main thread"
eu-stack --core="$W/unpacked/CoreDump" -e "$BIN" -m 2>&1 | awk '/^TID/{n++} n==1'
echo; echo "== cinnamon-session-binary (+unity3) around the return address 0x2ab61 (frame 1, 0x61be2f6e7b61 - base 0x61be2f6bd000)"
objdump -d --no-show-raw-insn --start-address=0x2aa80 --stop-address=0x2ac60 "$BIN" | grep -E "lea .*rip|call"
echo; echo "== the strings at the addresses that code loads"
for a in 36b48 36b90 36be0 39570; do
  strings -t x "$BIN" | awk -v a="$a" 'strtonum("0x"$1) == strtonum("0x" a) {print "  0x" a ": " substr($0, index($0, $2))}'
done
echo; echo "== libICE.so.6 IceProcessMessages at the faulting pc 0x10f5c (frame 0, 0x7c837d4f3f5c - base 0x7c837d4e3000)"
objdump -d --no-show-raw-insn --start-address=0x10f40 --stop-address=0x10f70 /usr/lib/x86_64-linux-gnu/libICE.so.6 | tail -10
