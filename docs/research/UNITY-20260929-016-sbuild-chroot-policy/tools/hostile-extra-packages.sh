#!/bin/sh
# UNITY-20260929-016, Verifier round 2: does build/sbuild-config.pl override a
# user sbuild config's $extra_packages, while build_sbuild's own
# --extra-package still reaches sbuild? Control: plain sbuild copies the
# user's package into its resolver archive.
W=/home/claude/work/a/unity-distro-016
R=/home/claude/work/a/016-real
T=20260929T201245Z
C=/home/claude/.cache/sbuild/chroots/resolute-amd64-$T.tar.zst
P=/srv/aptly/public/pool/main/n/nux/libnux-4.0-common_4.0.8+18.10.20180623-0ubuntu15+unity2_all.deb
X=$R/hostile-xdg3
E=$R/evilpkg_9.9_all.deb
rm -rf -- "${X:?}" "${R:?}/out-h4" "${R:?}/h3" "${R:?}/.evil"
mkdir -p "$X/sbuild" "$R/h3" "$R/.evil/DEBIAN"
printf 'Package: evilpkg\nVersion: 9.9\nArchitecture: all\nMaintainer: t <t@example.com>\nDescription: t\n' > "$R/.evil/DEBIAN/control"
dpkg-deb --root-owner-group --build "$R/.evil" "$E" >/dev/null
cat > "$X/sbuild/config.pl" <<EOF
\$unshare_tmpdir_template = '/var/tmp/sbuild-claude/sbuild-unshare-XXXXXX';
\$extra_packages = ['$E'];
1;
EOF
cd "$W" || exit 1
echo "== H3 control: plain sbuild, user config with \$extra_packages"
cp -a $R/tiny013 $R/h3/tiny013
( cd $R/h3/tiny013 && XDG_CONFIG_HOME=$X sbuild -d resolute --no-clean-source --verbose --chroot-mode=unshare --chroot=$C > $R/h3/sbuild.log 2>&1; echo "H3 exit=$?" )
grep -n -E '^Copying' $R/h3/sbuild.log | head -3
echo "== H4 build_sbuild.py, same user config, plus our own --extra-package"
XDG_CONFIG_HOME=$X python3 scripts/build_sbuild.py --task-id UNITY-20260929-016 --source-repo $R/tiny013 \
  --target-series resolute --output-dir $R/out-h4 --chroot-tarball $C --extra-package $P; echo "H4 exit=$?"
grep -n -E '^Copying' $R/out-h4/*sbuild.log | head -3
echo "  H4 lines naming evilpkg: $(grep -c evilpkg $R/out-h4/*sbuild.log)"
python3 -c "import json,glob; m=json.load(open(glob.glob('$R/out-h4/*-build-manifest.json')[0])); print('  H4 build_dependencies:', [e['package'] for e in m['build_dependencies']], 'chroot', m['chroot']['snapshot'])"
echo "== done $(date -u +%H:%M:%SZ)"
