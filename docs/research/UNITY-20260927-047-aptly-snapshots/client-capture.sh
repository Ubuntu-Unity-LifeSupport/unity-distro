#!/bin/bash
# client-capture.sh LABEL NAMES - on a target desktop (as the desktop user):
# apt-get update, then apt-cache policy for every binary package name in NAMES
# (our repository's binaries). Prints update errors/warnings, our Release
# fields, and the full apt-cache policy output. Read-only apart from apt's lists.
label=$1 names=$2
echo "== $label host=$(hostname) boot_id=$(cat /proc/sys/kernel/random/boot_id) date_utc=$(date -u +%FT%TZ)"
echo "## sources for our repository"; grep -l 192.168.56.10 /etc/apt/sources.list.d/* 2>/dev/null | xargs -r grep -h -E '^(URIs|Suites|Components|Signed-By|Architectures|deb )'
out=$(sudo -n apt-get update 2>&1); rc=$?
echo "## apt-get update rc=$rc; E/W lines:"; echo "$out" | grep -E '^(E|W|Err):' || echo "(none)"
L=$(ls /var/lib/apt/lists/192.168.56.10*_InRelease 2>/dev/null | head -1)
echo "## our InRelease: ${L:-missing}"; [ -n "$L" ] && grep -E '^(Origin|Label|Suite|Codename|Architectures|Components|Date):' "$L"
echo "## apt-cache policy for every name (compare before/after with diff)"
xargs apt-cache policy < "$names" 2>&1
