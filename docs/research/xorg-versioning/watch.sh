#!/bin/sh
# xorg-watch: tell the coordinator when Ubuntu uploads an xorg-server to
# resolute that is newer than the one our aptly package is based on.
#
# Our package is `<Ubuntu version>+unityN`. Any Ubuntu upload above that base
# will win over ours once it reaches -updates or -security, and it may not carry
# our CVE patches - so our patches must be rebased onto it before that.
#
# For each such upload (any pocket), once per version and pocket:
#   - an alert for the coordinator (scripts/alerts.py raise, key
#     xorg-server:<version>@<pocket>) - it stays on every taskctl run until C
#     or May acknowledges it (UNITY-20260927-013);
#   - one line in ~/AGENTS-LOG.md, as before.
# The pair is remembered only after the alert is written, so a failed alert is
# retried on the next run. If the check itself fails (aptly or Launchpad
# unreadable) XORG_WATCH_FAIL_LIMIT runs in a row (default 3, i.e. 9 h), that
# is an alert too - a silent watcher is a missed upload.
#
# Run by the systemd user timer xorg-watch.timer (README.md next to this
# file). Environment overrides, for testing:
#   XORG_WATCH_LOG      log file      (default ~/AGENTS-LOG.md)
#   XORG_WATCH_STATE    state file    (default ~/.local/state/xorg-watch/seen;
#                       the failure counter lives next to it)
#   XORG_WATCH_BASE     base version  (default: read from our published aptly)
#   XORG_WATCH_LP_JSON  file with a Launchpad getPublishedSources answer, used
#                       instead of asking Launchpad
#   ALERTS_FILE         alert file    (default ~/coordinator/ALERTS.md)
set -u
LOG=${XORG_WATCH_LOG:-$HOME/AGENTS-LOG.md}
STATE=${XORG_WATCH_STATE:-$HOME/.local/state/xorg-watch/seen}
FAILS=$(dirname "$STATE")/failures
LIMIT=${XORG_WATCH_FAIL_LIMIT:-3}
ALERTS="$(dirname "$(readlink -f "$0")")/../../../scripts/alerts.py"
APTLY_PACKAGES=http://192.168.56.10:8080/dists/resolute/main/binary-amd64/Packages
LP_URL='https://api.launchpad.net/devel/ubuntu/+archive/primary?ws.op=getPublishedSources&source_name=xorg-server&exact_match=true&distro_series=https://api.launchpad.net/devel/ubuntu/resolute&order_by_date=true'
mkdir -p "$(dirname "$STATE")"; touch "$STATE"
TMP=$(mktemp); trap 'rm -f "$TMP"' EXIT

fail() {
    echo "xorg-watch: $1" >&2
    n=$(cat "$FAILS" 2>/dev/null)
    case "$n" in ''|*[!0-9]*) n=0 ;; esac   # a damaged counter restarts at 0
    n=$((n + 1))
    echo "$n" > "$FAILS"
    # the streak is named by the moment it began, so a streak after an
    # acknowledged one - even on the same day - is a new alert
    [ -s "$FAILS.since" ] || date -u +%Y%m%dT%H%M%SZ > "$FAILS.since"
    if [ "$n" -ge "$LIMIT" ]; then
        python3 "$ALERTS" raise --source xorg-watch --key "xorg-watch-failing:$(cat "$FAILS.since")" \
            --message "xorg-watch failed $n runs in a row (last: $1); new resolute xorg-server uploads are not being seen. journalctl --user -u xorg-watch.service" >/dev/null
    fi
    exit 1
}

if [ -n "${XORG_WATCH_BASE:-}" ]; then
    OURS="$XORG_WATCH_BASE+unity?"; BASE=$XORG_WATCH_BASE
else
    # The published index, not `aptly repo search`: no database lock to collide with.
    OURS=$(curl -s -m 30 "$APTLY_PACKAGES" |
        awk '/^Package: xserver-xorg-core$/{p=1} p&&/^Version:/{print $2; exit}')
    [ -n "$OURS" ] || fail "cannot read xserver-xorg-core from our aptly"
    BASE=${OURS%%+unity*}
fi

if [ -n "${XORG_WATCH_LP_JSON:-}" ]; then
    cat "$XORG_WATCH_LP_JSON"
else
    curl -s -m 60 "$LP_URL"
fi |
python3 -c '
import datetime, json, subprocess, sys
base, ours, state_path = sys.argv[1:4]
try:
    entries = json.load(sys.stdin)["entries"]
except Exception as e:
    sys.exit("Launchpad answer unreadable: %s" % e)
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
    print("%s\t%s XORG-WATCH new upload %s in resolute-%s (ours %s): %s; rebase needed" % (
        key, now.strftime("%F %H:%MZ"), v, pocket.lower(), ours, eta))
' "$BASE" "$OURS" "$STATE" > "$TMP" 2> "$TMP.err" || { err=$(cat "$TMP.err"); rm -f "$TMP.err"; fail "${err:-Launchpad check failed}"; }
rm -f "$TMP.err"

TAB=$(printf '\t')
unraised=0
while IFS="$TAB" read -r key line; do
    [ -n "$key" ] || continue
    if out=$(python3 "$ALERTS" raise --source xorg-watch --key "xorg-server:$key" --message "$line"); then
        # "already raised": another run got there first; do not log it twice
        case "$out" in "already raised:"*) ;; *) echo "$line" >> "$LOG" ;; esac
        echo "$key" >> "$STATE"
    else
        # keep the log line, leave the upload unseen so the next run retries it
        echo "$line (ALERT NOT RAISED, retried next run)" >> "$LOG"
        unraised=$((unraised + 1))
    fi
done < "$TMP"
[ "$unraised" -eq 0 ] || fail "cannot raise the coordinator alert for $unraised upload(s) (scripts/alerts.py)"
rm -f "$FAILS" "$FAILS.since"
