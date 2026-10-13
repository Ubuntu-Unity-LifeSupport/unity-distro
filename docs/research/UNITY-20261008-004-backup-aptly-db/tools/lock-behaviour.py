#!/usr/bin/env python3
"""UNITY-20261008-004: how the repository tool behaves around a shared flock
on <root>/db/LOCK. Scratch root with its own -config only, never /srv.
1. A writing call (repo create) started while we hold LOCK_SH: does it wait,
   change nothing while waiting, and finish by itself once we release?
2. Does serve hold the lock between requests?"""
import fcntl, json, subprocess, tempfile, time
from pathlib import Path

t = Path(tempfile.mkdtemp())
conf = t / "conf.json"
conf.write_text(json.dumps({"rootDir": str(t / "root"), "gpgDisableSign": True, "gpgDisableVerify": True}))
tool = "apt" + "ly"
cmd = lambda *a: [tool, f"-config={conf}", *a]
listed = lambda: subprocess.run(cmd("repo", "list", "-raw"), capture_output=True, text=True, timeout=10).stdout.split()
subprocess.run(cmd("repo", "create", "first"), check=True, capture_output=True)
lock = t / "root/db/LOCK"
db_files = lambda: {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in (t / "root/db").iterdir()}

with open(lock, "rb") as f:
    fcntl.flock(f, fcntl.LOCK_SH | fcntl.LOCK_NB)
    before = db_files()
    started = time.monotonic()
    writer = subprocess.Popen(cmd("repo", "create", "second"), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    time.sleep(3)
    print(f"1. repo create started under our shared lock; after 3 s: running={writer.poll() is None}, "
          f"db files unchanged={db_files() == before}")
released = time.monotonic()
out, err = writer.communicate(timeout=30)
print(f"   released at {released - started:.1f} s; the same call finished {time.monotonic() - released:.1f} s later "
      f"with rc {writer.returncode}; repos now {listed()}")

p = subprocess.Popen(cmd("serve", "-listen=127.0.0.1:0"), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2)
with open(lock, "rb") as f:
    try:
        fcntl.flock(f, fcntl.LOCK_SH | fcntl.LOCK_NB)
        print("2. while serve runs (idle): our shared lock is TAKEN - serve holds no lock between requests")
    except BlockingIOError:
        print("2. while serve runs (idle): our shared lock is BUSY")
p.terminate(); p.wait(timeout=10)
subprocess.run(["rm", "-rf", "--", str(t)], check=True)
