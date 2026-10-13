# cinnamon-session: SEGV in IceProcessMessages after a compiz restart (UNITY-20260929-012)

Owner: agent B. Open.

```yaml
task: UNITY-20260929-012
title: cinnamon-session SEGV in IceProcessMessages after a compiz SIGHUP restart ended the session once
package: cinnamon-session
target_series: resolute
status: open - root cause under investigation, held privately pending a fix
```

## The observed crash

The core was saved during UNITY-20260927-040, on 2026-09-29 16:49:18 EEST. It is a SIGSEGV of
`cinnamon-session-binary --session=unity` (6.4.2-1+unity3, identified by build-id; libice6 2:1.1.1-1build1):

- frame 0 is `IceProcessMessages` (libICE);
- frame 1 is `auth_iochannel_watch` in csm-xsmp-server.c;
- the fault is a read at address 0.

## Correction

An earlier version of this card linked the crash to UNITY-20261013-007's defect (fixed in 6.4.2-1+unity6) and
proposed closing it as released there. That link is withdrawn: the independent verification showed that the crash
does not fit -007's mechanism. The root cause is under investigation and is held privately until a fix is
available.
