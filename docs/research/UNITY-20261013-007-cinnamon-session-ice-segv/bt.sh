# bt.sh moved here from UNITY-20261013-002; the gdb calls that produced logs/bt-*.txt were the simpler ones in the card (debuginfod off).
#!/bin/bash
# bt.sh - on target2 (test target): symbolized backtraces of the three apport crashes of 2026-10-13 06:xx (guest):
# installs the dbgsym packages of our builds from the live archive (cinnamon-session +unity5, light-locker +unity3),
# uses Ubuntu's debuginfod for the archive libraries, and runs gdb in batch mode on each unpacked CoreDump
# (/tmp/b1307/u-*/CoreDump, from apport-unpack). Output: /tmp/b1307/bt-<name>.txt
set -u
W=/tmp/b1307
cd $W || exit 1
for f in cinnamon-session-dbgsym_6.4.2-1%2Bunity5_amd64.ddeb:c/cinnamon-session light-locker-dbgsym_1.8.0-3ubuntu4%2Bunity3_amd64.ddeb:l/light-locker; do
  name=${f%%:*}; dir=${f##*:}
  python3 -c "import sys,urllib.request; open(sys.argv[2],'wb').write(urllib.request.urlopen(sys.argv[1],timeout=60).read())" \
    "http://192.168.56.10:8080/pool/main/$dir/$name" "$W/${name//%2B/+}"
  echo "  downloaded ${name//%2B/+}: sha256 $(sha256sum < "$W/${name//%2B/+}" | cut -c1-16)"
done
sudo dpkg -i $W/*.ddeb > $W/ddeb-install.log 2>&1; echo "  dpkg -i ddebs rc=$?"
dpkg-query -W cinnamon-session cinnamon-session-dbgsym light-locker light-locker-dbgsym compiz-core libice6 | sed 's/^/  /'
export DEBUGINFOD_URLS=https://debuginfod.ubuntu.com
for c in cinnamon-session:/usr/lib/x86_64-linux-gnu/cinnamon-session/cinnamon-session-binary:u-_usr_lib_x86_64-linux-gnu_cinnamon-session_cinnamon-session-binary \
         compiz:/usr/bin/compiz:u-_usr_bin_compiz light-locker:/usr/bin/light-locker:u-_usr_bin_light-locker; do
  IFS=: read -r name exe dir <<< "$c"
  {
    echo "== $name: $exe, core $dir/CoreDump ($(stat -c %s $dir/CoreDump) bytes)"
    grep -aE '^(Date|Package|ExecutablePath|Signal|SignalName|ProcCmdline|ProcEnviron|SegvAnalysis|SegvReason)' \
      /var/crash/${dir#u-}.1000.crash | grep -v '^ ' | head -12
    timeout 600 gdb -q -batch -nx -iex 'set debuginfod enabled on' -ex 'set pagination off' -ex 'set print frame-arguments scalars' \
      -ex 'info signal SIGSEGV' -ex 'thread' -ex 'bt full 25' -ex 'info registers rip' -ex 'x/6i $pc-12' \
      -ex 'thread apply all bt 12' -ex 'info sharedlibrary' "$exe" "$dir/CoreDump" 2>&1 \
      | grep -vE '^(Downloading|Download failed|warning: could not find|Reading symbols|  *\[|$)'
  } > $W/bt-$name.txt 2>&1
  echo "  bt-$name.txt: $(wc -l < $W/bt-$name.txt) lines"
done
