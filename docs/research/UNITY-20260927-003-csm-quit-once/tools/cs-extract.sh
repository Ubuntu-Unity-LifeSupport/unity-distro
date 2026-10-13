#!/bin/sh
# UNITY-20260927-003: the lines that matter from the previous boot after
# tools/cs-delay.sh, plus counts. Run on target as mike (journal group).
J="journalctl -b -1 -o short-precise --no-pager"
$J -t delaytest -t cinnamon-session -t cinnamon-session-binary -t systemd-logind \
  | grep -E 'action=|clicking|calling|Requesting system|Unable to|not confirmed|PrepareForShutdown|prepared|rebooting|powering|Power key|delaytest[^:]*: t=(1|2|3|4|5|6|10|30|60) ' \
  | cut -c1-260
echo "--- counts (cinnamon-session-binary tag only, to avoid the doubled stderr copy)"
for p in 'Requesting system restart' 'Requesting system shutdown' 'OperationInProgress' 'not confirmed by logind'; do
  printf '%s: %s\n' "$p" "$($J -t cinnamon-session-binary | grep -c "$p")"
done
echo "--- last delaytest tick with the session manager alive"
$J -t delaytest | grep -E 'csm=[0-9]' | tail -1 | cut -c1-200
echo "--- first tick without it"
$J -t delaytest | grep -E 't=[0-9]+ .*csm=$' | head -1 | cut -c1-200
echo "--- logind bus traffic (/var/tmp/cs-busmon.txt, if tools/cs-delay.sh recorded it)"
if [ -r /var/tmp/cs-busmon.txt ]; then
  grep -E '^(‣|  Sender|  Member|  ErrorName)' /var/tmp/cs-busmon.txt \
    | grep -vE 'Member=(ListInhibitors|GetSession|ListSessions|GetUser|CanReboot|CanPowerOff|CanSuspend|CanHibernate|CanHybridSleep|CanSuspendThenHibernate|Inhibit)$' \
    | grep -B2 -A0 -E 'Member=(Reboot|PowerOff|PrepareForShutdown)|ErrorName=org.freedesktop.login1' \
    | cut -c1-200
else
  echo "(none)"
fi
echo "--- logind's replies to the session manager's Reboot/PowerOff calls"
if [ -r /var/tmp/cs-busmon.txt ]; then
  awk '/^‣/{hdr=$0} /Member=(Reboot|PowerOff)$/{split(hdr,a,"Cookie="); split(a[2],b," "); c[b[1]]=1}
       /^‣ Type=(method_return|error)/{if (match($0,/ReplyCookie=[0-9]+/)) {rc=substr($0,RSTART+12,RLENGTH-12); if (rc in c) {pend=1; line=$0; next}}}
       pend && /ErrorName=/{print line; print; pend=0; next}
       pend && /^‣/{print line; pend=0}' /var/tmp/cs-busmon.txt | cut -c1-200
fi
