#!/usr/bin/env python3
# Move the pointer to screen X,Y with the EXISTING absolute tablet evdev device
# and click BUTTON there - real device input, not XTEST (known issue #3, agent A).
# usage: sudo evclick.py /dev/input/eventN X Y [button: left|right|none] [W H]
import fcntl, struct, sys, time
dev, x, y = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
btn = sys.argv[4] if len(sys.argv) > 4 else "left"
W = int(sys.argv[5]) if len(sys.argv) > 5 else 1280; H = int(sys.argv[6]) if len(sys.argv) > 6 else 800
EV_SYN, EV_KEY, EV_ABS = 0, 1, 3; BTN = {"left": 0x110, "right": 0x111}
def absinfo(f, code):  # EVIOCGABS(code) = _IOR('E', 0x40 + code, struct input_absinfo)
    buf = fcntl.ioctl(f, 0x80184540 + code, b"\0" * 24); return struct.unpack("6i", buf)
def ev(t, c, v):
    s = time.time(); return struct.pack("llHHi", int(s), int((s % 1) * 1e6), t, c, v)
with open(dev, "r+b", buffering=0) as f:
    _, mnx, mxx, *_ = absinfo(f, 0); _, mny, mxy, *_ = absinfo(f, 1)
    ax = mnx + (mxx - mnx) * x // (W - 1); ay = mny + (mxy - mny) * y // (H - 1)
    for dx in (-3, 0):   # arrive with a real motion, then settle
        f.write(ev(EV_ABS, 0, ax + dx) + ev(EV_ABS, 1, ay) + ev(EV_SYN, 0, 0)); time.sleep(0.05)
    if btn in BTN:
        f.write(ev(EV_KEY, BTN[btn], 1) + ev(EV_SYN, 0, 0)); time.sleep(0.08)
        f.write(ev(EV_KEY, BTN[btn], 0) + ev(EV_SYN, 0, 0))
