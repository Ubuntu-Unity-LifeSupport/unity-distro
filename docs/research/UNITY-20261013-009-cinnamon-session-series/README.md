# cinnamon-session +unity8 series (UNITY-20261013-009 and others)

Owner: agent B (target2). Paused 2026-10-13 for UNITY-20260929-012, resumed 2026-10-17.

Base: the published 6.4.2-1+unity7 (A's `a/UNITY-20261013-016`, 7393f0e).

## Upstream check (subagent sweep, 2026-10-13; notes in /srv/build/B-series-sweep/notes.md)

linuxmint/cinnamon-session master af94f9b and the tags 6.6.4 and 6.7.6-unstable fix none of the items below.
`csm-xsmp-server.c` and `csm-xsmp-client.c` are identical on 6.4.2 and master.

## Measured on target2 so far

The setup was Clean-2 → live, with cinnamon-session 6.4.2-1+unity7. The installed binary was replaced by an
unstripped copy of the same build (eu-unstrip of the binary and its dbgsym; `.text` identical, sha256 530b1f70…), so
bpftrace can probe static functions by name (`measure.sh`, logs/01).

| task | what was measured | result |
|---|---|---|
| UNITY-20261013-009 | `on_client_disconnected` and `_disconnect_client` per client: an xterm that exits normally, and one killed with SIGKILL (logs/02) | **twice per client**, for the same client pointer, in both cases. Confirmed |
| UNITY-20261013-010 | `client_iochannel_watch`'s return value; GLib criticals in the journal and `~/.xsession-errors` (logs/02) | the watch returns FALSE after the SIGKILL. No "Source ID … not found" critical was found; to look at more closely |
| UNITY-20261002-010 | SIGKILL of unity-fallback-mount-helper and of unity-indicator-appearance (logs/02) | neither is started again, but **cinnamon-session does not start them in a Unity session**. `unity-session.target` requires `xdg-desktop-autostart.target`, so systemd-xdg-autostart-generator runs every autostart app as `app-…@autostart.service`, and it writes `Restart=no` even for `X-GNOME-AutoRestart=true` (unity-indicator-appearance). unity-fallback-mount-helper's .desktop has no AutoRestart at all, in any published unity-settings-daemon. The layer is the Unity session's systemd setup, not cinnamon-session (and not upstream linuxmint/cinnamon-session#187, which is about cinnamon-session's own launcher) |
| UNITY-20260927-014 | `dm-tool switch-to-greeter`, then Logout(1) | **not measured yet**: dm-tool refused ("XDG_SEAT_PATH not defined"; neither our environment nor compiz's has it). logs/04 are therefore ordinary foreground Logout(1) runs: the session ends in about 1 s |
| foreground logout | `end_phase` during `cinnamon-session-quit --logout --no-prompt` and Logout(1) (logs/03, 04) | 4 `end_phase` calls, the last two 2-6 ms apart. The phase values are not read, so nothing is concluded |
| UNITY-20260929-007 | logout with at-spi-registryd stopped (SIGSTOP, then SIGCONT; allowed by C) | not run yet (`measure.sh stopped`) |
| UNITY-20261013-011 | code reading | the SmsConn is not freed on refusal, neither by cinnamon-session nor by libSM/libICE (sweep) |

## Next, when the series resumes

- -014: run the switch step with the session's seat path (from `loginctl`), not the environment.
- -0929-007: the `stopped` step.
- -010: read the client's finalize path.
- -1002-010: to C, re-scoped to unity-session.
- Then the DC for -009, -010, -011 (and -0929-007 if it reproduces). target2 goes back to Clean-2 first.

## Measured 2026-10-17 (target2: Clean-2 → live, InRelease 2026-10-17 03:12:42 UTC, cinnamon-session +unity7)

Before the setup, target2's clock was days behind after a host sleep. A cold cycle corrected it (chrony stepped 2.97 s),
as UNITY-20260929-022 describes.

`measure.sh` now lists the session manager's clients with their processes right before each logout. The client
numbers differ from boot to boot, so a "ClientN failed to reply" warning only means something next to that list.

| task | run | result |
|---|---|---|
| UNITY-20260927-014 | `switch` (logs/07, logs/10): `dm-tool switch-to-greeter` with lightdm's Seat0 path, then Logout(1) | **reproduces.** The session is inactive (`Active=no`, the greeter on seat0). **compiz** (Client5 in logs/10) does not reply to the end-session query. cinnamon-session then asks for the end-session dialog: the shell's dialog times out after 25 s, then the GTK fallback `cinnamon-session-quit --sm-owned --logout` is started on a display nobody sees, with `CRITICAL: Session not in running phase, previous dialog may have exited unexpectedly`. The session is still running 60 s and more later. Our +unity2 patch ("Ask for a dialog when inhibitors have nobody to be shown to") does not cover this case: **not FIXED_LOCAL** |
| UNITY-20260929-007 | `stopped` (logs/08, logs/12): at-spi2-registryd stopped with SIGSTOP, a foreground logout, a second Logout(1) after 10 s, then SIGCONT | **reproduces as reported.** The client that does not reply is **at-spi2-registryd** (Client4 in logs/12). The logout waits; the second request gets `NotInRunning: Logout interface is only available during the Running phase`; after SIGCONT the session ends within about 1 s. Whether a "not responding" dialog was shown in the foreground was not captured (no screenshot) |
| control | the same `stopped` run, with at-spi2-registryd not stopped by mistake (logs/11) | a foreground logout ends within about 1 s, with 4 `end_phase` calls |
| UNITY-20261013-010 | code reading of `csm-xsmp-client.c` | both close paths (`close_connection_callback` and the IO-error path) emit `disconnected` while the watch callback still holds its reference. The client is finalized inside the dispatch, while `watch_id` still names the live source, so `g_source_remove` finds it and no critical is logged. That matches what was measured: every traced exit returned 1, or 0 on the IO error, and no critical appeared. A stale `watch_id` would matter only on the `IceProcessMessagesConnectionClosed` path if the client outlived the callback. No trace showed that path. **Latent, not reproduced** |

target2 was restored to Clean-2 afterwards and confirmed inside (logs/13).
