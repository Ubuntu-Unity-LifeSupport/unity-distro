#!/bin/bash
# Log in through lightdm-gtk-greeter (manual login shown) on display $2 (default :0).
# Keyboard only, through XTEST, before the user's session exists. Agent A, #1 tests.
U=${1:-utest}; D=${2:-:0}; PW=utest-2604
X="sudo DISPLAY=$D XAUTHORITY=/var/run/lightdm/root/$D xdotool"
for i in $(seq 1 60); do $X search --onlyvisible --class lightdm-gtk-greeter >/dev/null 2>&1 && break; sleep 1; done
sleep 2; $X type --delay 60 "$U"; $X key Tab; sleep 0.5; $X type --delay 60 "$PW"; $X key Return
