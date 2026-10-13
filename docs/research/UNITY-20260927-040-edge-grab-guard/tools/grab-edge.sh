#!/bin/bash
# UNITY-20260927-040 (agent A): a left click on an xterm's right border while
# a compiz grab other than a mouse-driven move/resize is running - the
# unknowns of UNITY-20260927-001. Real evdev devices only (tablet places the
# pointer, PS/2 mouse clicks, AT keyboard types), no XTEST.
#   kbdresize  Alt+F8 (resize, keyboard-initiated), click on the border,
#              Right x3, Enter
#   kbdresize-esc  same, ends with Escape
#   kbdresize-drag, kbdmove-drag  Alt+F8 / Alt+F7, tablet back to the
#              border position, click there, Enter
#   kbdmove    Alt+F7 (move, keyboard-initiated), click on the border,
#              Right x3, Enter
#   expo-border  Super+S (expo), click where the border is, Escape
#   expo-altf8-border  same, with Alt+F8 pressed in expo before the click
#   expo-control  same, click 80 px right of the border (no decoration)
#   expo-dnd-border  a big window on viewport (1,0) under the border point in
#              expo (expo drag-and-drop), expo, click on the border, Escape
#   expo-dnd-control  same, click 80 px right (thumbnail, no decoration)
#   expo-twice  expo, click on the border, expo again, click there again
#   expo-twice-control  same, second click 80 px right (no decoration)
#   expo       (first version) Super+S, click on the border, Super+S again -
#              the click already leaves expo, so this re-enters it
#   expo-esc   (first version) same, leaves expo with Escape
# Prints the grab state while the operation runs and after it, the xterm
# geometry before/after, and whether a real click then reaches the sensor.
# Run as mike in the session, with tools/uprobetrace-040.sh around it.
# usage: grab-edge.sh VARIANT
. ~/envt.sh; V=$1
# VP=X,Y (default 0,0): the viewport the run starts on; the xterm is moved
# into it, so in expo the click lands in the thumbnail of the current one
VPX=${VP%%,*}; VPY=${VP##*,}; [ -z "$VP" ] && { VPX=0; VPY=0; }
# NOVP=1 skips it (tools/replay-stuck1.sh: the first stuck run had no reset)
[ -z "$NOVP" ] && { xdotool set_desktop_viewport $VPX $VPY; sleep 0.8; }
node() { grep -l "$1" /sys/class/input/event*/device/name | head -1 | cut -d/ -f5; }
T=/dev/input/$(node "USB Tablet"); M=/dev/input/$(node "ImExPS/2"); K=/dev/input/$(node "AT Translated")
W=$(xdotool search --onlyvisible --class '^XTerm$' | head -1)
[ -z "$W" ] && { (setsid nohup xterm -title rtarget >/dev/null 2>&1 &); sleep 2; W=$(xdotool search --onlyvisible --class '^XTerm$' | head -1); }
xdotool windowactivate --sync $W; xdotool windowmove $W 500 200 windowsize $W 400 300; sleep 0.7
eval $(xdotool getwindowgeometry --shell $W)
before="${WIDTH}x${HEIGHT}+$X+$Y"
R=$(xprop -id $W _NET_FRAME_EXTENTS | grep -oE "[0-9]+, [0-9]+, [0-9]+, [0-9]+" | cut -d, -f2 | tr -d ' ')
bx=$((X + WIDTH + ${R:-0} / 2 + 1)); by=$((Y + HEIGHT / 2))
sudo ~/evclick.py $T $bx $by none; sleep 0.3
case $V in
  kbdresize|kbdresize-esc)
    sudo ~/evkeys.py $K 'down LEFTALT' 'tap F8' 'up LEFTALT' 'sleep 1'
    pos=$(xdotool getmouselocation | cut -d' ' -f1,2)
    sudo ~/evseq.py $M 'down left' 'sleep 0.3' 'up left' 'sleep 0.5'
    during=$(~/grab-probe)
    if [ $V = kbdresize ]; then sudo ~/evkeys.py $K 'tap RIGHT' 'tap RIGHT' 'tap RIGHT' 'sleep 0.3' 'tap ENTER' 'sleep 1'
    else sudo ~/evkeys.py $K 'tap RIGHT' 'sleep 0.3' 'tap ESC' 'sleep 1'; fi ;;
  kbdresize-drag|kbdmove-drag)
    # compiz warps the pointer into the window for a keyboard move/resize;
    # bring it back to where the right border is with the tablet (this
    # motion resizes/moves the window), then click there
    [ $V = kbdresize-drag ] && k=F8 || k=F7
    sudo ~/evkeys.py $K 'down LEFTALT' "tap $k" 'up LEFTALT' 'sleep 1'
    # BX_OFFSET (tools/replay-stuck1.sh noborder): click that far right of it
    sudo ~/evclick.py $T $((bx + ${BX_OFFSET:-0})) $by none; sleep 0.5
    pos=$(xdotool getmouselocation | cut -d' ' -f1,2)
    eval $(xdotool getwindowgeometry --shell $W); pos="$pos xterm-now ${WIDTH}x${HEIGHT}+$X+$Y"
    sudo ~/evseq.py $M 'down left' 'sleep 0.3' 'up left' 'sleep 0.5'
    during=$(~/grab-probe)
    sudo ~/evkeys.py $K 'tap ENTER' 'sleep 1' ;;
  kbdmove)
    sudo ~/evkeys.py $K 'down LEFTALT' 'tap F7' 'up LEFTALT' 'sleep 1'
    pos=$(xdotool getmouselocation | cut -d' ' -f1,2)
    sudo ~/evseq.py $M 'down left' 'sleep 0.3' 'up left' 'sleep 0.5'
    during=$(~/grab-probe)
    sudo ~/evkeys.py $K 'tap RIGHT' 'tap RIGHT' 'tap RIGHT' 'sleep 0.3' 'tap ENTER' 'sleep 1' ;;
  expo-border|expo-altf8-border|expo-control)
    # In expo (2x2 viewports) the real border position of the xterm lies in
    # the thumbnail of viewport (1,0); the decoration's input windows stay at
    # their real positions. expo-control clicks 80 px right of the border,
    # the same thumbnail but no decoration. expo-altf8-border presses Alt+F8
    # in expo first (refused by resize while expo holds its grab).
    sudo ~/evkeys.py $K 'down LEFTMETA' 'sleep 0.3' 'tap S' 'sleep 0.3' 'up LEFTMETA' 'sleep 1.5'
    [ $V = expo-altf8-border ] && sudo ~/evkeys.py $K 'down LEFTALT' 'tap F8' 'up LEFTALT' 'sleep 1'
    [ $V = expo-control ] && cx=$((bx + 80)) || cx=$bx
    sudo ~/evclick.py $T $cx $by none; sleep 0.3
    pos=$(xdotool getmouselocation | cut -d' ' -f1,2)
    sudo ~/evseq.py $M 'down left' 'sleep 0.2' 'up left' 'sleep 1.5'
    during=$(~/grab-probe)
    sudo ~/evkeys.py $K 'tap ESC' 'sleep 1.5'
    xdotool set_desktop_viewport $VPX $VPY; sleep 1 ;;
  expo-dnd-border|expo-dnd-control)
    # A window on viewport (1,0) whose expo thumbnail lies under the real
    # border position (1100x700 at 100,50 of that viewport), so the press in
    # expo lands on a window thumbnail (expo drag-and-drop) and - for the
    # border variant - also on the xterm's decoration input window.
    # class Cover and no shell, so it keeps its name and is not the XTerm above
    CW=$(xdotool search --class '^Cover$' | head -1)
    [ -z "$CW" ] && { (setsid nohup xterm -class Cover -title cover -e sleep infinity >/dev/null 2>&1 &); sleep 2; CW=$(xdotool search --class '^Cover$' | head -1); }
    xdotool windowsize $CW 1100 700 windowmove $CW $((1280 + 100)) 50; sleep 0.7
    xdotool windowactivate --sync $W; sleep 0.5
    sudo ~/evkeys.py $K 'down LEFTMETA' 'sleep 0.3' 'tap S' 'sleep 0.3' 'up LEFTMETA' 'sleep 1.5'
    [ $V = expo-dnd-control ] && cx=$((bx + 80)) || cx=$bx
    sudo ~/evclick.py $T $cx $by none; sleep 0.3
    pos=$(xdotool getmouselocation | cut -d' ' -f1,2)
    sudo ~/evseq.py $M 'down left' 'sleep 0.2' 'up left' 'sleep 1.5'
    during=$(~/grab-probe)
    sudo ~/evkeys.py $K 'tap ESC' 'sleep 1.5'
    xdotool set_desktop_viewport $VPX $VPY; sleep 1 ;;
  expo-twice|expo-twice-control)
    # the sequence of the first stuck run (runs/t-expo-1, t-kbdresize-drag-1):
    # expo, click on the border (expo leaves to viewport (1,0) - the xterm
    # stays on (0,0)), expo again from there, click at the same place again
    # (expo-twice-control: 80 px right of it, no decoration there)
    sudo ~/evkeys.py $K 'down LEFTMETA' 'sleep 0.3' 'tap S' 'sleep 0.3' 'up LEFTMETA' 'sleep 1.5'
    sudo ~/evseq.py $M 'down left' 'sleep 0.2' 'up left' 'sleep 2'
    first="vp after first click: $(xdotool get_desktop_viewport)"
    sudo ~/evkeys.py $K 'down LEFTMETA' 'sleep 0.3' 'tap S' 'sleep 0.3' 'up LEFTMETA' 'sleep 1.5'
    [ $V = expo-twice-control ] && sudo ~/evclick.py $T $((bx + 80)) $by none && sleep 0.3
    pos="$first; pointer $(xdotool getmouselocation | cut -d' ' -f1,2)"
    sudo ~/evseq.py $M 'down left' 'sleep 0.2' 'up left' 'sleep 1.5'
    during=$(~/grab-probe)
    sudo ~/evkeys.py $K 'tap ESC' 'sleep 1.5'
    xdotool set_desktop_viewport $VPX $VPY; sleep 1 ;;
  expo|expo-esc)
    sudo ~/evkeys.py $K 'down LEFTMETA' 'sleep 0.3' 'tap S' 'sleep 0.3' 'up LEFTMETA' 'sleep 1.5'
    pos=$(xdotool getmouselocation | cut -d' ' -f1,2)
    sudo ~/evclick.py $T $bx $by left; sleep 1
    during=$(~/grab-probe)
    if [ $V = expo ]; then sudo ~/evkeys.py $K 'down LEFTMETA' 'sleep 0.3' 'tap S' 'sleep 0.3' 'up LEFTMETA' 'sleep 1.5'
    else sudo ~/evkeys.py $K 'tap ESC' 'sleep 1.5'; fi ;;
esac
after=$(~/grab-probe)
eval $(xdotool getwindowgeometry --shell $W)
echo "$V vp=$VPX,$VPY border@$bx,$by xterm $before -> ${WIDTH}x${HEIGHT}+$X+$Y | pointer before click: $pos | during: $during | after: $after | $(~/clickcheck.sh)"
