#!/bin/bash
# payload.sh PUBLISHED_DIR BUILD_DIR - compare the published libcolumbus +unity1 binaries (the pool files) with this
# task's +unity2 build, package by package (.deb and .ddeb):
#   file list; control fields with Version (and the Version in Source:/Depends) normalised; the md5sums control
#   file (the payload); and the dynamic symbols exported by libcolumbus.so.1 (name and version).
set -u
A=$1; B=$2
T=$(mktemp -d)
norm() { sed -E 's/0ubuntu39\+unity[12]/0ubuntu39+unityN/g'; }
for b in "$B"/*.deb "$B"/*.ddeb; do
  f=$(basename "$b"); pkg=${f%%_*}; ext=${f##*.}
  a=$(ls "$A"/${pkg}_*+unity1_*.$ext 2>/dev/null | head -1)
  if [ -z "$a" ]; then echo "$pkg ($ext): NOT IN THE PUBLISHED SET"; continue; fi
  dpkg-deb -c "$a" | awk '{print $1, $6}' | sort -k2 > $T/la; dpkg-deb -c "$b" | awk '{print $1, $6}' | sort -k2 > $T/lb
  dpkg-deb -f "$a" | norm > $T/ca; dpkg-deb -f "$b" | norm > $T/cb
  for d in a b; do rm -rf "${T:?}/e$d"; mkdir -p $T/e$d; done
  dpkg-deb -e "$a" $T/ea; dpkg-deb -e "$b" $T/eb
  ls $T/ea > $T/ma; ls $T/eb > $T/mb
  m="md5sums $(cmp -s $T/ea/md5sums $T/eb/md5sums && echo identical || echo DIFFER)"
  s=""
  for x in $(cat $T/ma); do [ "$x" = control ] || [ "$x" = md5sums ] || cmp -s $T/ea/$x $T/eb/$x || s="$s $x"; done
  echo "$pkg ($ext): files $(cmp -s $T/la $T/lb && echo identical || echo DIFFER) ($(wc -l < $T/la)); control" \
       "$(cmp -s $T/ca $T/cb && echo identical || echo DIFFERS) apart from the version; $m;" \
       "control members $(cmp -s $T/ma $T/mb && echo "identical ($(paste -sd, $T/ma))" || echo DIFFER)${s:+, differing:$s}"
  diff $T/la $T/lb | head -5; diff $T/ca $T/cb | head -10
  cmp -s $T/ea/md5sums $T/eb/md5sums || diff $T/ea/md5sums $T/eb/md5sums | head -10
done
for d in a b; do rm -rf "${T:?}/x$d"; mkdir -p $T/x$d; done
dpkg-deb -x $(ls "$A"/libcolumbus1v5_*+unity1_amd64.deb) $T/xa; dpkg-deb -x $(ls "$B"/libcolumbus1v5_*_amd64.deb) $T/xb
for d in a b; do nm -D --defined-only $(ls $T/x$d/usr/lib/x86_64-linux-gnu/libcolumbus.so.1.*) | awk '{print $2, $3}' | sort > $T/s$d; done
echo "libcolumbus.so.1 exported symbols: $(cmp -s $T/sa $T/sb && echo identical || echo DIFFER) ($(wc -l < $T/sa) symbols)"
diff $T/sa $T/sb | head -10
for d in a b; do readelf -d $T/x$d/usr/lib/x86_64-linux-gnu/libcolumbus.so.1.* | grep -E 'NEEDED|SONAME' | awk '{print $2, $NF}' > $T/n$d; done
echo "DT_NEEDED/SONAME: $(cmp -s $T/na $T/nb && echo identical || echo DIFFER)"
rm -rf "${T:?}"
