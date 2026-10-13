# cinnamon-session: SEGV in IceProcessMessages after a compiz restart (UNITY-20260929-012)

Owner: agent B. Closed by UNITY-20261013-007's cinnamon-session 6.4.2-1+unity6 (rule R): no build of its own.

```yaml
task: UNITY-20260929-012
title: cinnamon-session SEGV in IceProcessMessages after a compiz SIGHUP restart ended the session once
package: cinnamon-session
target_series: resolute
status: released in 6.4.2-1+unity6 (UNITY-20261013-007)
```

## The core

The core was saved during UNITY-20260927-040: `~/work/a/040-build/crash/`, 2026-09-29 16:49:18 EEST, SIGSEGV,
`cinnamon-session-binary --session=unity`. The crash file does not record the package version, and the debug symbols
of that build were never published (the pool has dbgsym from +unity4 on), and the builder has no gdb. `core.sh` reads
the core with elfutils and objdump instead (`logs/01-core.txt`):

- **The build.** The main binary in the core has build-id `0da081d8…`. That is the binary of
  cinnamon-session 6.4.2-1+unity3, among the seven published debs. libICE's build-id `65787ecd…` is the builder's
  libice6 2:1.1.1-1build1.
- **The stack (eu-stack, main thread):** frame 0 is `IceProcessMessages` (libICE), frame 1 returns to
  cinnamon-session at 0x2ab61, then the GLib main loop and `csm_main`.
- **The caller.** The call before 0x2ab61 is `IceProcessMessages@plt` at 0x2ab5c. The same function loads the strings
  "CsmXsmpServer: IceProcessMessages returned IceProcessMessagesIOError", "…ConnectionClosed",
  "../cinnamon-session/csm-xsmp-server.c" and "auth_iochannel_watch" (its assertion's function name). So frame 1 is
  `auth_iochannel_watch()` in csm-xsmp-server.c, the watch of a connection that is still being set up.
- **The faulting load.** The faulting instruction at libICE+0x10f5c loads from `iceConn->process_msg_info`
  (offset 0x90 of `struct _IceConn`, checked with `offsetof`), indexed in 40-byte entries
  (`sizeof(_IceProcessMsgInfo)`). That is `iceConn->process_msg_info[opcode - his_min_opcode]`, a table that
  `_IceFreeConnection()` frees.

## Why it is UNITY-20261013-007's defect

UNITY-20261013-007 found the same thing in 6.4.2: `ice_error_handler()` closes the connection on a fatal ICE error
from inside `IceProcessMessages()`. For a connection still being set up, libICE frees it at once. Then two things use
the freed connection:
- `IceProcessMessages()` itself, when it goes on after the error handler returns;
- `auth_iochannel_watch()`, when it closes the connection again on the IO-error path.

-007's own core crashed in the second (`IceCloseConnection` ← `disconnect_ice_connection` ← `auth_iochannel_watch`).
This core crashed in the first: inside `IceProcessMessages()` called by `auth_iochannel_watch()`, on the freed
connection's message table.

6.4.2-1+unity6 (`Fix-connection-lifetime-in-the-XSMP-server.patch`, commits c01299a and 7904214, published
2026-10-13 12:41:10Z) removes the close from the error handler, and gives each connection one owner. With it, the
connection is not freed inside `IceProcessMessages()`, so neither use can happen. +unity7 (live now) carries the same
patch.

The trigger in -040 was a compiz restart with SIGHUP. Most likely the restarted compiz connected its XSMP client
again, which makes a connection in setup, the window the defect needs. That is an inference, not measured. No reproduction was attempted: our rule is no crash
reproduction tools, and the core identifies the defect by itself.

## Target record

UNITY-20261013-007's target verification (`docs/research/UNITY-20261013-007-cinnamon-session-ice-segv/gate/target-verification.txt`)
covers the published +unity6: ordinary XSMP use on target2 with passive uprobes, and every connection closed once.
This task adds no target test of its own: the change and its verification are -007's.

## Closure

Rule R, released_in:
- UNITY-20261013-007, publish record sha256 dd785ca9…;
- change commits c01299a60338b815ef022a795f88176815c8054b and 7904214331aab6e1c4caa24d4eb951f0bda316d7;
- source_repo packages/cinnamon-session.
