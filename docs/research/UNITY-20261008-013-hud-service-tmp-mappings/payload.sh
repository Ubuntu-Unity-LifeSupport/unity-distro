#!/bin/bash
# payload.sh ARCHIVE_DIR BUILD_DIR - compare the archive libcolumbus 0ubuntu39 .debs with our +unity1 build:
# file lists, and the dynamic symbols exported by libcolumbus.so.1 (name and version).
set -u
A=$1; B=$2
T=$(mktemp -d)
for pkg in libcolumbus1v5 libcolumbus1-dev python3-columbus libcolumbus1-common; do
  a=$(ls $A/${pkg}_*.deb 2>/dev/null | head -1); b=$(ls $B/${pkg}_*.deb 2>/dev/null | head -1)
  if [ -z "$a" ]; then echo "$pkg: not in the archive set (arch-independent data; built: $(basename "$b"))"; continue; fi
  dpkg-deb -c "$a" | awk '{print $6}' | sed 's/^\.//' | sort > $T/a; dpkg-deb -c "$b" | awk '{print $6}' | sed 's/^\.//' | sort > $T/b
  echo "$pkg: file list $(cmp -s $T/a $T/b && echo identical || echo DIFFERS) ($(wc -l < $T/a) files)"
  diff $T/a $T/b | head -5
done
for d in a b; do mkdir -p $T/x$d; done
dpkg-deb -x $(ls $A/libcolumbus1v5_*.deb) $T/xa; dpkg-deb -x $(ls $B/libcolumbus1v5_*.deb) $T/xb
for d in a b; do nm -D --defined-only $(ls $T/x$d/usr/lib/x86_64-linux-gnu/libcolumbus.so.1.*) | awk '{print $2, $3}' | sort > $T/s$d; done
echo "libcolumbus.so.1 exported symbols: $(cmp -s $T/sa $T/sb && echo identical || echo DIFFER) ($(wc -l < $T/sa) symbols)"
diff $T/sa $T/sb | head -10
rm -rf "${T:?}"
