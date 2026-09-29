#!/bin/sh
# UNITY-20260929-013: real sbuild runs of the new build_sbuild.py (branch a/UNITY-20260929-013).
T=/home/claude/work/a/unity-distro-013/scripts/build_sbuild.py
R=/home/claude/work/a/013-real
P=/srv/aptly/public/pool/main/n/nux
V=4.0.8+18.10.20180623-0ubuntu15+unity2
cd /home/claude/work/a/unity-distro-013
echo "== R1 tiny013 + libnux-4.0-common 0ubuntu11 (older than the archive's 0ubuntu12)"
python3 $T --task-id UNITY-20260929-013 --source-repo $R/tiny013 --target-series resolute --output-dir $R/out-r1 \
  --extra-package $R/libnux-4.0-common_4.0.8+18.10.20180623-0ubuntu11_all.deb; echo "R1 exit=$?"
echo "== R2 tiny013 + libnux-4.0-common $V from the pool"
python3 $T --task-id UNITY-20260929-013 --source-repo $R/tiny013 --target-series resolute --output-dir $R/out-r2 \
  --extra-package $P/libnux-4.0-common_${V}_all.deb; echo "R2 exit=$?"
echo "== R3 unity 7b0eca27 + libnux-4.0-0, -common, -dev $V from the pool"
python3 $T --task-id UNITY-20260927-040 --source-repo /home/claude/work/a/040-unity --target-series resolute --output-dir $R/out-r3 \
  --extra-package $P/libnux-4.0-0_${V}_amd64.deb --extra-package $P/libnux-4.0-common_${V}_all.deb \
  --extra-package $P/libnux-4.0-dev_${V}_amd64.deb; echo "R3 exit=$?"
echo "== done"
