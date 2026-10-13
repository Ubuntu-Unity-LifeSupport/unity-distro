#!/bin/bash
# UNITY-20260928-007 (agent A): what `dpkg-source -b` (as sbuild runs it in a
# source tree) does with a git checkout, per source format, per checkout kind
# (clone: .git directory; worktree: .git file) and per dpkg-source option.
# Builds a tiny package per case in a scratch dir; reports whether the build
# succeeded and whether any .git entry is in the produced source files.
set -u
W=$(mktemp -d); trap 'rm -rf "${W:?}"' EXIT
mkpkg() {  # DIR FORMAT NATIVE
  local d=$1 fmt=$2 native=$3 ver
  mkdir -p "$d/debian/source" "$d/src"; echo "int main(void){return 0;}" > "$d/src/a.c"
  [ "$native" = yes ] && ver=1.0 || ver=1.0-1
  printf 'tiny (%s) resolute; urgency=medium\n\n  * test\n\n -- T <t@example.com>  Mon, 28 Sep 2026 00:00:00 +0000\n' "$ver" > "$d/debian/changelog"
  printf 'Source: tiny\nMaintainer: T <t@example.com>\n\nPackage: tiny\nArchitecture: all\nDescription: t\n' > "$d/debian/control"
  [ "$fmt" != "1.0" ] && echo "$fmt" > "$d/debian/source/format"
}
check() {  # DIR -> "ok|FAIL gitentries=N"
  local d=$1 p=$2; shift 2
  (cd "$p" && dpkg-source "$@" -b "$(basename "$d")" > "$p/log" 2>&1) && r=ok || r="FAIL($(grep -m1 -oE 'error: .{0,60}' "$p/log"))"
  local n=0
  for f in "$p"/*.diff.gz; do [ -f "$f" ] && n=$((n + $(zcat "$f" | grep -cE '^\+\+\+ [^ ]*/\.git(/|$)'))); done
  for f in "$p"/*.tar.*; do [ -f "$f" ] && case $f in *orig*) ;; *) n=$((n + $(tar -tf "$f" | grep -cE '(^|/)\.git(/|$)')));; esac; done
  echo "$r gitentries=$n"
}
for case in "1.0 no" "1.0 yes" "3.0 (quilt) no" "3.0 (native) yes"; do
  fmt=${case% *}; native=${case##* }
  for kind in clone worktree; do
    for opts in "" "-i" "-I" "-i -I"; do
      p=$W/$RANDOM$RANDOM; mkdir -p $p; d=$p/tiny-1.0
      mkpkg "$d" "$fmt" "$native"
      if [ $native = no ]; then (cd $p && tar -czf tiny_1.0.orig.tar.gz --exclude=debian tiny-1.0); fi
      if [ $kind = clone ]; then git -C "$d" init -q && git -C "$d" add -A && git -C "$d" -c user.email=t@e -c user.name=t commit -qm x
      else g=$p/g; git init -q $g; cp -r "$d/." $g/; git -C $g add -A; git -C $g -c user.email=t@e -c user.name=t commit -qm x
           rm -rf "${d:?}"; git -C $g worktree add -q "$d" 2>/dev/null; fi
      [ $kind = clone ] && touch "$d/.git/index"   # an index newer than the orig
      printf '%-16s %-6s %-8s %-7s %s\n' "$fmt" "$native" "$kind" "${opts:-none}" "$(check "$d" "$p" $opts)"
    done
  done
done
