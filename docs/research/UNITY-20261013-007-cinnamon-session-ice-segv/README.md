# cinnamon-session: session manager crash when an XSMP client connection fails during setup (UNITY-20261013-007)

Owner: agent B (target2).

```yaml
task: UNITY-20261013-007
package: cinnamon-session (6.4.2-1+unity5 installed from live)
target_series: resolute
status: REVIEW - fixed in 6.4.2-1+unity6 (local build), target check PASS, independent Verifier PASS (2026-10-13)
```

## What happened (target2, 2026-10-13, logs/01)

The setup was Clean-2 → live (Release Date 2026-10-13 01:41:51 UTC). In the boot where the upgrade ran,
unattended-upgrades held the dpkg lock for about 20 minutes. Then came the first cold boot after the upgrade
(06:05:19 guest time, 03:05Z), with autologin into Unity:

- **06:06:46** compiz starts. At 06:06:47.099 it logs `SmcOpenConnection failed: IO error occurred opening
  connection`.
- **06:06:47.099** In the same instant the kernel logs: `cinnamon-sessio[2269]: segfault at 75e33e4666a8 ip
  000075e47390084c … error 4 in libICE.so.6.3.0`. The session leader is gone.
- **06:06:47.2-.7** compiz logs `Failed to load plugin: composite`, then the opengl init fails, then
  `/usr/share/compiz/resize.xml:150: I/O error : Invalid bytes in character encoding`. The file is intact on disk:
  `dpkg --verify` finds no difference.
- **06:07:08** compiz SIGSEGV. **06:07:15** the restarts of unity7.service fail with `Couldn't open display :0`,
  and the greeter is back.
- **Apport crash reports:** cinnamon-session (SIGSEGV 06:06:47), compiz (SIGSEGV 06:07:08) and light-locker
  (SIGABRT 05:38:34, in the previous boot, during the upgrade).

The next cold boot, with nothing changed, came up normally: no segfault and no ICE or XML error (logs/02).

## Backtraces (logs/bt-*.txt; gdb on the apport cores, our dbgsym for cinnamon-session)

**cinnamon-session 6.4.2-1+unity5**, the crash that ends the session:

```
#0 _IceTransClose+44            call *0x80(%rax)        (libICE.so.6, libice6 2:1.1.1-1build1)
#1 _IceFreeConnection
#2 IceCloseConnection
#3 disconnect_ice_connection (ice_conn=0x64c31c08a400)  ../cinnamon-session/csm-xsmp-server.c:103
#4 auth_iochannel_watch (... ice_conn=0x64c31c08a400)   ../cinnamon-session/csm-xsmp-server.c:156
#5-#7 glib main loop
#8 csm_main ()                                          ../cinnamon-session/main.c:72
#9 main                                                 ../cinnamon-session/main.c:287
```

Frame #4 is the `IceProcessMessagesIOError` branch of `auth_iochannel_watch`. The server closes a connection whose
transport is no longer valid: the call goes through the transport's Close pointer.

**compiz 1:0.9.14.2+25.10.20250930-0ubuntu3+unity2**, without symbols (no dbgsym in the archive):
- SIGSEGV in `MoveScreen::MoveScreen(CompScreen*)+1287` (libmove.so);
- from `PluginClassHandler<MoveScreen,…>::get` → `initScreen` → `CompManager::initPlugin` → `CompPlugin::push` →
  `PluginManager::updatePlugins` → `PrivateScreen::processEvents`.

Its analysis belongs with compiz (UNITY-20261013-004, agent A).

**light-locker 1.8.0-3ubuntu4+unity3:** SIGABRT at 05:38:34, during the in-place upgrade. Its binaries and a dozen
libraries were replaced afterwards (gdb: build-id mismatch), so no frames can be resolved. It is recorded as a fact,
with no task; a task follows only if it shows up outside an upgrade.

## Analysis (2026-10-13)

- **Our patches:** none of +unity1 … +unity5 touches the code in the trace. They change `csm-manager.c`,
  `csm-system.c`, `csm-systemd.c`, `meson.build` and the D-Bus interface XML. The XSMP server and client code is
  upstream 6.4.2.
- **Upstream:** cinnamon-session master `c038bb4` (2026-10-11) has `csm-xsmp-server.c` unchanged since 6.4.2. No
  upstream fix is known.
- **The cause:** a code reading of cinnamon-session and libICE 1.1.1 is in progress. libice6 2:1.1.1-1build1 carries
  no source patches.
- **Reproduction:** none. A reproduction with a test client is not part of this task.

## Fix: 6.4.2-1+unity6 (2026-10-13)

`Fix-connection-lifetime-in-the-XSMP-server.patch`, the last patch in the series. Each ICE connection of the XSMP
server is closed once, by its owner: the authentication watch or its protocol timeout until the XSMP client is set up,
the client after that. The ICE error handler only logs. No behaviour change for normal clients. The earlier patches
are unchanged, and `debian/control` is unchanged.

**Build:** sbuild (chroot 20261008T083223Z), successful in 30 s, `dh_auto_test` ran (build/). The orig tarball is
the +unity5 one.

## Target check (target2, two cold sessions, logs/03-06)

The setup was Clean-2 → live (Release Date 2026-10-13 01:41:51 UTC), then this build with `dpkg -i`; `dpkg -V` is
clean. Ordinary use only, with passive bpftrace uprobes on `IceAcceptConnection`, `IceCloseConnection` and
`_IceFreeConnection` in cinnamon-session (`observe.sh`, `summary.py`):

- an xterm that exits normally;
- an xterm killed with SIGKILL;
- then a logout.

**Result,** in both sessions:
- every connection lifetime has exactly one close followed by one free (4 of 4);
- cinnamon-session survives the SIGKILL and ends cleanly at logout;
- no crash report, segfault or critical.

Session 2 has step timestamps; session 1 was recorded with an earlier `observe.sh` without them. target2 was
restored to Clean-2 afterwards and confirmed inside.

**Not run:** restart, an explicit Save-Yourself, and the UNITY-20261012-003 regression set.

## Verification

Independent Verifier, 2026-10-13: **PASS**, REVIEWED. The Verifier checked the diff against the approved design, the
build against its manifest, and the target records (it ran `summary.py` itself). It found no blocking issue.

Known gaps: UNITY-20261013-009, -010 and -011.

## Patch in the upstream form (2026-10-13)

The patch now carries the same diff as the upstream commit. Comments that annotated existing code are removed,
and the existing declarations keep their alignment. Packaging commit `7904214`, on `1d3f2bc`; the code is
unchanged (comments stripped, the two versions of the file are identical; Verifier PASS).

Rebuilt (build/, `source_commit` 7904214) and compared with the build of `1d3f2bc`:
- file lists are the same;
- every non-ELF file is identical;
- cinnamon-session-check-accelerated and its helper are identical.

In cinnamon-session-binary all allocated sections are identical except `.text`, where three immediates differ by
6: the line numbers that `g_assert_not_reached ()` and `G_OBJECT_WARN_INVALID_PROPERTY_ID` (two places) pass in
csm-xsmp-server.c, 6 lines earlier now that the comments above them are shorter. No instruction or code path
differs.

### Target check of the 7904214 build (target2, two cold sessions, logs/07-09)

The check above, repeated on the build that is published. The setup was Clean-2 → live (Release Date
2026-10-13 10:44:09 UTC, full-upgrade, nothing left to upgrade). Then this build with `dpkg -i`, after its sha256
was checked against build/ (cinnamon-session `e528f0b5…`, -common `d7967587…`); `dpkg -V` is clean.
`observe.sh` and `summary.py` were the same as before, in sessions s3 and s4.

**Result,** in both sessions:
- every connection lifetime has exactly one close followed by one free (4 of 4);
- cinnamon-session survives the SIGKILL of an xterm and ends at logout;
- no crash report, no segfault line, no cinnamon-session critical.
