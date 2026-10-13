#!/bin/bash
# check-1013.sh STEP - on target2 (as mike over ssh): unity-session 49.4+unity2 (Recommends libunity-gtk4-menu0)
# against the live archive, after a restore of Clean-2, 2026-10-13. The new unity-session comes from the gated
# snapshot only after publication, so before it the build's deb is offered through a local file repository
# (~/b037/repo: the deb and a Packages index made with dpkg-scanpackages on the builder), next to the live archive.
#   setup:     confirm the restore; add the live archive and the local repository; apt-get update
#   fresh:     the fresh-install resolution: apt-get -s install unity-session against an empty dpkg status
#              (Dir::State::status=/dev/null equivalent), so apt resolves it as on a new system; is libunity-gtk4-menu0
#              in the plan, and as what (Recommends)
#   norec:     apt-get -s full-upgrade --no-install-recommends: unity-session upgraded, libunity-gtk4-menu0 not pulled
#   upgrade:   apt-get full-upgrade with apt's default (install-recommends): libunity-gtk4-menu0 installed with
#              unity-session; versions and the reason apt gives (apt-mark showauto)
set -u
B=~/b037
case $1 in
  setup)
    echo "== setup at $(date -u +%FT%TZ), boot $(uptime -s)"
    ls -d ~/.dirty ~/b1204t ~/b1313 2>&1 | sed 's/^/  /'
    echo "  sources.list.d: $(ls /etc/apt/sources.list.d/ | xargs)"
    dpkg-query -W unity-session libunity-gtk4-menu0 2>&1 | sed 's/^/  /'
    touch ~/.dirty
    sudo install -m644 $B/unity-distro.asc /etc/apt/keyrings/unity-distro.asc
    sudo install -m644 $B/unity-distro.sources /etc/apt/sources.list.d/unity-distro.sources
    echo "deb [trusted=yes] file:$B/repo ./" | sudo tee /etc/apt/sources.list.d/b037-local.list > /dev/null
    sudo apt-get update -q > /tmp/u037.log 2>&1; echo "  update rc=$?"
    grep -h '^Date' /var/lib/apt/lists/192.168.56.10*_InRelease | sed 's/^/  live /'
    apt-cache policy unity-session libunity-gtk4-menu0 | sed 's/^/  /' ;;
  fresh)
    echo "== fresh-install resolution at $(date -u +%FT%TZ)"
    : > /tmp/empty-status
    apt-get -s -o Dir::State::status=/tmp/empty-status install unity-session > /tmp/fresh.txt 2>&1; echo "  apt-get -s install rc=$?"
    echo "  packages in the plan: $(grep -c '^Inst ' /tmp/fresh.txt)"
    grep -E '^Inst (unity-session|libunity-gtk4-menu0|libgtk-nocsd0) ' /tmp/fresh.txt | sed 's/^/  /'
    echo "  the same with --no-install-recommends:"
    apt-get -s -o Dir::State::status=/tmp/empty-status --no-install-recommends install unity-session > /tmp/fresh-norec.txt 2>&1
    grep -E '^Inst (unity-session|libunity-gtk4-menu0|libgtk-nocsd0) ' /tmp/fresh-norec.txt | sed 's/^/  /'
    echo "  (libunity-gtk4-menu0 lines without recommends: $(grep -c '^Inst libunity-gtk4-menu0 ' /tmp/fresh-norec.txt))" ;;
  norec)
    echo "== full-upgrade --no-install-recommends, simulated, at $(date -u +%FT%TZ)"
    sudo apt-get -s full-upgrade --no-install-recommends > /tmp/norec.txt 2>&1; echo "  rc=$?"
    grep -E '^Inst (unity-session|libunity-gtk4-menu0|libgtk-nocsd0) ' /tmp/norec.txt | sed 's/^/  /'
    echo "  (libunity-gtk4-menu0 lines: $(grep -c '^Inst libunity-gtk4-menu0 ' /tmp/norec.txt))" ;;
  upgrade)
    echo "== full-upgrade (apt's default, install-recommends $(apt-config dump | grep -i 'APT::Install-Recommends ' | cut -d' ' -f2)) at $(date -u +%FT%TZ)"
    # wait for unattended-upgrades and the dpkg lock (a first attempt failed on the lock: the process started after a
    # pgrep-only check)
    for i in $(seq 180); do
      n=$(ps -eo args | grep -c "[/]usr/bin/unattended-upgrade$"); l=$(sudo fuser /var/lib/dpkg/lock-frontend 2>/dev/null | wc -w)
      [ "$n" = 0 ] && [ "$l" = 0 ] && break; sleep 10
    done
    sudo DEBIAN_FRONTEND=noninteractive apt-get full-upgrade -y -q > /tmp/up037.log 2>&1; echo "  full-upgrade rc=$?"
    grep -E '^(Get|Пол):.*(unity-session|libunity-gtk4-menu0) ' /tmp/up037.log | sed 's/^/  /'
    grep -E "The following NEW packages|Следующие НОВЫЕ пакеты" -A3 /tmp/up037.log | sed 's/^/  /'
    dpkg-query -W unity-session libunity-gtk4-menu0 libgtk-nocsd0 | sed 's/^/  /'
    echo "  automatically installed: $(apt-mark showauto libunity-gtk4-menu0)"
    echo "  installed unity-session file sha256: $(sha256sum $B/repo/unity-session_49.4+unity2_all.deb | cut -c1-16)"
    grep -E " (install|upgrade) (unity-session|libunity-gtk4-menu0):" /var/log/dpkg.log | tail -3 | sed 's/^/  /' ;;
esac
