#!/bin/bash
# reboot-probe.sh LABEL OUT - reboot target2, wait for the X session, run probe.sh.
label=$1 out=$2
ssh target2 'sudo systemctl reboot' </dev/null
sleep 30
until ssh -o ConnectTimeout=5 target2 'pidof -s compiz >/dev/null || pidof -s xfwm4 >/dev/null' 2>/dev/null; do sleep 10; done
sleep 20
ssh target2 "~/probe.sh '$label'" </dev/null | tee "$out"
