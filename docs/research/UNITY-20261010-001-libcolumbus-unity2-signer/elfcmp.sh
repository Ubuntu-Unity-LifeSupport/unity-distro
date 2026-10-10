#!/bin/bash
# elfcmp.sh A.so B.so - compare two ELF files section by section (sha256 of each section's bytes, by name).
# The sections that carry the package version and the identity derived from it are reported separately:
# .note.package (the package metadata note, with the version), .note.gnu.build-id, .gnu_debuglink.
set -u
T=$(mktemp -d)
# name, type, file offset and size of every section (readelf -S -W: [Nr] Name Type Address Off Size ...);
# the bytes are read from the file by offset and size, so non-allocated sections (.gnu_debuglink, .comment, ...)
# are compared too (objcopy -O binary writes only allocated ones). NOBITS sections have no bytes in the file.
sections() { readelf -S -W "$1" | sed -n 's/^ *\[ *[0-9]*\] *//p' | awk 'NF >= 6 && $1 != "NULL" {print $1, $2, $4, $5}'; }
for x in a b; do
  f=$1; [ $x = b ] && f=$2
  sections "$f" | while read -r s type off size; do
    if [ "$type" = NOBITS ]; then echo "$s nobits size $size"; continue; fi
    echo "$s $(dd if="$f" bs=1 skip=$((16#$off)) count=$((16#$size)) status=none | sha256sum | cut -c1-16) size $size"
  done > $T/$x
done
grep -vE '^(\.note\.package|\.note\.gnu\.build-id|\.gnu_debuglink) ' $T/a > $T/ra
grep -vE '^(\.note\.package|\.note\.gnu\.build-id|\.gnu_debuglink) ' $T/b > $T/rb
echo "sections: $(wc -l < $T/a) in A, $(wc -l < $T/b) in B; all but .note.package/.note.gnu.build-id/.gnu_debuglink:" \
     "$(cmp -s $T/ra $T/rb && echo identical || echo DIFFER) ($(wc -l < $T/ra) sections)"
diff $T/ra $T/rb
echo "differing among the version-carrying ones: $(diff <(grep -E '^(\.note\.package|\.note\.gnu\.build-id|\.gnu_debuglink) ' $T/a) <(grep -E '^(\.note\.package|\.note\.gnu\.build-id|\.gnu_debuglink) ' $T/b) | grep '^<' | awk '{print $2}' | xargs)"
for x in 1 2; do f=$1; [ $x = 2 ] && f=$2; echo "  package note $x: $(readelf -p .note.package "$f" 2>/dev/null | grep -o '{.*}' | head -1)"; done
rm -rf "${T:?}"
