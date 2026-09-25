# Five indicators rebuilt for resolute (FTBFS fixes)

Found by the stack-health sweep (`docs/STACK-HEALTH.md`, indicator rows):
indicator-datetime, -power, -session and -sound fail to build in resolute
(Canonical's test rebuild, 2026-03-20), and indicator-keyboard was never
rebuilt there. The binaries we ship are 2024 builds, or come from the
2026-01 mass rebuild. None of these packages could take a patch until it
could be built again.

Each fix is on branch `unity/resolute` of `packages/<pkg>` (git-ubuntu
clones, source format 1.0). All five are built with sbuild and in aptly.

| Package | Version | Commit | What broke / the fix |
|---|---|---|---|
| indicator-datetime | 15.10+21.04.20210304-0ubuntu6+unity1 | `7676fbe` | CMake 4: `cmake_minimum_required` 2.8.9 → 3.10 (`CMakeLists.txt`), 2.6 → 3.10 (`cmake/GdbusCodegen.cmake`). Then two tests failed, `NotificationFixture.Notification` and `.InteractiveDuration`: libnotify 0.8 sends the icon as the `image-path` hint and leaves `app_icon` empty. The tests (`tests/test-sound.cpp`, `tests/test-notification.cpp`) now read the hint when `app_icon` is `""`. The indicator itself is unchanged. 28/28 tests pass. |
| indicator-power | 12.10.6+17.10.20170829.1-0ubuntu9+unity1 | `bff6e5d` | The same CMake bumps; GCC 15 makes `-Wincompatible-pointer-types` an error: `src/service.c` casts the `g_object_ref()` result back with `G_DBUS_CONNECTION()`. |
| indicator-session | 17.3.20+21.10.20210613.1-0ubuntu5+unity1 | `47aac89` | CMake bump only. |
| indicator-sound | 12.10.2+18.10.20180612-0ubuntu7+unity1 | `338d8fd` | Cherry-picked from 26.10 (0ubuntu10, LP #2166355): CMake 3.10 and the GCC 15 casts in `src/main.c`. |
| indicator-keyboard | 0.0.0+19.10.20240924-0ubuntu1+unity1 | `ad9d0bf` | `debian/control`: add `lightdm-vala` (the vala files left `liblightdm-gobject-1-dev`; 26.10 did the same in 0ubuntu3) and `systemd` → `systemd-dev`, so configure still finds the user unit dir. |

Rule 0, where I looked: 26.10 (stonking) has fixes only for sound
(0ubuntu10) and keyboard (0ubuntu3/4). datetime, power and session are still
at the resolute versions there, so nothing exists to take. The Ayatana forks
are a separate code base and do not replace these packages. That is a
different decision.

## Verification

- sbuild in resolute: all five `Status: successful`; datetime's test suite
  runs (28/28).
- The file lists match the archive's debs, except locale files and one path:
  indicator-keyboard's autopilot module moves from `python3.12` to
  `python3.14`. Every package still carries
  `/usr/lib/systemd/user/indicator-*.service`.
- target2, installed with `dpkg -i` and rebooted into Unity:
  `systemctl --user` shows datetime, sound, power, session and keyboard
  `active (running)` (bluetooth and printers too); each exports its
  `/com/canonical/indicator/<name>/desktop` menu on D-Bus. The panel shows
  clock, sound and session; power and keyboard hide themselves on a VM with
  no battery and one layout. No new crash reports. The warnings
  in the journal (no PulseAudio D-Bus socket yet; `Etc/Utc` TZID;
  no `org.gnome.Calendar.desktop`) are not build-related, and were not
  investigated further.

## indicator-keyboard's test crash (LP #1968333), fixed in +unity2

Before 0ubuntu1+unity1 was published, this README said the crash in
`/indicator-keyboard-service/activate-character-map` was memory corruption in
the service. That was wrong. The crash is in the test's own mock `Service`
(`tests/main.vala`), and the indicator is not affected.

- **The pattern.** The mock announces a new command with
  `notify["command"] ((!) pspec);`, a detailed emission of `GObject.notify`.
- **What Vala generates.** Since Vala 0.55.1 (commit `b9df26bcf`,
  "codegen: Split out GSignalModule.emit_signal()", 2021-11-01), a signal
  with an emitter (`[HasEmitter]` on `notify` in `gobject-2.0.vapi`) is
  emitted by calling the emitter with the signal's arguments, and the detail
  is dropped. The C is `g_object_notify (self, pspec)`: a `GParamSpec*`
  where a property name is expected. GLib prints the garbage "property
  name", and the signal is not emitted. The `emitter` branch of
  `emit_signal()` in `codegen/valagsignalmodule.vala` ignores `detail_expr`.
  That branch is unchanged in 0.56.19 and in main. No Vala issue or commit
  mentions it (issues searched for g_object_notify, HasEmitter, emitter
  detail, detailed signal).
- **Why the build hid it.** `-w` in `tests/Makefile.am` hides GCC's
  incompatible-pointer diagnostic. The test then aborts on its first
  critical, so tests 3-9 never ran after jammy (Vala 0.56). In 2022
  `debian/rules` got `dh_auto_test || true` "temporarily"
  ([LP #1968333](https://bugs.launchpad.net/bugs/1968333), open, High,
  same message in its log).

Reproducer: a 20-line Vala class with the same `execute()` compiled with
valac 0.56.18 (resolute) printed the critical, and no notify arrived.
With `notify_property ("command")` Vala generates
`g_object_notify (self, "command")` and the notify arrives.

Fix (branch `unity/resolute`, commits `cb8cf96` and `1a14712`, version
`0.0.0+19.10.20240924-0ubuntu1+unity2`):

- `Service.execute()` calls `notify_property ("command")`;
- `debian/rules` drops `|| true`, so test failures fail the build again.

sbuild: all 9 tests pass with the tests fatal, the first full run since the
eoan build in 2019 (valac 0.44.3). The file list is the same as +unity1.
The service code did not change. On target2 the service restarts active and
exports its actions. The package is in aptly.

Rule 0: in 26.10 (0ubuntu4, valac 0.56.19) the test still fails, and the
build passes only because of `|| true`. `tests/main.vala` has been unchanged
since 2015. Ayatana's keyboard indicator is a C rewrite with no such tests,
indicator-keyboard is not in Debian, and the forks on gitlab carry the same
line.

Not reported anywhere: the Vala codegen bug (upstream gitlab
GNOME/vala) and our fix for LP #1968333. Both wait for May.
