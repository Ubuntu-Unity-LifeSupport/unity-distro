"""UNITY-20260927-047 repeat R, pre-marker checks with the guard's own functions
from the base checkout (main). No inspect() call, no marker read, nothing is
written to the rehearsal log, aptly is not run."""
import importlib.util
import json

spec = importlib.util.spec_from_file_location("guard", "/home/claude/unity-distro/.claude/hooks/command_guard.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

g._check_root()
print("root, tree, mounts: OK (", g.REHEARSAL_ROOT, ")")
path = g.REHEARSAL_ROOT + "/" + "aptly.conf"
config, _ = g._strict_json(path, "the config file")
g._check_config(config)
print("config schema: OK", json.dumps(config))
print("marker present:", __import__("os").path.lexists(g.REHEARSAL_MARKER))
with open(g.REHEARSAL_LOG) as f:
    print("rehearsal log lines:", sum(1 for _ in f))
