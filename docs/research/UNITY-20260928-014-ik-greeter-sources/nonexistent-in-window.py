#!/usr/bin/env python3
"""UNITY-20260928-014: in the manager's notify::is-loaded handler (where the
greeter's indicator-keyboard lists users and writes), print for every listed
user is_loaded, is_nonexistent, user_name, uid and whether input_sources is
NULL. Restarts accounts-daemon itself after 2 s. Read-only otherwise.
Usage (as the user whose view you want): nonexistent-in-window.py [SECONDS]"""

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


def describe(user):
    return (f"loaded={user.is_loaded()} nonexistent={user.is_nonexistent()} "
            f"name={user.get_user_name()!r} uid={user.get_uid()} "
            f"input_sources={'NULL' if user.get_input_sources() is None else 'set'}")


manager = AccountsService.UserManager.get_default()


def on_loaded(mgr, _pspec):
    log(f"MANAGER is-loaded = {mgr.props.is_loaded}")
    if mgr.props.is_loaded:
        for user in mgr.list_users():
            log("  list_users:", describe(user))


manager.connect("notify::is-loaded", on_loaded)


def restart():
    log("RESTART accounts-daemon")
    subprocess.Popen(["sudo", "-n", "systemctl", "restart", "accounts-daemon"])
    return False


GLib.timeout_add(2000, restart)
GLib.timeout_add(int(RUN * 1000), lambda: loop.quit())
loop = GLib.MainLoop()
loop.run()
