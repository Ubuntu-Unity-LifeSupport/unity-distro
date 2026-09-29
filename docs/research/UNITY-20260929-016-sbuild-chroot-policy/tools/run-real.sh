#!/bin/sh
# UNITY-20260929-016: real runs of the new chroot policy (branch a/UNITY-20260929-016).
W=/home/claude/work/a/unity-distro-016
R=/home/claude/work/a/016-real
P=/srv/aptly/public/pool/main/n/nux
V=4.0.8+18.10.20180623-0ubuntu15+unity2
T=${T:?snapshot timestamp}
C=/home/claude/.cache/sbuild/chroots/resolute-amd64-$T.tar.zst
cd "$W" || exit 1
echo "== S1 create the tarball from snapshot $T"
python3 scripts/sbuild_chroot.py create --snapshot "$T"; echo "S1 exit=$?"
ls -l "$C" "${C%.tar.zst}.json"
python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print('  sources', d['sources']); print('  inrelease', {k: v['date'] for k, v in d['inrelease'].items()}); print('  packages', len(d['packages']), [p for p in d['packages'] if p.startswith('ca-certificates')])" "${C%.tar.zst}.json"
echo "== S2 tiny013 on it (real sbuild)"
python3 scripts/build_sbuild.py --task-id UNITY-20260929-016 --source-repo $R/tiny013 --target-series resolute \
  --output-dir $R/out-s2 --chroot-tarball "$C"; echo "S2 exit=$?"
grep -n -E '^I: Unpacking|upgraded,|InRelease|on-demand|too old' $R/out-s2/*sbuild.log | head -12
echo "== S3 unity 7b0eca27 + our nux from the pool, same tarball"
python3 scripts/build_sbuild.py --task-id UNITY-20260929-016 --source-repo $R/unity --target-series resolute \
  --output-dir $R/out-s3 --chroot-tarball "$C" \
  --extra-package $P/libnux-4.0-0_${V}_amd64.deb --extra-package $P/libnux-4.0-common_${V}_all.deb \
  --extra-package $P/libnux-4.0-dev_${V}_amd64.deb; echo "S3 exit=$?"
grep -n -E '^I: Unpacking|upgraded,|InRelease|on-demand|too old|Status:' $R/out-s3/*sbuild.log | head -14
for m in $R/out-s2/*-build-manifest.json $R/out-s3/*-build-manifest.json; do
  python3 -c "import json,sys; c=json.load(open(sys.argv[1]))['chroot']; print('  ', sys.argv[1].rsplit('/',1)[1], c['snapshot'], c['sha256'][:16], len(c['log_inrelease']), 'InRelease lines')" "$m"
done
echo "== done $(date -u +%H:%M:%SZ)"
