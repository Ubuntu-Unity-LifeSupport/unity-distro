#!/bin/sh
# UNITY-20260927-040 target verification, after the switch: unity +unity12
# from our published repository by apt. The tests had put the same version on
# from the gated debs with apt-get install ./*.deb, so reinstall it from the
# repository; then the published packages are what runs.
set -u
sudo apt-get update 2>&1 | grep -E "^(E|W|Err):" || echo "apt-get update: no E/W"
grep -E "^Date:" /var/lib/apt/lists/192.168.56.10*_InRelease
apt-cache policy unity libunity-core-6.0-9 | grep -E "^[a-z]|Installed|Candidate|\*\*\*"
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q --reinstall unity libunity-core-6.0-9 unity-schemas \
  unity-services unity-uwidgets 2>&1 | grep -E "^(Get|Получено|Пол:|Setting up|Настраивается)" | head -8
sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -q 2>&1 | tail -1
dpkg-query -W unity libunity-core-6.0-9 unity-schemas unity-services unity-uwidgets
sha256sum /usr/lib/x86_64-linux-gnu/compiz/libunityshell.so /usr/lib/x86_64-linux-gnu/libunity-core-6.0.so.9
