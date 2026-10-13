#!/bin/sh
# UNITY-20261013-022: the user dbus.service as systemd sees it. Prints the raw
# `systemctl --user show` to $1.raw and the same with runtime fields removed
# to $1.filtered (the filter is the grep below).
systemctl --user show dbus.service > "$1.raw"
grep -vE '^(.*Timestamp.*|.*Monotonic=.*|MainPID|ExecMainPID|ExecMainCode|ExecMainStatus|ExecMainHandoffTimestamp.*|InvocationID|ControlGroupId|Memory[A-Za-z]*|CPU[A-Za-z]*|IO[A-Za-z]*|Tasks[A-Za-z]*|IP[A-Za-z]*|Effective[A-Za-z]*|ExecStart|ExecStartEx|ExecReload|ExecReloadEx|StatusText|StatusErrno|NRestarts|ActiveEnterTimestamp.*|StateChangeTimestamp.*|InactiveExitTimestamp.*|ConditionTimestamp.*|AssertTimestamp.*|Result|ReloadResult|CleanResult|LiveMountResult|ControlPID|GuessMainPID|Id|Names|Following|SubState|ActiveState|LoadState|UnitFileState|UnitFilePreset|FreezerState|TimeoutStartFailureMode|ManagedOOM[A-Za-z]*Effective.*|NotifyAccessEffective)=' "$1.raw" > "$1.filtered"
wc -l "$1.raw" "$1.filtered"
