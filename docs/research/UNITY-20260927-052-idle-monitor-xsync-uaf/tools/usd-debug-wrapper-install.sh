#!/bin/sh
# Install (or with "remove" undo) the --debug wrapper for unity-settings-daemon.
B=/usr/lib/unity-settings-daemon/unity-settings-daemon
if [ "$1" = remove ]; then sudo rm -f "$B"; sudo dpkg-divert --local --rename --remove "$B"; exit; fi
dpkg-divert --list "$B" | grep -q real || sudo dpkg-divert --local --rename --divert "$B.real" --add "$B"
sudo install -m 755 ~/usd-debug-wrapper.sh "$B"
