#!/bin/bash
# UNITY-20260928-007 (agent A): what `-i -I` changes in a real package's
# source package. For CHECKOUT at REF:
#   reference = dpkg-source -b (no options) on `git archive REF` (tracked
#               files only, no .git at all);
#   candidate = dpkg-source -i -I -b on a fresh clone at REF (.git present).
# Prints the paths that differ between the two (diff.gz "+++" paths, or the
# members of a full tarball), and the tracked files that dpkg-source's default
# ignore regex (-i) or tar-ignore globs (-I) match.
# usage: side-effect-check.sh CHECKOUT REF [ORIG_TARBALL]
set -u
C=$1 REF=$2 O=${3:-}
T=$(mktemp -d); trap 'rm -rf "${T:?}"' EXIT
v=$(git -C "$C" show "$REF:debian/changelog" | dpkg-parsechangelog -l- -S Version)
p=$(git -C "$C" show "$REF:debian/changelog" | dpkg-parsechangelog -l- -S Source)
up=${v#*:}; case "$up" in *-*) up=${up%-*};; esac
for side in ref cand; do mkdir -p "$T/$side"; [ -n "$O" ] && cp "$O" "$T/$side/"; done
git -C "$C" archive --prefix="$p-$up/" "$REF" | tar -x -C "$T/ref"
git clone -q --no-hardlinks "$C" "$T/cand/$p-$up" 2>/dev/null; git -C "$T/cand/$p-$up" checkout -q "$REF" 2>/dev/null
(cd "$T/ref" && dpkg-source -b "$p-$up" > log 2>&1) || { echo "$p: REFERENCE BUILD FAILED: $(grep -m1 error "$T/ref/log")"; exit 1; }
(cd "$T/cand" && dpkg-source -i -I -b "$p-$up" > log 2>&1) || { echo "$p: CANDIDATE BUILD FAILED: $(grep -m1 error "$T/cand/log")"; exit 1; }
paths() {  # DIR: one path per line from the non-orig source files
  for f in "$1"/*.diff.gz; do [ -f "$f" ] && zcat "$f" | sed -n 's/^+++ [^/]*\/\([^\t]*\).*/diff:\1/p'; done
  for f in "$1"/*.tar.*; do [ -f "$f" ] || continue; case $f in *.orig.tar.*) continue;; esac
    tar -tf "$f" | sed -E 's#^[^/]*/##; /^$/d; s#^#tar:#'; done
}
paths "$T/ref" | sort > "$T/r"; paths "$T/cand" | sort > "$T/c"
kind=$(ls "$T/cand" | grep -oE '\.(diff\.gz|debian\.tar\.[a-z]+|tar\.[a-z]+)$' | sort -u | tr '\n' ' ')
only_ref=$(comm -23 "$T/r" "$T/c" | tr '\n' ' '); only_cand=$(comm -13 "$T/r" "$T/c" | tr '\n' ' ')
m=$(git -C "$C" ls-tree -r --name-only "$REF" | perl -MDpkg::Source::Package -ne '
  BEGIN { $re = Dpkg::Source::Package::get_default_diff_ignore_regex();
          @g = Dpkg::Source::Package::get_default_tar_ignore_pattern();
          for (@g) { my $x = quotemeta($_); $x =~ s/\\\*/[^\/]*/g; $x =~ s/\\\?/./g; $x =~ s/\\\[/[/g; $x =~ s/\\\]/]/g; push @r, qr{(?:^|/)$x$} } }
  chomp; my @w; push @w, "i" if /$re/; for my $r (@r) { if (m{$r}) { push @w, "I"; last } }
  print "$_(" . join("", @w) . ") " if @w;')
printf '%s %s [%s]: %d paths; only without options: %s; only with -i -I: %s; tracked files matching the default ignores: %s\n' \
  "$p" "$v" "${kind% }" "$(wc -l < "$T/r")" "${only_ref:-none}" "${only_cand:-none}" "${m:-none}"
