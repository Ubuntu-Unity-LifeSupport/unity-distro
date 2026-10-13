#!/bin/bash
# payload-compare.sh OLD_DIR NEW_DIR VERSION - compare the .debs of two builds of one version:
# control fields (minus Installed-Size), file lists (path, mode, size), exported dynamic symbols
# of every shared object, and per-file sha256 (reported, rebuilds are not bit-identical).
# Read-only: unpacks into a temporary directory.
set -u
old=$1 new=$2 ver=$3
tmp=$(mktemp -d)
trap 'rm -rf "${tmp:?}"' EXIT
echo "# payload compare, version $ver"
echo "# old: $old"
echo "# new: $new"
for nd in "$new"/*_"${ver#*:}"_*.deb; do
  f=$(basename "$nd")
  od="$old/$f"
  if [ ! -f "$od" ]; then echo "ONLY-NEW $f"; continue; fi
  for s in old new; do
    d=$od; [ $s = new ] && d=$nd
    mkdir -p "$tmp/$s/$f"
    dpkg-deb -f "$d" | grep -v '^Installed-Size' > "$tmp/$s/$f.control"
    dpkg-deb -c "$d" | awk '{print $1, $3, $6}' | sort > "$tmp/$s/$f.list"
    dpkg-deb -x "$d" "$tmp/$s/$f"
    (cd "$tmp/$s/$f" && find . -type f -name '*.so*' | sort | while read -r so; do
       echo "== $so"; nm -D --defined-only "$so" 2>/dev/null | awk '{print $2, $3}' | sort; done) > "$tmp/$s/$f.syms"
    (cd "$tmp/$s/$f" && find . -type f | sort | xargs -r sha256sum) > "$tmp/$s/$f.sha"
  done
  c=same; cmp -s "$tmp/old/$f.control" "$tmp/new/$f.control" || c=DIFF
  l=same; cmp -s "$tmp/old/$f.list" "$tmp/new/$f.list" || l=DIFF
  y=same; cmp -s "$tmp/old/$f.syms" "$tmp/new/$f.syms" || y=DIFF
  n=$(diff "$tmp/old/$f.sha" "$tmp/new/$f.sha" | grep -c '^>')
  echo "$f control=$c files=$l symbols=$y files_with_other_sha256=$n/$(wc -l < "$tmp/new/$f.sha")"
  [ $c = DIFF ] && diff "$tmp/old/$f.control" "$tmp/new/$f.control" | sed 's/^/    /'
  [ $l = DIFF ] && diff "$tmp/old/$f.list" "$tmp/new/$f.list" | sed 's/^/    /' | head -20
  [ $y = DIFF ] && diff "$tmp/old/$f.syms" "$tmp/new/$f.syms" | sed 's/^/    /' | head -20
done
for od in "$old"/*_"${ver#*:}"_*.deb; do [ -f "$new/$(basename "$od")" ] || echo "ONLY-OLD $(basename "$od")"; done
