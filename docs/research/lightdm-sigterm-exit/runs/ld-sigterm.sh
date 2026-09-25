#!/bin/sh
# LP #2168421, deterministic: the greeter's session-child gets SIGTERM with
# no child to pass it to (child_pid = 0) while the malloc arena lock is held
# (main_arena.mutex = 1), as when the signal lands inside malloc().
# Run as root (systemd-run). Usage: ld-sigterm.sh TAG
TAG=$1; D=/home/mike/ld/$TAG; mkdir -p $D
M="setpriv --reuid=mike --regid=mike --init-groups env HOME=/home/mike DISPLAY=:0 XAUTHORITY=/home/mike/.Xauthority"
log() { echo "$(date +%T.%3N) $*" >> $D/steps; }
sleep 10
log "lightdm $(dpkg-query -W -f='${Version}' lightdm)"
$M xdotool key ctrl+alt+Delete; sleep 3; $M xdotool mousemove 728 458 click 1
sleep 30
G=$(pgrep -u lightdm -f 'greeter' | head -1)
SC=$(ps -o ppid= -p $G | tr -d ' ')
log "greeter pid $G, its session-child $SC: $(ps -o user=,args= -p $SC)"
# child_pid is a static in session-child.c that gdb will not take the address
# of; read its offset from the code of session-child's signal_cb instead.
FN=$(gdb -q -batch -ex "info line session-child.c:163" /usr/sbin/lightdm 2>/dev/null | grep -o "0x[0-9a-f]* <signal_cb" | head -1 | cut -d" " -f1)
OFF=$(gdb -q -batch -ex "disassemble $FN,+32" /usr/sbin/lightdm 2>/dev/null | grep -o "# 0x[0-9a-f]* <child_pid>" | head -1 | cut -d" " -f2)
BASE=0x$(grep -m1 "/usr/sbin/lightdm" /proc/$SC/maps | cut -d- -f1)
ADDR=$(printf "0x%x" $((BASE + OFF)))
log "signal_cb $FN, child_pid offset $OFF, base $BASE, address $ADDR"
[ -n "$FN" ] && [ -n "$OFF" ] || { log "ABORT: child_pid not located, test not valid"; systemctl restart lightdm; exit 0; }
timeout 300 gdb -q -batch -p $SC \
  -ex "print *(int *)$ADDR" -ex "set var *(int *)$ADDR = 0" -ex "print *(int *)$ADDR" \
  -ex "print main_arena.mutex" -ex "set var main_arena.mutex = 1" -ex "print main_arena.mutex" \
  -ex detach > $D/gdb-set.txt 2>&1
grep -E "^\\$|No symbol" $D/gdb-set.txt >> $D/steps
grep -q "No symbol" $D/gdb-set.txt && { log "ABORT: symbol missing, test not valid"; kill -9 $SC; systemctl restart lightdm; exit 0; }
T0=$(date +%s.%N)
kill -TERM $SC
for i in $(seq 1 20); do kill -0 $SC 2>/dev/null || break; sleep 0.5; done
if kill -0 $SC 2>/dev/null; then
  log "session-child $SC STILL ALIVE 10 s after SIGTERM: state $(awk '/^State/{print $2}' /proc/$SC/status) wchan $(cat /proc/$SC/wchan)"
  timeout 120 gdb -q -batch -iex "set debuginfod enabled on" -p $SC -ex "bt 14" 2>&1 | grep -E "^#" > $D/stuck-bt.txt
  head -14 $D/stuck-bt.txt | cut -c1-120 >> $D/steps
  kill -9 $SC
else
  log "session-child $SC exited $(echo "$(date +%s.%N) - $T0" | bc | cut -c1-5) s after SIGTERM"
fi
systemctl restart lightdm; sleep 60
log "after lightdm restart: seat0=$(loginctl list-sessions --no-legend | awk '$4=="seat0"{print $1"/"$3}')"
chown -R mike:mike /home/mike/ld
