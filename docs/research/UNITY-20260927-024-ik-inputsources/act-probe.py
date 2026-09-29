#!/usr/bin/env python3
"""Watch libaccountsservice's ActUser objects across an accounts-daemon restart.

UNITY-20260927-024. Prints, with a monotonic timestamp, every notify::is-loaded
and "changed" signal of each user the manager lists, and the manager's
user-added/-removed/-changed. Every POLL seconds it also prints a snapshot:
is_loaded, user_name, uid, object path, input_sources (NULL or the value).
On every manager notify::is-loaded it logs the new value and, synchronously in
that handler, the state of every watched user, as a consumer that waits for
the manager would see it. It only reads; restart the daemon from outside. Usage: act-probe.py [SECONDS] [POLL]
"""

import sys
import time

import gi

gi.require_version("AccountsService", "1.0")
from gi.repository import AccountsService, GLib  # noqa: E402

T0 = time.monotonic()
RUN = float(sys.argv[1]) if len(sys.argv) > 1 else 60
POLL = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
watched = {}


def log(*parts):
    print(f"{time.monotonic() - T0:8.3f}", *parts, flush=True)


def describe(user):
    sources = user.get_input_sources()
    return (f"loaded={user.is_loaded()} name={user.get_user_name()!r} "
            f"uid={user.get_uid()} path={user.get_object_path()!r} "
            f"input_sources={'NULL' if sources is None else sources.print_(False)}")


def watch(user, why):
    key = id(user)
    if key in watched:
        return
    watched[key] = user
    log("WATCH", why, hex(key), describe(user))
    user.connect("notify::is-loaded",
                 lambda u, p: log("NOTIFY is-loaded", hex(id(u)), describe(u)))
    user.connect("changed", lambda u: log("CHANGED", hex(id(u)), describe(u)))


def snapshot():
    for key, user in watched.items():
        log("SNAP", hex(key), describe(user))
    return GLib.SOURCE_CONTINUE


def manager_loaded(manager, *_):
    log("MANAGER is-loaded =", manager.props.is_loaded)
    for key, user in watched.items():
        log("  AT-MANAGER-NOTIFY", hex(key), describe(user))
    if not manager.props.is_loaded:
        return
    for user in manager.list_users():
        watch(user, "list_users")


manager = AccountsService.UserManager.get_default()
manager.connect("notify::is-loaded", manager_loaded)
manager.connect("user-added", lambda m, u: (log("USER-ADDED"), watch(u, "user-added")))
manager.connect("user-removed", lambda m, u: log("USER-REMOVED", hex(id(u)), describe(u)))
manager.connect("user-changed", lambda m, u: log("USER-CHANGED", hex(id(u)), describe(u)))
manager_loaded(manager)

loop = GLib.MainLoop()
GLib.timeout_add(int(POLL * 1000), snapshot)
GLib.timeout_add(int(RUN * 1000), loop.quit)
loop.run()
