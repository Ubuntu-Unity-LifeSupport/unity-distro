# indicator-bluetooth and indicator-printers: no systemd user unit in 26.04

Found by the stack-health sweep (`docs/STACK-HEALTH.md`, section B).

## What is wrong

The resolute packages carry only the old Upstart job and override, not
`/usr/lib/systemd/user/<name>.service` (checked in the archive's .debs:
indicator-bluetooth 0.0.6+17.10.20170605-0ubuntu7, indicator-printers
0.1.7+17.10.20171101-0ubuntu8; questing's packages had the unit). Unity asks
for both units, so on target2 with the archive packages:

```
indicator-bluetooth.service   not-found inactive dead
indicator-printers.service    not-found inactive dead
```

and neither service process runs. Filed for bluetooth as
[LP: #2153375](https://bugs.launchpad.net/bugs/2153375) (2026-04, New); the
reporter saw the icon missing from gnome-panel and got it back by adding the
file by hand. Nobody has reported printers.

## Why

Both `configure.ac` ask `pkg-config --variable=systemduserunitdir systemd`.
`systemd.pc` moved to `systemd-dev`, and both packages build-depend on
`systemd` only, so the variable is empty and `data/Makefile.am` installs the
unit nowhere. The 26.04 mass rebuild (LP: #2132257) was the first build since
the move; 26.10 (`stonking`) carries the same binaries.

indicator-keyboard lost its unit the same way in 26.10's rebuild; in resolute
its binary predates the move and still has it. libindicator (indicators-pre.target)
has no resolute build yet - a rebuild would need the same check.

## Fix

`Build-Depends: systemd-dev` in place of `systemd`
(`indicator-bluetooth-systemd-dev.patch`, `indicator-printers-systemd-dev.patch`;
branches `unity/resolute` of `packages/indicator-bluetooth` and
`packages/indicator-printers`, cloned from git-ubuntu, no remote of ours).
Versions `0ubuntu7+unity1` and `0ubuntu8+unity1`, in aptly.

Source format 1.0: the source package is built from `git archive` next to the
orig tarball (dpkg-source 1.0 does not skip `.git`); its diff touches the same
files outside `debian/` as the archive's diff.

## Verified on target2

- The new .debs differ from the archive's only by the unit (and, for
  bluetooth, the `.mo` files Launchpad moves into language packs).
- After `dpkg -i` and a reboot both units are `loaded active running`, both
  service processes run, the journal shows them started.
- indicator-bluetooth answers on the bus with `bluetooth-supported: false`
  and `root-desktop visible: false`: target2 has no Bluetooth adapter
  (`/sys/class/bluetooth` absent), so hiding the icon is correct.
  indicator-printers exports `/com/canonical/indicator/printers`; it shows an
  icon only while there are print jobs.
- Not checked: the icons with a real adapter or a print job.
