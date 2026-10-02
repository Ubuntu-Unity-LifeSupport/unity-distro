#!/bin/sh
# UNITY-20260929-014: real runs of the hardened tool (branch a/UNITY-20260929-014).
W=/home/claude/work/a/unity-distro-014
T=$W/scripts/build_sbuild.py
R=/home/claude/work/a/014-real
P=/srv/aptly/public/pool/main/n/nux
V=4.0.8+18.10.20180623-0ubuntu15+unity2
M040=/home/claude/work/a/unity-distro-040/docs/research/UNITY-20260927-040-edge-grab-guard/build-gated
cd "$W" || exit 1
echo "== Q1 tiny013 + libnux-4.0-common $V from the pool (real sbuild)"
python3 $T --task-id UNITY-20260929-014 --source-repo $R/tiny013 --target-series resolute --output-dir $R/out-q1 \
  --extra-package $P/libnux-4.0-common_${V}_all.deb; echo "Q1 exit=$?"
ls -A $R/out-q1 | sed 's/^/  /'
for m in $R/out-q1/*-build-manifest.json; do
  python3 -c "import json,sys; sys.path.insert(0,'scripts'); import build_dependencies as b; from pathlib import Path; p=Path(sys.argv[1]); print('  Q1 manifest_error:', b.manifest_error(json.load(open(p)), p.parent))" "$m"
done
echo "== Q2 the same + a foreign-architecture package: refused before sbuild, output left empty"
python3 $T --task-id UNITY-20260929-014 --source-repo $R/tiny013 --target-series resolute --output-dir $R/out-q2 \
  --extra-package $P/libnux-4.0-common_${V}_all.deb --extra-package $R/libfoo_1.0_arm64.deb; echo "Q2 exit=$?"
echo "  Q2 output: [$(ls -A $R/out-q2 | tr '\n' ' ')]"
echo "== Q3 the UNITY-20260927-040 gated manifest under the new check (real pool)"
python3 -c "import json,sys; sys.path.insert(0,'scripts'); import build_dependencies as b; from pathlib import Path; p=Path(sys.argv[1]); print('  Q3 manifest_error:', b.manifest_error(json.load(open(p)), p.parent))" $M040/UNITY-20260927-040-unity-build-manifest.json
echo "== done"
