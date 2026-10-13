#!/bin/sh
# UNITY-20260927-040: compare the gated release build with the test build,
# package by package: control version, file list and DEBIAN/md5sums.
# usage: compare-builds.sh GATED_DIR TEST_DIR
G=${1:?gated dir}; T=${2:?test dir}
W=$(mktemp -d); trap 'rm -rf "${W:?}"' EXIT
for d in "$G"/*.deb; do
  n=$(basename "$d"); t="$T/$n"
  if [ ! -f "$t" ]; then echo "$n: MISSING in test build"; continue; fi
  for s in g t; do
    f=$d; [ $s = t ] && f=$t
    dpkg-deb -c "$f" | awk '{print $1, $6}' | sort > "$W/$s.list"
    dpkg-deb -I "$f" md5sums 2>/dev/null | sort > "$W/$s.md5"
    dpkg-deb -f "$f" Version Depends > "$W/$s.ctl"
  done
  l=$(diff "$W/g.list" "$W/t.list" | grep -c '^[<>]')
  m=$(diff "$W/g.md5" "$W/t.md5" | grep '^[<>]' | awk '{print $3}' | sort -u)
  c=$(diff -q "$W/g.ctl" "$W/t.ctl" >/dev/null && echo same || echo DIFF)
  echo "$n: files=$(wc -l < "$W/g.list") list-diff=$l control=$c md5-diff=$(echo "$m" | grep -c .) ${m:+[$(echo $m)]}"
done
