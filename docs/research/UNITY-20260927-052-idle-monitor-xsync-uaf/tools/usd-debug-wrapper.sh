#!/bin/sh
# UNITY-20260927-005 (agent A): installed on target in place of
# /usr/lib/unity-settings-daemon/unity-settings-daemon (dpkg-divert --local
# --rename to ...daemon.real) so that every instance, whichever launcher starts
# it, keeps the same PID (G_MESSAGES_DEBUG=all: GLib drops g_debug otherwise) and writes its --debug log to /tmp/usd-PID.log.
G_MESSAGES_DEBUG=all exec /usr/lib/unity-settings-daemon/unity-settings-daemon.real --debug "$@" > /tmp/usd-$$.log 2>&1
