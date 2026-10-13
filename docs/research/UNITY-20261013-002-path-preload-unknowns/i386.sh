#!/bin/bash
# i386.sh TAG BINARY... - on target2: for each binary, the dynamic loader's messages with
#   P  the path form   /usr/$LIB/libunity-gtk4-menu.so.0:/usr/$LIB/libgtk-nocsd.so.0 (literal $LIB)
#   N  the bare names  libunity-gtk4-menu.so.0:libgtk-nocsd.so.0 (the earlier releases)
# run once (t32 0) and with an exec chain of 3 (t32 3 = 4 images), stderr lines counted and the distinct lines
# printed. Also what ld.so tried (LD_DEBUG=libs, first lines) for the path form, so the $LIB expansion is visible.
set -u
tag=$1; shift
P='/usr/$LIB/libunity-gtk4-menu.so.0:/usr/$LIB/libgtk-nocsd.so.0'
N='libunity-gtk4-menu.so.0:libgtk-nocsd.so.0'
echo "== $tag at $(date -u +%FT%TZ); foreign architectures: $(dpkg --print-foreign-architectures | xargs);" \
     "$(dpkg-query -W -f='${Package}:${Architecture} ${Version}  ' libc6 libc6-i386 'libc6:i386' 2>/dev/null)"
for b in "$@"; do
  echo "-- $b ($(file -b "$b" | cut -d, -f1-2))"
  for form in P N; do
    v=$P; [ $form = N ] && v=$N
    for n in 0 3; do
      out=$(LD_PRELOAD="$v" "$b" $n 2>/tmp/i386.err); rc=$?
      echo "  $form t32 $n: rc $rc, stdout lines $(printf '%s\n' "$out" | grep -c '^t32'), stderr lines $(grep -c . /tmp/i386.err)," \
           "mapped: $(printf '%s\n' "$out" | head -1 | grep -o 'nocsd [-0-9]* gtk4-menu [-0-9]*')"
      sort /tmp/i386.err | uniq -c | sed 's/^/      /'
    done
  done
  echo "  LD_DEBUG=libs for the path form (lines naming the two libraries):"
  LD_DEBUG=libs LD_PRELOAD="$P" "$b" 0 2>&1 >/dev/null | grep -E 'nocsd|gtk4-menu' | sed 's/^ *[0-9]*: */      /' | head -8
done
