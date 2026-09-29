#!/usr/bin/env python3
"""UNITY-20260928-019: print the last N records of /var/log/wtmp (glibc
struct utmp, 384 bytes on x86_64): type, pid, line, id, user, time (UTC).
Types: 7 USER_PROCESS, 8 DEAD_PROCESS. Usage: wtmp-tail.py [N]"""
import struct, sys, time

N = int(sys.argv[1]) if len(sys.argv) > 1 else 6
FMT = "<hxxi32s4s32s256shhiii4i20s"
SIZE = struct.calcsize(FMT)
data = open("/var/log/wtmp", "rb").read()
recs = [data[i:i + SIZE] for i in range(0, len(data) - SIZE + 1, SIZE)]
for r in recs[-N:]:
    t, pid, line, ident, user, host, _, _, _, sec, usec, *_ = struct.unpack(FMT, r)
    s = lambda b: b.split(b"\0", 1)[0].decode(errors="replace")
    print(f"type={t} pid={pid} line={s(line)!r} id={s(ident)!r} user={s(user)!r} "
          f"time={time.strftime('%H:%M:%SZ', time.gmtime(sec))}")
