# cinnamon-session: session manager crash when an XSMP client connection fails during setup (UNITY-20261013-007)

Owner: agent B (target2).

```yaml
task: UNITY-20261013-007
package: cinnamon-session (6.4.2-1+unity5 installed from live)
target_series: resolute
status: INVESTIGATING
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
