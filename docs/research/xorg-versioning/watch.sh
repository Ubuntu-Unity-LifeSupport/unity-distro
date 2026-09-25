#!/bin/sh
# xorg-watch: tell the agents when Ubuntu uploads an xorg-server to resolute
# that is newer than the one our aptly package is based on.
#
# Our package is `<Ubuntu version>+unityN`. Any Ubuntu upload above that base
# will win over ours once it reaches -updates or -security, and it may not carry
# our CVE patches - so our patches must be rebased onto it before that.
#
# For each such upload (any pocket) the script appends ONE line to
# ~/AGENTS-LOG.md and remembers it; it never repeats a line for the same
# version and pocket. Run by the systemd user timer xorg-watch.timer (see
# README.md next to this file). Environment overrides, for testing:
#   XORG_WATCH_LOG    log file      (default ~/AGENTS-LOG.md)
#   XORG_WATCH_STATE  state file    (default ~/.local/state/xorg-watch/seen)
#   XORG_WATCH_BASE   base version  (default: read from our published aptly)
set -u
LOG=${XORG_WATCH_LOG:-$HOME/AGENTS-LOG.md}
STATE=${XORG_WATCH_STATE:-$HOME/.local/state/xorg-watch/seen}
APTLY_PACKAGES=http://192.168.56.10:8080/dists/resolute/main/binary-amd64/Packages
mkdir -p "$(dirname "$STATE")"; touch "$STATE"

if [ -n "${XORG_WATCH_BASE:-}" ]; then
    OURS="$XORG_WATCH_BASE+unity?"; BASE=$XORG_WATCH_BASE
else
    # The published index, not `aptly repo search`: no database lock to collide with.
    OURS=$(curl -s -m 30 "$APTLY_PACKAGES" |
        awk '/^Package: xserver-xorg-core$/{p=1} p&&/^Version:/{print $2; exit}')
    if [ -z "$OURS" ]; then
        echo "xorg-watch: cannot read xserver-xorg-core from our aptly" >&2; exit 1
    fi
    BASE=${OURS%%+unity*}
fi

curl -s -m 60 'https://api.launchpad.net/devel/ubuntu/+archive/primary?ws.op=getPublishedSources&source_name=xorg-server&exact_match=true&distro_series=https://api.launchpad.net/devel/ubuntu/resolute&order_by_date=true' |
python3 -c '
import datetime, json, subprocess, sys
base, ours, state_path = sys.argv[1:4]
try:
    entries = json.load(sys.stdin)["entries"]
except Exception as e:
    sys.exit("xorg-watch: Launchpad answer unreadable: %s" % e)
seen = set(open(state_path).read().split())
now = datetime.datetime.now(datetime.timezone.utc)
for e in entries:
    v, pocket, status = e["source_package_version"], e["pocket"], e["status"]
    if status not in ("Pending", "Published"):
        continue
    if subprocess.run(["dpkg", "--compare-versions", v, "gt", base]).returncode:
        continue
    key = "%s@%s" % (v, pocket)
    if key in seen:
        continue
    when = e["date_published"] or e["date_created"]
    if pocket == "Proposed":
        # SRUs age at least 7 days in -proposed before they may be released.
        t = datetime.datetime.fromisoformat(when)
        left = t + datetime.timedelta(days=7) - now
        eta = "in -proposed since %s; SRU minimum 7 days -> earliest -updates %s (%s left)" % (
            t.strftime("%F %H:%MZ"), (t + datetime.timedelta(days=7)).strftime("%F"),
            "%dd %dh" % (left.days, left.seconds // 3600) if left.total_seconds() > 0 else "0d, may land any time")
    else:
        eta = "already in resolute-%s - apt picks it over ours NOW" % pocket.lower() \
            if pocket != "Release" else "in resolute release pocket"
    print("%s XORG-WATCH new upload %s in resolute-%s (ours %s): %s; rebase needed" % (
        now.strftime("%F %H:%MZ"), v, pocket.lower(), ours, eta))
    with open(state_path, "a") as f:
        f.write(key + "\n")
' "$BASE" "$OURS" "$STATE" >> "$LOG"
