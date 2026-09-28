#!/bin/bash
# UNITY-20260928-003 (agent A): build a two-commit history on unity/resolute
# for a package that has no git history of ours:
#   1. the target-series archive source as extracted by dpkg-source,
#   2. our published source (from aptly's pool, checked against aptly's sha256)
#      replacing the tree entirely.
# No intermediate history is made up. 3.0 (quilt) sources are extracted with
# --skip-patches (patches unapplied, no .pc), as git-ubuntu does. After each
# commit the committed tree is compared with the extracted tree (diff -r;
# empty directories, which git cannot hold, are counted and left out).
# usage: import-dsc-history.sh REPO ARCHIVE.dsc ARCHIVE_LABEL OURS.dsc OURS_NOTE [OURS_LABEL]
set -euo pipefail
R=$1 A=$2 AL=$3 O=$4 ON=$5 OL=${6:-published in our aptly}
T=$(mktemp -d); trap 'rm -rf "${T:?}"' EXIT
export GIT_AUTHOR_NAME="Ubuntu Unity Life Support" GIT_AUTHOR_EMAIL="mihail.rozshko@gmail.com"
export GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME" GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"
extract() {  # DSC DIR
  if grep -q '^Format: 3.0 (quilt)' "$1"; then dpkg-source -q --skip-patches -x "$1" "$2" >/dev/null 2>&1
  else dpkg-source -q -x "$1" "$2" >/dev/null 2>&1; fi
}
snapshot() {  # DSC MESSAGE-FILE
  rm -rf "${T:?}/x"; extract "$1" "$T/x"
  find "$R" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
  (cd "$T/x" && tar -cf - .) | (cd "$R" && tar -xf -)
  git -C "$R" add -A -f .
  git -C "$R" commit -q -F "$2"
  rm -rf "${T:?}/y"; mkdir "$T/y"; git -C "$R" archive HEAD | tar -x -C "$T/y"
  e=$(find "$T/x" -mindepth 1 -type d -empty | wc -l); find "$T/x" -mindepth 1 -type d -empty -delete
  if diff -r --no-dereference "$T/x" "$T/y" >/dev/null; then echo "  tree check OK (empty dirs not in git: $e): $(git -C "$R" log -1 --format='%h %s')"
  else echo "  TREE CHECK FAILED:"; diff -rq --no-dereference "$T/x" "$T/y" | head; exit 1; fi
}
src() { sed -n 's/^Source: //p' "$1"; }; ver() { sed -n 's/^Version: //p' "$1"; }
sums() { sed -n '/^Checksums-Sha256:/,/^[A-Z]/p' "$1" | grep '^ ' | awk '{print "  " $1 "  " $3}'; }
mkdir -p "$R"; git -C "$R" init -q -b unity/resolute
printf '%s %s (%s)\n\nThe %s source as dpkg-source extracts it%s, unchanged.\nSource files (sha256):\n%s\n\nRECONSTRUCTED HISTORY (UNITY-20260928-003): made on 2026-09-28 from source\npackages, not recovered from an original git repository. Author and date are\nthose of the import, not of the release; the real history of the package is in\ndebian/changelog. Provenance: docs/research/UNITY-20260928-003-dsc-history/\nin github.com/Ubuntu-Unity-LifeSupport/unity-distro.\n' \
  "$(src "$A")" "$(ver "$A")" "$AL" "$AL" "$(grep -q '3.0 (quilt)' "$A" && echo ' (patches unapplied)')" "$(sums "$A")" > "$T/m1"
snapshot "$A" "$T/m1"
printf '%s %s (%s)\n\nOur published source as dpkg-source extracts it%s, replacing the tree above;\nthe diff to the previous commit is our change. %s\nSource files (sha256):\n%s\n\nRECONSTRUCTED HISTORY (UNITY-20260928-003): made on 2026-09-28 from source\npackages, not recovered from an original git repository. Author and date are\nthose of the import, not of the release; the real history of the package is in\ndebian/changelog. Provenance: docs/research/UNITY-20260928-003-dsc-history/\nin github.com/Ubuntu-Unity-LifeSupport/unity-distro.\n' \
  "$(src "$O")" "$(ver "$O")" "$OL" "$(grep -q '3.0 (quilt)' "$O" && echo ' (patches unapplied)')" "$ON" "$(sums "$O")" > "$T/m2"
snapshot "$O" "$T/m2"
