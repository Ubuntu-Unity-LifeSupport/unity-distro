#!/bin/sh
# UNITY-20260929-016, Verifier round 1: does build/sbuild-config.pl (SBUILD_CONFIG)
# override a user sbuild config that adds a local repository and a chroot
# setup command? Control: plain sbuild with that config shows both in its log.
W=/home/claude/work/a/unity-distro-016
R=/home/claude/work/a/016-real
T=20260929T201245Z
C=/home/claude/.cache/sbuild/chroots/resolute-amd64-$T.tar.zst
X=$R/hostile-xdg
rm -rf -- "${X:?}" "${R:?}/evilrepo" "${R:?}/out-h2" "${R:?}/h1"
mkdir -p "$X/sbuild" "$R/evilrepo" "$R/h1"
: > "$R/evilrepo/Packages"
cat > "$X/sbuild/config.pl" <<EOF
\$unshare_tmpdir_template = '/var/tmp/sbuild-claude/sbuild-unshare-XXXXXX';
\$extra_repositories = ['deb [trusted=yes] file:$R/evilrepo ./'];
\$external_commands = { "chroot-setup-commands" => [['echo', 'HOSTILE-SETUP-MARKER']] };
1;
EOF
cd "$W" || exit 1
echo "== H1 control: plain sbuild, hostile user config, no SBUILD_CONFIG"
cp -a $R/tiny013 $R/h1/tiny013
( cd $R/h1/tiny013 && XDG_CONFIG_HOME=$X sbuild -d resolute --no-clean-source --verbose --chroot-mode=unshare --chroot=$C > $R/h1/sbuild.log 2>&1; echo "H1 exit=$?" )
grep -n -E 'evilrepo|HOSTILE-SETUP-MARKER' $R/h1/sbuild.log | head -6
echo "== H2 build_sbuild.py, same hostile user config"
XDG_CONFIG_HOME=$X python3 scripts/build_sbuild.py --task-id UNITY-20260929-016 --source-repo $R/tiny013 \
  --target-series resolute --output-dir $R/out-h2 --chroot-tarball $C; echo "H2 exit=$?"
echo "  H2 lines naming evilrepo or the marker: $(grep -c -E 'evilrepo|HOSTILE-SETUP-MARKER' $R/out-h2/*sbuild.log)"
grep -n -E '^I: Unpacking|snapshot.ubuntu.com.*InRelease|upgraded,' $R/out-h2/*sbuild.log | head -6
echo "== done $(date -u +%H:%M:%SZ)"
