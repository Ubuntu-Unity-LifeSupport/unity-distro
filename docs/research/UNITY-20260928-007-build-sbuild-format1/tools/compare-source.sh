#!/bin/bash
# UNITY-20260928-007 (agent A): compare the source packages of two builds of
# the same package: the file names the .dsc lists, and the paths inside each
# non-orig source file (diff.gz "+++" paths, tarball members). Orig tarballs
# are compared by sha256. usage: compare-source.sh DIR_BEFORE DIR_AFTER
set -u
list() {  # DIR
  local d=$1 dsc; dsc=$(ls "$d"/*.dsc | head -1)
  sed -n '/^Checksums-Sha256:/,/^[A-Z]/p' "$dsc" | awk 'NF==3{print $3}' | while read n; do
    case $n in
      *.orig.tar.*) echo "orig $n $(sha256sum "$d/$n" | cut -c1-16)";;
      *.diff.gz) zcat "$d/$n" | sed -n 's/^+++ [^/]*\/\([^\t]*\).*/diff:\1/p' | sort | sed 's/^/  /'; echo "file $n";;
      *.tar.*) tar -tf "$d/$n" | sort | sed 's/^/  tar:/'; echo "file $n";;
      *) echo "file $n";;
    esac
  done
}
list "$1" > /tmp/cmp-before.$$; list "$2" > /tmp/cmp-after.$$
echo "before: $(grep -c . /tmp/cmp-before.$$) lines, after: $(grep -c . /tmp/cmp-after.$$) lines"
diff /tmp/cmp-before.$$ /tmp/cmp-after.$$ && echo "IDENTICAL (names, paths, orig sha256)"
rm -f /tmp/cmp-before.$$ /tmp/cmp-after.$$
