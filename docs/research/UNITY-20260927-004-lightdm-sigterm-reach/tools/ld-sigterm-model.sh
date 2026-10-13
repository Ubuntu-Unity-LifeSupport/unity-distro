#!/bin/sh
# UNITY-20260927-004: the no-child branch of signal_cb() with the signal
# landing inside malloc, deterministically, on the greeter's session-child of
# the installed lightdm (stock: needs its debug info from debuginfod).
# Based on research/lightdm-sigterm-exit/runs/ld-sigterm.sh: gdb sets
# child_pid = 0 (as after waitpid) and, with LOCK=1, takes main_arena.mutex
# (as when SIGTERM interrupts malloc); then SIGTERM. tools/ld-fini-free.bt,
# attached to that process only, records the destructors that run.
# Run as root with the greeter up. Usage: ld-sigterm-model.sh OUTDIR LOCK
set -u
D=${1:?outdir}; LOCK=${2:?0 or 1}; mkdir -p "$D"
log() { echo "$(date +%T.%3N) $*" >> "$D/steps"; }
S=$(loginctl list-sessions --no-legend | awk '$3=="lightdm" && $4=="seat0"{print $1}')
SC=$(loginctl show-session "$S" -p Leader --value)
log "lightdm $(dpkg-query -W -f='${Version}' lightdm); greeter session $S, session-child $SC: $(tr '\0' ' ' < /proc/$SC/cmdline); GLIBC_TUNABLES=$(tr '\0' '\n' < /proc/$SC/environ | grep ^GLIBC_TUNABLES= | cut -d= -f2-)"
cp /proc/$SC/maps "$D/maps"
# child_pid is a static gdb will not take the address of; read its offset
# from the code of signal_cb (as the 2026-09 script does).
FN=$(gdb -q -batch -iex "set debuginfod enabled on" -ex "info line session-child.c:163" /usr/sbin/lightdm 2>/dev/null | grep -o "0x[0-9a-f]* <signal_cb" | head -1 | cut -d" " -f1)
OFF=$(gdb -q -batch -iex "set debuginfod enabled on" -ex "disassemble $FN,+32" /usr/sbin/lightdm 2>/dev/null | grep -o "# 0x[0-9a-f]* <child_pid>" | head -1 | cut -d" " -f2)
BASE=0x$(grep -m1 "/usr/sbin/lightdm" /proc/$SC/maps | cut -d- -f1)
[ -n "$FN" ] && [ -n "$OFF" ] || { log "ABORT: child_pid not located, test not valid"; exit 1; }
ADDR=$(printf "0x%x" $((BASE + OFF)))
log "signal_cb $FN, child_pid offset $OFF, address $ADDR"
bpftrace -p "$SC" /home/mike/ld-fini-free.bt > "$D/fini.txt" 2>&1 &
sleep 6
{
  echo "print *(int *)$ADDR"; echo "set var *(int *)$ADDR = 0"; echo "print *(int *)$ADDR"
  echo "print main_arena.mutex"
  [ "$LOCK" = 1 ] && echo "set var main_arena.mutex = 1"
  echo "print main_arena.mutex"; echo "detach"
} > "$D/gdb-cmds"
timeout 300 gdb -q -batch -iex "set debuginfod enabled on" -p $SC -x "$D/gdb-cmds" > "$D/gdb-set.txt" 2>&1
grep -E "^\\$|No symbol" "$D/gdb-set.txt" >> "$D/steps"
grep -q "No symbol" "$D/gdb-set.txt" && { log "ABORT: symbol missing, test not valid"; kill -9 $SC; exit 1; }
T0=$(date +%s.%N)
kill -TERM $SC
for i in $(seq 1 20); do kill -0 $SC 2>/dev/null || break; sleep 0.5; done
if kill -0 $SC 2>/dev/null; then
  log "session-child $SC STILL ALIVE 10 s after SIGTERM: state $(awk '/^State/{print $2}' /proc/$SC/status) wchan $(cat /proc/$SC/wchan)"
  timeout 120 gdb -q -batch -iex "set debuginfod enabled on" -p $SC -ex "bt 16" 2>&1 | grep -E "^#" > "$D/stuck-bt.txt"
  head -16 "$D/stuck-bt.txt" | cut -c1-140 >> "$D/steps"
  kill -9 $SC
else
  log "session-child $SC exited $(echo "$(date +%s.%N) - $T0" | bc | cut -c1-5) s after SIGTERM"
fi
sleep 2
