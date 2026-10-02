# UNITY-20260927-041 - target verification

Date: 2026-09-29, 18:2xZ-20:35Z. Machine: VM `oem-test`.

Repository:

- `./resolute` became snapshot `unity-resolute-20260927-041` at 18:15:21Z;
- at ~18:4xZ it became UNITY-20260927-040's `unity-resolute-20260927-040`,
  which carries the same 7 records;
- served at `http://192.168.56.10:8080/`, signed with key
  `29A893E0...7BF3F77FC27B152C`.

Result: **PASS**. On the published path (installer medium, our repository,
OEM install), `/etc/sudoers` in OEM mode is 0440 root:root and passes
`visudo -c`. Calamares is still on top at the end user's first boot.

## Steps and results

1. **Live ISO session with our repository** (logs/11).
   - `apt-cache policy` for -ubuntu-unity, -common and -common-data shows
     candidate `1:26.04.12+unity3` from `192.168.56.10:8080 resolute/main`.
   - After the install all three are `ii`, `dpkg -V` is clean, and the
     changelog has 96 entries, +unity3 on top.
   - In `oemconfig.tar.gz` (`2bf47026...`), `sudoers.oem` is
     `-r--r----- root/root` (d0a025d4...), and `basicwallpaper` is
     ca88f9c3...
   - The only apt operations against our repository ran in this step,
     before UNITY-20260927-040 switched `./resolute`.
2. **Fresh Calamares OEM install** from that session (logs/12, full log in
   logs/12a): batch `ubuntuunity-2604-2026-09-29`, erase disk, normal
   installation. Completion: succeeded. On the target:
   - `/etc/sudoers` is 440 root:root, 1762 bytes, d0a025d4 (the shipped
     sudoers.oem);
   - `/etc/sudoers.orig` is 440;
   - `visudo -c` of the active sudo-rs and of sudo.ws both report
     "parsed OK", rc 0;
   - `basicwallpaper` is ca88f9c3; the only apt source is the Ubuntu
     archive.
3. **snap-seed-glue-emb** of -common +unity3, statically built with snapd
   2.76.3 (logs/13).
   - The OEM install runs it only for selected third-party snaps, and none
     was selected.
   - So it was run in the live session on a copy of `/var/lib/snapd/seed`,
     as `pkgselect_snap_context.conf` runs it for Thunderbird.
   - Result: rc 0; `thunderbird_1274.snap` and its `seed.yaml` entry were
     added.
4. **Vendor-stage OEM session**, the first boot as `oem` (logs/14).
   - `/etc/sudoers` is 440, `sudo -n true` works, and `sudo visudo -c` gives
     "parsed OK", rc 0.
   - `calamares-finish-oem` then set the LightDM autologin session to
     `ubuntu-unity-oem-environment`.
5. **Snapshot `OEM-ready-unity3`**, taken powered off with no ISO attached.
   The first attempt at 18:50Z failed with E_ACCESSDENIED and left the
   machine wedged in VBoxSVC. The snapshot was taken once VBoxSVC recovered.
6. **Cold first boot** from that state with no input (logs/15), checked from
   inside the guest:
   - the disk is this install: `/etc/sudoers` 440 root:root, basicwallpaper
     ca88f9c3, session `ubuntu-unity-oem-environment`;
   - xfwm4 at 56.6 s, wallpaper viewable at 62.7 s, Calamares at 74.4 s;
   - the wallpaper is `DESKTOP`, `BELOW`, and never focused;
   - Calamares is on top. For `oem`, `/etc/sudoers` is not readable
     (0440 root:root).

## Instrumentation (not part of the product)

- `openssh-server` and `xdotool` from the archive, installed from the live
  session through a chroot;
- the builder's ssh key in `/home/oem/.ssh`;
- the live session itself had `openssh-server` and `xdotool`
  (vm-bootstrap).

## Limits

- The end user's setup was not run through; the fix touches only the OEM
  mode's `/etc/sudoers`.
  After setup, `calamares-oemfinish.sh` restores `/etc/sudoers.orig` (0440).
  This is from reading the code, not measured.
- Kubuntu and Lubuntu ship `sudoers.oem` 0400, which `visudo -c` also
  rejects. That is out of scope and not checked on machines.
- One cold boot, as planned. The wallpaper behaviour is the one
  UNITY-20260927-021 already verified: 2 of 2 with +unity2, and basicwallpaper's
  source is unchanged.
- Only the Ubuntu Unity flavour, on a BIOS/MBR VM with 4 GB and 2 CPUs.
