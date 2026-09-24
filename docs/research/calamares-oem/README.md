# Wallpaper over Calamares in the OEM setup (release notes, bug 4)

The 26.04 release notes say: "the wallpaper has the tendency to appear over
the Calamares (installer) window when performing OEM installation. Use
Alt+Tab to get back to Calamares".

## Which stage

An OEM installation has two stages.

1. **The vendor's install**, from the live session: Unity and compiz, with
   `calamares-launch-oem`. The desktop is `nemo-desktop`, a proper
   `_NET_WM_WINDOW_TYPE_DESKTOP` window. In target2's installed Unity session
   (not the live one), `sudo calamares` stays on top, before and after
   Alt+Tab. Nothing points at this stage; the live session itself is checked
   on `oem-test`.
2. **The end user's first-time setup**, after the vendor runs "Finish OEM
   preparation". LightDM logs `oem` into the session
   `ubuntu-unity-oem-environment`, whose script is
   `/usr/libexec/start-ubuntu-unity-oem-env`
   (calamares-settings-ubuntu, `ubuntuunity/oem/ubuntu-unity-oem-env/`):

   ```sh
   /usr/bin/xfwm4 &
   /usr/bin/basicwallpaper /usr/share/backgrounds/ubuntu-unity/ubuntu-unity-default.png &
   sudo /usr/bin/calamares -D8
   ```

   There is no Unity here: the wallpaper is a program of its own.

## Cause

`basicwallpaper` (calamares-settings-ubuntu, `common/basicwallpaper/main.cpp`)
does:

```cpp
w->setWindowFlags(Qt::WindowStaysOnBottomHint);
w->setGeometry(screen->geometry());
w->showFullScreen();
```

The window it maps is an ordinary `NORMAL` window with
`_NET_WM_STATE_FULLSCREEN`. The stay-on-bottom hint does not survive:
`_NET_WM_STATE` has no `BELOW`. xfwm4 puts a fullscreen window that has focus
into its fullscreen layer, above every normal window. So the wallpaper covers
Calamares whenever it gets focus.

Measured on target2 in Xvfb with the unpacked `oemconfig.tar.gz`, the real
xfwm4 4.20.0, the real Calamares 3.3.14 and the session script's order
(`oemenv.sh`, `check.sh`; pixel at 700,200: `#EFEFEF` is Calamares,
`#464625` is the wallpaper):

| Case | archive 26.04.12 | fixed |
|---|---|---|
| session starts in the script's order (6 runs) | Calamares on top | Calamares on top |
| Alt+Tab once | **wallpaper on top** | Calamares on top |
| Alt+Tab again | Calamares on top | Calamares on top |
| wallpaper maps 15 s after Calamares | **wallpaper on top**, it has focus | Calamares on top |
| Calamares' About dialog opened and closed | Calamares keeps focus | - |

On target2 Calamares always mapped after the wallpaper (6 of 6 starts), so
the startup case never fired by itself there. In the builder's `b-dev` chroot
(same xfwm4, Calamares and Xvfb, installed there with our package) it did:
the archive's wallpaper mapped after Calamares at a plain session start and
covered it. So it is a race, and which process wins depends on the machine;
whichever maps last gets focus. Alt+Tab moves focus both ways, which is why
the release notes' workaround works.

The package itself, installed in the chroot (`check.sh`, same pixel test):

| Case | archive binary | `1:26.04.12+unity1` |
|---|---|---|
| session start | **wallpaper on top** | Calamares on top |
| Alt+Tab, Alt+Tab | Calamares, then **wallpaper** | Calamares, Calamares |
| wallpaper maps 15 s late | **wallpaper on top** | Calamares on top |

## Fix

In `basicwallpaper`, on X11 only, map a desktop window that never takes focus
instead of a fullscreen one:

```cpp
w->setAttribute(Qt::WA_X11NetWmWindowTypeDesktop);
w->setWindowFlags(Qt::Window | Qt::FramelessWindowHint
                  | Qt::WindowStaysOnBottomHint
                  | Qt::WindowDoesNotAcceptFocus);
```

xfwm4 then reports it as `DESKTOP` with `STICKY, SKIP_PAGER, SKIP_TASKBAR,
BELOW`, keeps it below everything and leaves it out of Alt+Tab. It still
covers the screen with the image. Kubuntu runs the same binary natively under
kwin_wayland (`kubuntu-oem-env-shim`), where X11 window types mean nothing, so
the Wayland path keeps the old fullscreen code.

Packaged as calamares-settings-ubuntu `1:26.04.12+unity1`: commit `b6b546b`
on branch `unity/resolute` of `packages/calamares-settings-ubuntu` (cloned
from Launchpad `~ubuntu-qt-code/+git/calamares-settings-ubuntu`; no remote of
ours, so the change is also here as
`0001-basicwallpaper-desktop-window-on-X11-so-it-cannot-co.patch`), on top
of `c699701`, which is byte for byte the archive's 26.04.12. In aptly:
`-ubuntu-unity`, `-common`, `-common-data` (the Unity package needs the exact
`-common` version); the Kubuntu and Lubuntu packages are built but not
published. The 26.10 branch
(`ubuntu/stonking`) has not touched basicwallpaper since, so the bug is still
there upstream.

The binary ships inside `/etc/calamares/oemconfig.tar.gz` of
`calamares-settings-ubuntu-unity`. The fix reaches a machine only if the
package is in the image the vendor installs from, so it matters for our ISO,
not for an installed system.

## Seen along the way, not fixed

- `Makefile` for Ubuntu Unity does `chmod 400 kubuntu/oemconfig/etc/sudoers.oem`,
  Kubuntu's copy, instead of `ubuntuunity/...` (a copy-paste slip). The
  Ubuntu Unity `sudoers.oem` ships as 0644 (seen in the archive's
  `oemconfig.tar.gz`) and becomes `/etc/sudoers` for the setup stage.
  Whether sudo complains about 0644 there is to be seen on `oem-test`.

## Still to check on a real installation

The VM `oem-test` (host session, waiting for May) runs both stages from the
official ISO, then the same with our package: `vm-bootstrap.sh` gives ssh
access to the live session and to the `oem` user.
