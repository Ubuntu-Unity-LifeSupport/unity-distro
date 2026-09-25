#!/bin/bash
# Which xserver-xorg-core would apt pick? Isolated apt state; the system is untouched.
# usage: run.sh <installed-version> <repo dirs under /tmp/sim...>
inst=$1; shift; R=/tmp/sim/root; rm -rf $R; mkdir -p $R/lists/partial $R/cache/archives/partial $R/etc/parts
for f in /var/lib/apt/lists/*_Packages /var/lib/apt/lists/*_InRelease; do case $f in *192.168.56.10*) ;; *) cp $f $R/lists/;; esac; done
cp /etc/apt/sources.list.d/ubuntu.sources $R/etc/parts/
: > $R/etc/sources.list; for d in "$@"; do echo "deb [trusted=yes] file:/tmp/sim/$d ./" >> $R/etc/sources.list; done
awk -v v="$inst" '/^Package: xserver-xorg-core$/{p=1} p&&/^Version:/{$0="Version: " v; p=0} {print}' /var/lib/dpkg/status > $R/status
O="-o Dir::State::Lists=$R/lists -o Dir::Cache=$R/cache -o Dir::State::status=$R/status -o Dir::Etc::SourceList=$R/etc/sources.list -o Dir::Etc::SourceParts=$R/etc/parts -o APT::Get::Always-Include-Phased-Updates=true"
apt-get $O update -qq >/dev/null 2>&1
apt-cache $O policy xserver-xorg-core | sed -n 2,3p | tr -s ' ' | tr '\n' ';'; echo
