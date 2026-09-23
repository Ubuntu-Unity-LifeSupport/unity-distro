#!/bin/sh
# make-chroot.sh SRC ROOT - resolute chroot with Unity's build-deps, our nux
# (aptly, PCRE2 fix) and what the tests need to run. Run on builder.
# SRC: a pristine `git archive` of packages/unity at ubuntu/devel.
# ROOT: a directory outside $HOME, e.g. /var/tmp/sbuild-claude/unity-ut.
SRC=$1 ROOT=$2
TMPDIR=/var/tmp/sbuild-claude mmdebstrap --mode=unshare --variant=buildd --components="main universe" \
  --include=xvfb,xauth,dbus,dbus-x11,patch,cmake \
  --customize-hook="copy-in $SRC /" \
  --customize-hook="upload /srv/aptly/public/unity-distro-archive.asc /etc/apt/keyrings/unity-distro.asc" \
  --customize-hook='echo "deb [signed-by=/etc/apt/keyrings/unity-distro.asc] http://192.168.56.10:8080 resolute main" > "$1/etc/apt/sources.list.d/unity-distro.list"' \
  --customize-hook='chroot "$1" apt-get update' \
  --customize-hook='chroot "$1" apt-get -y build-dep /src' \
  --customize-hook='chroot "$1" apt-get -y install xserver-xorg-core xserver-xorg-video-dummy x11-utils libgl1-mesa-dri' \
  resolute "$ROOT" http://de.archive.ubuntu.com/ubuntu
# Then: copy fix.diff and test.diff (git diff of the commit's two parts),
# build.sh, runtest.sh, dummy.conf into ROOT, and
#   enter.sh ROOT /build.sh && enter.sh ROOT /runtest.sh
# For the run without the fix: enter.sh ROOT sh -c 'cd /src && patch -R -p1 < /fix.diff && cd obj && make test-gnome-session-manager'
