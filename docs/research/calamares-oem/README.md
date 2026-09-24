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

## On a real OEM installation (VM `oem-test`)

The official `ubuntu-unity-26.04-desktop-amd64.iso` (SHA256 checked against
`SHA256SUMS`) in a VM with target2's profile (BIOS, VMSVGA, 4 GB, 2 CPUs),
driven over ssh with xdotool (`vm-bootstrap.sh` in the live session; for the
installed system `openssh-server` and the key were added from the live
session through a chroot before the first boot - instrumentation only).
Screens: `gnome-screenshot` in the session, pixel test as above (`probe.sh`,
`live.sh`).

1. **Vendor's stage**, live session under Unity: `calamares-launch-oem`,
   OEM batch `ubuntuunity-2604-2026-09-24`, erase disk, normal installation.
   Calamares stayed on top throughout; "completion: succeeded". The only
   crash report was light-locker's SIGABRT, known issue #5.
2. **OEM preparation**, first boot into Unity as `oem`: "Finish OEM
   preparation" switched LightDM's autologin session to
   `ubuntu-unity-oem-environment`. Snapshot `OEM-ready` taken here (host).
3. **End user's first-time setup**, archive `basicwallpaper`
   (sha256 `cdd40699dae0...`):

   | Boot | What the user sees |
   |---|---|
   | first boot after OEM preparation | **wallpaper only** - `basicwallpaper` FULLSCREEN, FOCUSED, above a maximised Calamares |
   | reboot 1, reboot 2 | Calamares |
   | Alt+Tab, Alt+Tab (running session) | **wallpaper**, then Calamares |
   | wallpaper restarted after Calamares | **wallpaper**, it has focus |

   So the release notes' bug is exactly this, and it hits the one boot that
   matters: the first one, still busy with first-boot work, lost the race.
4. **Same stage with our binary** (`1:26.04.12+unity1`, sha256
   `2cd8d1f51497...`, put where `oemconfig.tar.gz` puts it):

   | Case | What the user sees |
   |---|---|
   | Alt+Tab, Alt+Tab | Calamares, Calamares |
   | wallpaper restarted after Calamares | Calamares, which keeps focus |
   | reboots 1-3 | Calamares |
   | "Continue with Setup?" closed with Set Up Now | Calamares |

   Then the whole setup ran through: user `tester` got uid 1000, `oem` and
   the OEM files (`basicwallpaper`, the session, `sudoers`) were removed,
   "All done", Done restarted into the LightDM greeter.

Not tested: a cold first boot with our binary. It needs the binary on the
disk before that boot - an image built with our package, or `OEM-ready`
patched offline from the live ISO. The late-map case reproduces what that
boot does (the wallpaper maps after Calamares), and it passes.

Seen, not investigated: the finished system boots to `lightdm-gtk-greeter`,
not `unity-greeter` (both are on the ISO). Whether a normal, non-OEM install
does the same is not checked.
