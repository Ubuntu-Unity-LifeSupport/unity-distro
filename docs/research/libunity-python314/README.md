# libunity: the Python scope runner on Python 3.14

Agent B, 2026-09-26, on `target2` (Unity session, Python 3.14.4). target2
was rolled back to `Clean-2` afterwards.

## Rule 0

The runner still imports `imp` in each of these:
- Debian salsa `-7` (2026-04-25) and `-8` (2026-05-06). Their patches are
  the Filter setter and `debian.patch`; there is no `imp` change.
- 26.10, which has `-8`.
- The open Debian bugs.

## Cause and reproduction

`/usr/share/unity-scopes/scope-runner-dbus.py` (package
`unity-scopes-runner`) runs every Python scope. It is started through
D-Bus activation by the scope's `.service` file. Its line 19 is
`import imp`, a module removed in Python 3.12.

With `unity-scope-calculator` (archive, `ModuleType=python3`), running the
scope's `Exec` line gives
`ModuleNotFoundError: No module named 'imp'`, and apport files a crash.

In the Dash, `calc: 12*7` (the scope's keyword) gives "no results"
(`dash-stock.png`), and no runner process is left.

## Fix: `libunity 7.1.4+19.04.20190319-6.1ubuntu1+unity1`

In `packages/libunity`, branch `unity/resolute`, commit `78c98ec` (a
git-ubuntu clone, no remote of ours), the quilt patch
`python-3.12-no-imp.patch`:
- replaces `imp.load_source()` with `importlib`;
- passes a `SourceFileLoader` explicitly, so that a file with any
  extension still loads, as with `imp`.

The build in a clean `sbuild -d resolute` passes the package's 4 Python
tests. They do not cover the runner.

**On target2 with `+unity1`:**
- The runner takes `com.canonical.Unity.Scope.Info.Calculator` on the
  bus.
- In the Dash, `calc: 12*7` shows "Info → 84" (`dash-unity1.png`).
- What remains are PyGI deprecation warnings (`GLib.unix_signal_add_full`,
  `UnityExtras` without `require_version`). They are warnings, not
  errors.

`+unity1` is in aptly.

## Found on the way

- `unity-scope-calculator` and `unity-scope-manpages` both ship
  `/usr/lib/python3/dist-packages/__init__.py`, so they cannot be
  installed together: dpkg refuses the second one. These are archive
  packages, not ours.
- On the fresh boot of Clean-2, `light-locker` crashed with SIGABRT
  (`/var/crash/_usr_bin_light-locker.1000.crash`, 15:45). Not
  investigated here.

## Other Python warnings from STACK-HEALTH (listed, not changed)

| file | lines | package | owner |
|---|---|---|---|
| `/usr/bin/unity` | 249, 251, 253, 259: `"\ "` invalid escape | unity | agent A |
| `/usr/share/apport/package-hooks/source_unity-settings-daemon.py` | 13: `"\w"` | unity-settings-daemon | agent A |
| `/usr/share/apport/package-hooks/source_unity-control-center.py` | 13: `"\w"` | unity-control-center | nobody: no changes of ours, not in either status |

`unity-uwidgets` (`settings/wallpaper.py` imports `requests`, which is
not a dependency) is a binary package of the `unity` source, version
`7.7.1+26.04.20260306-0ubuntu3+unityN`, so it is agent A's.
