# UNITY-20260927-021 - target verification

Date: 2026-09-29 (16:26Z-17:30Z). Machine: VM `oem-test`. Repository: live
`./resolute` = snapshot `unity-resolute-20260927-021-r2`, served at
`http://192.168.56.10:8080/` and signed with key `29A893E0...7BF3F77FC27B152C`.

Result: **PASS**. The +unity2 fix reaches an OEM install through the normal
path: installer medium, our repository, OEM install. On the first boot of the
end user's setup, Calamares is on top in 2 of 2 cold boots.

## Main limit: apt does not fix an OEM system that is already installed

The OEM environment's `/usr/bin/basicwallpaper` does not belong to any
package on the installed system. Evidence: logs/14.

- `shellprocess@oemprep` runs `calamares-oemprep.sh`. It unpacks
  `/etc/calamares/oemconfig.tar.gz` from the installer medium into the target
  (`tar xzf ... -C $ROOT --strip-components=2`).
- The installed OEM system (snapshot `OEM-ready`) has no `calamares-settings-*`
  package at all. Its apt sources list only the Ubuntu archive.
- `dpkg -S basicwallpaper` finds no owner.

So `apt upgrade` on an OEM machine that is already prepared cannot deliver
the fix. A user of the official ISO gets it only by running the OEM install
from a medium that carries `calamares-settings-ubuntu-unity 1:26.04.12+unity2`.

The verified path is: live session, then our repository, then OEM install.
The plan's original step (upgrade inside the installed disk) was replaced for
this reason, with C's agreement.

## Steps and results

1. **Before** (logs/14): `oem-test` was restored to `OEM-ready` and booted
   from `ubuntu-unity-26.04-desktop-amd64.iso`.
   - Installed disk: only `calamares`/`calamares-data` 3.3.14-0ubuntu25, no
     calamares-settings package. `/usr/bin/basicwallpaper` is `cdd40699...`
     (the archive build, logs/01), unowned.
   - Live medium: calamares-settings-ubuntu-{unity,common,common-data}
     1:26.04.12 from the archive. Its `oemconfig.tar.gz` (`6baf2926...`) holds
     basicwallpaper `cdd40699...`.
2. **Our repository in the live session** (logs/15):
   - Our key and a deb822 source (`resolute main`) were added.
   - `apt-cache policy` for all three packages shows candidate
     `1:26.04.12+unity2` from `http://192.168.56.10:8080 resolute/main`, above
     `+unity1` (ours) and the archive's `1:26.04.12` (installed).
   - `apt-get install` of the three packages upgraded them to +unity2. All
     three have status `ii`.
   - `dpkg -V` is clean.
   - The changelog has 95 entries, top `1:26.04.12+unity2`.
   - The new `/etc/calamares/oemconfig.tar.gz` (`90992b17...`) holds
     basicwallpaper `077f7c36...`, the r2 build.
3. **OEM install** (logs/16, full Calamares log in logs/16a):
   - `calamares-launch-oem`, batch `ubuntuunity-2604-2026-09-29`, erase disk,
     normal installation, no updates during install.
   - `calamares-oemprep.sh` ran; completion succeeded.
   - Checked from the live session on the target: `/usr/bin/basicwallpaper` is
     `077f7c36...`. The OEM session and finish files are present. The `oem`
     uid is 60999 (from `fix-oem-uid`). The only apt source is the Ubuntu
     archive.
4. **OEM preparation** (logs/17):
   - First boot into Unity as `oem`, then `calamares-finish-oem`.
   - LightDM autologin session became `ubuntu-unity-oem-environment`.
   - The ISO was ejected before Enter at "remove the installation medium".
   - Snapshot `OEM-ready-unity2` was taken powered off, with no ISO attached.
5. **Cold first boots** from `OEM-ready-unity2`, no input sent (coldrun.sh
   and coldwatch.sh from `docs/research/calamares-oem/`):

   | Run | xfwm4 | wallpaper viewable | Calamares viewable | focus | wallpaper state | Result |
   |---|---|---|---|---|---|---|
   | cold-unity2-1 (logs/18) | 60.8 s | 70.3 s | 96.8 s | xfwm4's own window | `DESKTOP`, `BELOW` | Calamares on top |
   | cold-unity2-2 (logs/19) | 65.4 s | 72.7 s | 89.2 s | xfwm4's own window | `DESKTOP`, `BELOW` | Calamares on top |

   - The wallpaper maps first in both runs and never takes focus.
   - Compare the archive build on `OEM-ready` (README of
     `docs/research/calamares-oem`, cold-archive-3): there the wallpaper is
     `NORMAL` + `FULLSCREEN`, takes focus, and stays above Calamares.
   - The rollback between the runs was confirmed inside the guest: marker
     `~/.dirty-cold-unity2-1`, written at the end of run 1, is absent in
     run 2.

## Instrumentation (not part of the product)

Added only to observe the machine; none of it touches basicwallpaper, the
OEM session or Calamares:

- `openssh-server` from the archive, installed from the live session through
  a chroot;
- the builder's ssh key in `/home/oem/.ssh`;
- `xdotool` from the archive, installed as `oem` during OEM preparation;
- the live session also had `openssh-server`/`xdotool` (vm-bootstrap).

`OEM-ready` was instrumented the same way, except that no xdotool was
recorded for it.

## Other limits

- kubuntu/lubuntu were not checked on machines (May's decision,
  UNITY-20260927-044). The patched basicwallpaper in
  `calamares-settings-kubuntu`/`-lubuntu` +unity2 is unmeasured.
- Known item, not investigated: Calamares is on top, but it has no keyboard
  focus until clicked. Focus stays on xfwm4's own window, the same as
  cold-fixed-1/2 with +unity1.
- The end user's setup was not run through after these boots. The full
  setup was already run with +unity1, and basicwallpaper is the only binary
  change since.
- Only the Ubuntu Unity flavour, BIOS/MBR, 4 GB/2 CPU VM (target2 profile).
