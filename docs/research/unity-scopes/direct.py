#!/usr/bin/python3
"""direct.py NAME QUERY - import /usr/share/unity-scopes/NAME/unity_NAME_daemon.py and call its search()"""
import sys, importlib.util, traceback, warnings
warnings.simplefilter("ignore")
name, query = sys.argv[1], sys.argv[2]
path = "/usr/share/unity-scopes/%s/unity_%s_daemon.py" % (name, name)
spec = importlib.util.spec_from_file_location("m_" + name, path)
m = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(m)
    r = m.search(query, [])
    print("%s: %d results %s" % (name, len(r), [x.get('title', x) if isinstance(x, dict) else x[2] if isinstance(x, tuple) and len(x) > 2 else x for x in r[:2]]))
except Exception:
    print("%s: EXCEPTION" % name); traceback.print_exc(limit=3)
