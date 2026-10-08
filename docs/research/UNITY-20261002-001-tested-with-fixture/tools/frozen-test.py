"""UNITY-20261002-001: run test_tested_with with the fixture clock frozen
(one stamp, one tar mtime), as if both chroot tarballs were made in the same
second. Usage: u001-frozen-test.py <worktree>"""
import subprocess, sys, unittest
from pathlib import Path
tests = Path(sys.argv[1]) / "scripts/tests"
sys.path.insert(0, str(tests))
import chroot_fixtures as cf

real_stamp = cf.stamp_days_ago
FROZEN = {}
def frozen_stamp(days):  # one fixed stamp per age, for the whole run
    return FROZEN.setdefault(days, real_stamp(days))
cf.stamp_days_ago = frozen_stamp
real_run = subprocess.run
class FrozenSubprocess:
    def __getattr__(self, name):
        return getattr(subprocess, name)
    @staticmethod
    def run(cmd, **kw):
        if cmd[:1] == ["tar"]:
            cmd = cmd[:2] + ["--mtime=@1790000000", "--sort=name"] + cmd[2:]
        return real_run(cmd, **kw)
cf.subprocess = FrozenSubprocess()

import test_build_sbuild as t  # noqa: E402  (imports make_chroot from the patched module)
t.stamp_days_ago = frozen_stamp  # the test module may import it by name
suite = unittest.TestSuite([t.BuildSbuildTest(n) for n in sys.argv[2:] or ["test_tested_with"]]) \
    if hasattr(t, "BuildSbuildTest") else unittest.defaultTestLoader.loadTestsFromModule(t)
res = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(0 if res.wasSuccessful() else 1)
