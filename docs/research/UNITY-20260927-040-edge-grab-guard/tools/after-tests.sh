#!/bin/bash
# UNITY-20260927-040 (agent A): what A2 must not break - title-bar drags
# (GrabEdge's three paths into Edge::ButtonDownEvent), double-click, a title
# drag in expo, and the first border press right after a grab ended. Real
# evdev devices only. Traced with
# SCEN=after-tests.sh uprobetrace-040.sh VARIANT OUT. usage: after-tests.sh VARIANT
#   title-immediate  fixedwin (not maximizable): press on the title, move 60,30
#   title-hold       xterm: press on the title, hold 0.8 s, move 60,30
#   title-motion     xterm: press on the title, move 60,30 at once
#   title-dblclick   xterm: double-click on the title (maximize), again (restore)
#   expo-title       xterm: in expo, press on the title's real position, move
#   after-wall       Ctrl+Alt+Right, Ctrl+Alt+Left (wall slides), wait, then a
#                    plain border drag (+40 px)
#   after-expo       expo in and out (Escape), wait, then a plain border drag
. ~/envt.sh; V=$1
xdotool set_desktop_viewport 0 0; sleep 0.8
node() { grep -l "$1" /sys/class/input/event*/device/name | head -1 | cut -d/ -f5; }
T=/dev/input/$(node "USB Tablet"); M=/dev/input/$(node "ImExPS/2"); K=/dev/input/$(node "AT Translated")
W=$(xdotool search --onlyvisible --class '^XTerm$' | head -1)
[ -z "$W" ] && { (setsid nohup xterm -title rtarget >/dev/null 2>&1 &); sleep 2; W=$(xdotool search --onlyvisible --class '^XTerm$' | head -1); }
xdotool windowactivate --sync $W; xdotool windowmove $W 500 200 windowsize $W 400 300; sleep 0.7
geo() { eval $(xdotool getwindowgeometry --shell $1); echo "${WIDTH}x${HEIGHT}+$X+$Y"; }
maxst() { xprop -id $1 _NET_WM_STATE | grep -c MAXIMIZED_VERT; }
eval $(xdotool getwindowgeometry --shell $W)
TOP=$(xprop -id $W _NET_FRAME_EXTENTS | grep -oE "[0-9]+, [0-9]+, [0-9]+, [0-9]+" | cut -d, -f3 | tr -d " ")
RGT=$(xprop -id $W _NET_FRAME_EXTENTS | grep -oE "[0-9]+, [0-9]+, [0-9]+, [0-9]+" | cut -d, -f2 | tr -d ' ')
tx=$((X + WIDTH / 2 + 40)); ty=$((Y - ${TOP:-20} / 2))
bx=$((X + WIDTH + ${RGT:-0} / 2 + 1)); by=$((Y + HEIGHT / 2))
target=$W; extra=""
case $V in
  title-immediate)
    F=$(xdotool search --onlyvisible --name '^fixedwin$' | head -1)
    [ -z "$F" ] && { (setsid nohup ~/fixedwin.py >/dev/null 2>&1 &); sleep 2; F=$(xdotool search --onlyvisible --name '^fixedwin$' | head -1); }
    xdotool windowactivate --sync $F; xdotool windowmove $F 700 450; sleep 0.7
    eval $(xdotool getwindowgeometry --shell $F)
    FT=$(xprop -id $F _NET_FRAME_EXTENTS | grep -oE "[0-9]+, [0-9]+, [0-9]+, [0-9]+" | cut -d, -f3 | tr -d " ")
    extra="allowed-actions: $(xprop -id $F _NET_WM_ALLOWED_ACTIONS | grep -o 'MAXIMIZE_[A-Z]*' | paste -sd,)"
    target=$F; before=$(geo $F)
    sudo ~/evclick.py $T $((X + WIDTH / 2 + 40)) $((Y - ${FT:-20} / 2)) none; sleep 0.3
    sudo ~/evseq.py $M 'down left' 'move 60 30 6' 'sleep 0.2' 'up left' 'sleep 0.8' ;;
  title-hold)
    before=$(geo $W); sudo ~/evclick.py $T $tx $ty none; sleep 0.3
    sudo ~/evseq.py $M 'down left' 'sleep 0.8' 'move 60 30 6' 'sleep 0.2' 'up left' 'sleep 0.8' ;;
  title-motion)
    before=$(geo $W); sudo ~/evclick.py $T $tx $ty none; sleep 0.3
    sudo ~/evseq.py $M 'down left' 'move 60 30 6' 'sleep 0.2' 'up left' 'sleep 0.8' ;;
  title-dblclick)
    before="$(geo $W) max=$(maxst $W)"; sudo ~/evclick.py $T $tx $ty none; sleep 0.3
    sudo ~/evseq.py $M 'down left' 'up left' 'down left' 'up left' 'sleep 1.2'
    extra="max after 1st double-click: $(maxst $W)"
    eval $(xdotool getwindowgeometry --shell $W); sudo ~/evclick.py $T $((X + WIDTH / 2 + 40)) 12 none; sleep 0.3   # maximized: title in the panel
    sudo ~/evseq.py $M 'down left' 'up left' 'down left' 'up left' 'sleep 1.2'
    extra="$extra, after 2nd: $(maxst $W)" ;;
  expo-title)
    before=$(geo $W)
    sudo ~/evkeys.py $K 'down LEFTMETA' 'sleep 0.3' 'tap S' 'sleep 0.3' 'up LEFTMETA' 'sleep 1.5'
    sudo ~/evclick.py $T $tx $ty none; sleep 0.3
    sudo ~/evseq.py $M 'down left' 'move 60 30 6' 'sleep 0.2' 'up left' 'sleep 1.5'
    extra="during: $(~/grab-probe)"
    sudo ~/evkeys.py $K 'tap ESC' 'sleep 1.5'; xdotool set_desktop_viewport 0 0; sleep 1 ;;
  after-wall|after-expo)
    if [ $V = after-wall ]; then
      sudo ~/evkeys.py $K 'down LEFTCTRL' 'down LEFTALT' 'tap RIGHT' 'sleep 0.5' 'tap LEFT' 'up LEFTALT' 'up LEFTCTRL' 'sleep 1'
    else
      sudo ~/evkeys.py $K 'down LEFTMETA' 'sleep 0.3' 'tap S' 'sleep 0.3' 'up LEFTMETA' 'sleep 1.5' 'tap ESC' 'sleep 1'
    fi
    xdotool set_desktop_viewport 0 0; sleep 0.8
    extra="grabs before the press: $(~/grab-probe)"
    before=$(geo $W); sudo ~/evclick.py $T $bx $by none; sleep 0.3
    sudo ~/evseq.py $M 'down left' 'move 40 0 4' 'sleep 0.2' 'up left' 'sleep 0.8' ;;
esac
echo "$V $before -> $(geo $target) | $extra | after: $(~/grab-probe) | $(~/clickcheck.sh)"
