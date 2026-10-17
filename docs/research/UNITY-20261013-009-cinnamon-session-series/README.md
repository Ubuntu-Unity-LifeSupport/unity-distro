# cinnamon-session +unity8 series (UNITY-20261013-009 and others)

Owner: agent B (target2). Paused 2026-10-13 for UNITY-20260929-012, resumed 2026-10-17. Result: 6.4.2-1+unity8 with
UNITY-20260927-014, UNITY-20261013-009 and UNITY-20261013-010. Closed without code:
- UNITY-20260929-007, by design;
- UNITY-20261013-011, won't fix;
- UNITY-20261002-010, not cinnamon-session's (moved to UNITY-20261017-001).

Base: the published 6.4.2-1+unity7 (A's `a/UNITY-20261013-016`, 7393f0e).

## Upstream check (subagent sweep, 2026-10-13; notes in ~/work/b/evidence/UNITY-20261013-009-upstream-sweep-notes.md on builder)

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

## 6.4.2-1+unity8 (package branch b/UNITY-20261013-009, b526443)

The package carries three patches on +unity7 (7393f0e), one commit each, plus the changelog. The design is DESIGN.md
(Design Challenger round 1 REVISE for item 1; round 2 APPROVE for the whole series).

| commit | patch | task |
|---|---|---|
| 9210524 | `Connect-a-client-s-disconnected-signal-only-once.patch` | UNITY-20261013-009 |
| 7ad4d3e | `Clear-the-client-s-watch-id-when-its-IO-watch-stops.patch` | UNITY-20261013-010 |
| 269909e | `Give-clients-of-an-inactive-session-a-grace-period-befo.patch` | UNITY-20260927-014 |

**Build** (`build-unity8/`): sbuild on the new chroot resolute-amd64-20261017T042748Z (the previous one was older than
7 days), `DEB_BUILD_OPTIONS=parallel=4`, status successful, lintian pass. The compiler warnings in the changed files
are the existing ones (deprecated `g_type_class_add_private`, `fscanf`); none is on a changed line.

**target2** (Clean-2 → live, then `dpkg -i` of this build with `dpkg -V` clean; the unstripped copy of the same build,
`.text` identical, for the probes; logs/15):

| test | log | result |
|---|---|---|
| -014: switched away, then Logout(1) | logs/16 | **the session ends after 62 s**: Logout at 209.8 s; at 240.9 s (the end of the 30 s grace) "Client6 (compiz) failed to reply" is logged and the session moves to END_SESSION, with no dialog launched; END_SESSION ends at its 30 s timeout and the session is gone at 271.6 s. With +unity7 the session was still running after more than 60 s, waiting on an invisible dialog (logs/07, logs/10) |
| -014 round 2: the slow XSMP client (`xsmp-slow.c`, allowed by C) in a switched-away session | logs/17 | the client answers the registration SaveYourself at once. It gets the end-session SaveYourself (shutdown, interaction allowed) and answers it **3 s late** with an InteractRequest: interaction is granted at once and the client completes its save, so a late answer is honoured, not dropped. Only compiz, which never answers, is dropped after the grace period. The logout then goes on (END_SESSION's fast SaveYourself) and ends in 62 s. The first attempt (logs/17-…-test-bug) had a test-client bug: it answered the registration SaveYourself with an InteractRequest (BadState) and never completed it, so it was dropped as silent. Fixed in the client, not in cinnamon-session |
| -009 | logs/18 | `on_client_disconnected` and `_disconnect_client` **once** per client, for an xterm exit and a SIGKILL (twice on +unity7) |
| -010 | logs/18 | the watch returns 0 after the SIGKILL; no GLib critical in the journal |
| a foreground logout | logs/18 | ends in 1.8 s |
| a foreground logout with at-spi2-registryd stopped | logs/19 (and .png) | **unchanged**: Unity's end-session dialog is shown, a second Logout gets NotInRunning, and after SIGCONT the session ends in about 1 s |

target2 was restored to Clean-2 afterwards and confirmed inside (logs/20).

## Verification (2026-10-17)

An independent Verifier (an ephemeral general-purpose subagent) reviewed the code, the build records and the logs.
Nothing was reproduced independently. **Verdict: PASS.**
- The patches match DESIGN.md and the Design Challenger's conditions.
- The build manifest matches b526443: tree, artifacts, and `.debian.tar.xz` identical to `git archive`.
- The timings and counts in logs/16-19, and the controls in logs/02, 07 and 10, support this card.

Non-blocking notes:
- The patch `Date:` headers are round times, a few minutes later than the commits.
- The new patches carry `Assisted-by: Claude Code:claude-opus-5` (the form of linuxmint/cinnamon-session#220), while
  the rest of the series uses `Assisted-by: LLM <model>`. To align before anything goes upstream.
- That a client which keeps interacting holds the logout rests on code reading (its JIT inhibitor leads to the dialog
  path, as today). In logs/17 the client finished its save as soon as interaction was granted.
- Known limitation: in an inactive session, a client that answers late with is_ok=FALSE, or an inhibitor an
  application registered itself, still leads to a dialog nobody sees once the grace period ends. Reboot and
  shutdown are out of scope.
- A stray editor backup of a patch in the package worktree (ignored, not in the source package) was deleted.

## Publication (2026-10-17)

The slot steps were:
- origin/main merged (690aa94);
- the db backup `~/backups/UNITY-20261013-009-20261017T060806Z`;
- `repo add` of the manifest's artifacts, with the pool sha256 equal to the manifest;
- the snapshot `unity-resolute-20261013-009`, which is the live `unity-resolute-20261013-029` plus the four +unity8
  records (`gate/snapshot-diff.txt`);
- version safety SAFE;
- the peer ACK from A;
- the gate as the last commit (94a6c0b, sha256 558a6b0d…);
- C's approval, with the gaps UNITY-20261017-002 and UNITY-20261017-003.

Published 2026-10-17T06:12:02Z in one run.

Target verification (`gate/target-verification.txt`, logs/21-24):
- Clean-2 → live; the downloaded deb is the gated one.
- A switched-away Logout(1) ends in 61.6 s.
- A foreground logout ends in 1.6 s, with 0 crash reports.
- target2 was restored to Clean-2 afterwards.
