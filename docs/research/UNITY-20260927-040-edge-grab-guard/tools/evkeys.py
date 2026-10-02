#!/usr/bin/env python3
# Play real key presses into the EXISTING keyboard evdev device (not XTEST).
# UNITY-20260927-001 (agent A); keys for keyboard move/resize and expo added
# in UNITY-20260927-040.
# usage: sudo evkeys.py /dev/input/eventN 'down LEFTALT' 'tap F8' 'tap RIGHT' 'sleep 1' 'up LEFTALT'
import struct, sys, time
EV_SYN, EV_KEY = 0, 1
KEY = {"LEFTALT": 56, "TAB": 15, "ESC": 1, "F7": 65, "F8": 66, "ENTER": 28,
       "LEFTMETA": 125, "LEFTCTRL": 29, "S": 31, "E": 18, "RIGHT": 106, "LEFT": 105, "UP": 103, "DOWN": 108}
def ev(t, c, v):
    s = time.time(); return struct.pack("llHHi", int(s), int((s % 1) * 1e6), t, c, v)
with open(sys.argv[1], "wb", buffering=0) as f:
    for cmd in sys.argv[2:]:
        a = cmd.split()
        if a[0] in ("down", "up"):
            f.write(ev(EV_KEY, KEY[a[1]], 1 if a[0] == "down" else 0) + ev(EV_SYN, 0, 0)); time.sleep(0.05)
        elif a[0] == "tap":
            for v in (1, 0):
                f.write(ev(EV_KEY, KEY[a[1]], v) + ev(EV_SYN, 0, 0)); time.sleep(0.05)
        elif a[0] == "sleep":
            time.sleep(float(a[1]))
