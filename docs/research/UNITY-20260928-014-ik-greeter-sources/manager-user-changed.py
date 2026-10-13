#!/usr/bin/env python3
"""UNITY-20260928-014: does ActUserManager emit user-changed when a listed
user's data comes back after an accounts-daemon restart, and what does a
fresh list_users() show at that moment? Restarts the daemon itself after 2 s.
Usage: manager-user-changed.py [SECONDS]"""

import subprocess
import sys
import time

import gi

gi.require_version("AccountsService", "1.0")
from gi.repository import AccountsService, GLib  # noqa: E402

T0 = time.monotonic()
RUN = float(sys.argv[1]) if len(sys.argv) > 1 else 8


def log(*parts):
    print(f"{time.monotonic() - T0:7.3f}", *parts, flush=True)


def d(user):
    return f"{user.get_object_path()} name={user.get_user_name()!r} nonexistent={user.is_nonexistent()}"


m = AccountsService.UserManager.get_default()
m.connect("notify::is-loaded", lambda mgr, _p: log(f"is-loaded={mgr.props.is_loaded}",
                                                   "list:", [d(u) for u in mgr.list_users()] if mgr.props.is_loaded else ""))
m.connect("user-changed", lambda mgr, u: log("user-changed:", d(u), "| fresh list:", [d(x) for x in mgr.list_users()]))
m.connect("user-added", lambda mgr, u: log("user-added:", d(u)))
m.connect("user-removed", lambda mgr, u: log("user-removed:", d(u)))


def restart():
    log("RESTART accounts-daemon")
    subprocess.Popen(["sudo", "-n", "systemctl", "restart", "accounts-daemon"])
    return False


GLib.timeout_add(2000, restart)
GLib.timeout_add(int(RUN * 1000), lambda: loop.quit())
loop = GLib.MainLoop()
loop.run()
