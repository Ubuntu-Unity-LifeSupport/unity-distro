#!/bin/bash
# trial.sh begin TAG APP [ARGS...] | trial.sh end TAG - one attempt of the counted series, measured by events:
#   begin: the libunity-gtk4-menu0 version, start.sh TAG APP (NOAUDIT=1, so the panel and hud-service are the only
#          menu subscribers), the panel service's entry table (sync.sh), then popwatch.sh for 25 s in the background.
#          Exactly one key then comes from the host, then Escape.
#   end:   after popwatch has ended: its lines (popup mapped / unmapped), then stop.sh TAG (ShowEntry,
#          EntryActivated, the menu calls and the active-window changes).
set -u
B=~/b1203
case $1 in
  begin)
    tag=$2; shift 2
    echo "== $tag on $(dpkg-query -W -f='libunity-gtk4-menu0 ${Version}, ' libunity-gtk4-menu0)$(dpkg-query -W -f='libgtk-nocsd0 ${Version}, ' libgtk-nocsd0)$(dpkg-query -W -f='unity ${Version}' unity)"
    NOAUDIT=1 bash $B/start.sh "$tag" "$@" 2>&1 | grep -v -e '^pkill' -e '^Try '
    bash $B/sync.sh "$tag-before-key"
    nohup bash $B/popwatch.sh 25 > /tmp/pop-$tag.txt 2>&1 < /dev/null &
    sleep 0.5; echo "  popwatch started: $(head -1 /tmp/pop-$tag.txt)"
    ;;
  end)
    tag=$2
    while pgrep -x -f "bash $B/popwatch.sh 25" > /dev/null; do sleep 0.5; done
    echo "== $tag: popup watch"; sed 's/^/  /' /tmp/pop-$tag.txt
    bash $B/stop.sh "$tag" | grep -v -e indicator-datet -e indicator-sessi -e DescribeAll
    ;;
esac
