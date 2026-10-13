#!/usr/bin/env python3
"""UNITY-20260928-014: what list_users() returns across a daemon outage.
Prints every manager notify::is-loaded, user-added/-removed, every listed
user's "changed", and a snapshot of list_users() once per second: is_loaded,
is_nonexistent, user_name, uid, object path. Read-only; the caller stops and
starts accounts-daemon and deletes the user. Usage: list-users-probe.py SECONDS"""

import sys
import time

import gi

gi.require_version("AccountsService", "1.0")
from gi.repository import AccountsService, GLib  # noqa: E402

T0 = time.monotonic()
RUN = float(sys.argv[1]) if len(sys.argv) > 1 else 20
seen = set()


def log(*parts):
    print(f"{time.monotonic() - T0:7.3f}", *parts, flush=True)


def describe(user):
    return (f"{user.get_object_path()} loaded={user.is_loaded()} nonexistent={user.is_nonexistent()} "
            f"name={user.get_user_name()!r} uid={user.get_uid()}")


def watch(user):
    if id(user) not in seen:
        seen.add(id(user))
        user.connect("changed", lambda u: log("  USER changed:", describe(u)))


manager = AccountsService.UserManager.get_default()
manager.connect("notify::is-loaded", lambda m, _p: log(f"MANAGER is-loaded = {m.props.is_loaded}"))
manager.connect("user-added", lambda m, u: log("MANAGER user-added:", describe(u)))
manager.connect("user-removed", lambda m, u: log("MANAGER user-removed:", describe(u)))


def snapshot():
    if manager.props.is_loaded:
        users = manager.list_users()
        for user in users:
            watch(user)
        log("SNAP", " | ".join(describe(u) for u in users) or "(none)")
    return True


GLib.timeout_add(1000, snapshot)
GLib.timeout_add(int(RUN * 1000), lambda: loop.quit())
loop = GLib.MainLoop()
loop.run()
