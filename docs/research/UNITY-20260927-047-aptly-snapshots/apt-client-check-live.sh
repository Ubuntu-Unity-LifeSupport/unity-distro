#!/bin/bash
# UNITY-20260927-047 L4 check: an isolated apt client (own state/cache/sources,
# no system lists touched) on file:<live>/public, Signed-By the live key;
# apt-get update must give no E:/W: line; show two candidates. Read-only.
set -u
T=/srv/aptly
KEY=/srv/aptly/public/unity-distro-archive.asc
W=$(mktemp -d)
mkdir -p "$W/state/lists/partial" "$W/cache/archives/partial" "$W/etc/sources.list.d" "$W/etc/preferences.d"
cp "$KEY" "$W/key.asc"
printf 'Types: deb\nURIs: file:%s/public\nSuites: resolute\nComponents: main\nArchitectures: amd64\nSigned-By: %s/key.asc\n' "$T" "$W" > "$W/etc/sources.list.d/r.sources"
: > "$W/status"
O=(-o Dir::State="$W/state" -o Dir::State::status="$W/status" -o Dir::Cache="$W/cache" -o Dir::Etc::sourcelist=/dev/null
   -o Dir::Etc::sourceparts="$W/etc/sources.list.d" -o Dir::Etc::preferencesparts="$W/etc/preferences.d" -o APT::Architecture=amd64)
out=$(apt-get "${O[@]}" update 2>&1); rc=$?
echo "apt-get update rc=$rc; E/W lines: $(printf '%s\n' "$out" | grep -cE '^(E|W):')"
printf '%s\n' "$out" | grep -E '^(E|W):' | head -3
for p in unity libunity-gtk4-menu0; do echo "$p candidate: $(apt-cache "${O[@]}" policy "$p" | awk '/Candidate:/{print $2}')"; done
rm -rf "${W:?}"
