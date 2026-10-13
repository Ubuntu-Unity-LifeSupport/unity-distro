"""UNITY-20261002-001 reproduction: two make_chroot() calls in the same second
(same stamp, same mtimes) give byte-identical tarballs."""
import hashlib, os, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[4] / "scripts/tests"))
import chroot_fixtures as cf

base = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR", "/tmp")))
stamp = cf.stamp_days_ago(1)
# freeze the clock: same stamp and mtimes, as when both calls land in one second
os.environ["SOURCE_DATE_EPOCH"] = "0"
real_run = subprocess.run
def run(cmd, **kw):
    if cmd[:1] == ["tar"]:
        cmd = cmd[:2] + ["--mtime=@1790000000", "--sort=name", "--owner=0", "--group=0"] + cmd[2:]
    return real_run(cmd, **kw)
cf.subprocess.run = run
a = cf.make_chroot(base / "chroots", stamp=stamp)
b = cf.make_chroot(base / "other", stamp=stamp)
ha, hb = (hashlib.sha256(p.read_bytes()).hexdigest() for p in (a, b))
print("first ", ha, a.name)
print("other ", hb, b.name)
print("IDENTICAL" if ha == hb else "DIFFERENT")
