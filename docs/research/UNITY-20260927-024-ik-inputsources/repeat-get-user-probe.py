#!/usr/bin/env python3
"""Call act_user_manager_get_user() the way indicator-keyboard does (UNITY-20260927-024).

update_greeter_user() (lib/main.vala:318-324) calls get_user() on the greeter's
entry name and reads is_loaded at once, without waiting for notify::is-loaded.
This probe does the same for each NAME: once as soon as the manager is loaded,
and again after DELAY seconds (the next entry-selected for the same name), and
prints what the consumer would see each time. Usage: repeat-get-user-probe.py
DELAY NAME...
"""

import sys

import gi

gi.require_version("AccountsService", "1.0")
from gi.repository import AccountsService, GLib  # noqa: E402

DELAY = float(sys.argv[1])
NAMES = sys.argv[2:]
manager = AccountsService.UserManager.get_default()
loop = GLib.MainLoop()


def look(round_):
    for name in NAMES:
        user = manager.get_user(name)
        if not user.is_loaded():
            print(f"round {round_} {name}: is_loaded=False (the consumer skips it)", flush=True)
            continue
        sources = user.get_input_sources()
        print(f"round {round_} {name}: is_loaded=True nonexistent={user.props.nonexistent} "
              f"user_name={user.get_user_name()!r} input_sources="
              f"{'NULL' if sources is None else sources.print_(False)} "
              f"object={hex(id(user))}", flush=True)
    return GLib.SOURCE_REMOVE


def start(*_):
    if not manager.props.is_loaded:
        return
    look(1)
    GLib.timeout_add(int(DELAY * 1000), lambda: look(2))
    GLib.timeout_add(int(DELAY * 1000) + 500, loop.quit)


manager.connect("notify::is-loaded", start)
start()
loop.run()
