# Test VMs: clock behind after a long-running session (UNITY-20260929-022)

Owner: agent B (target-desktop-2). This is an operation record: nothing on the machines was changed (C's decision,
2026-10-13).

```yaml
task: UNITY-20260929-022
title: target VMs time sync - target-desktop-2 clock ~4.5 min behind (NTP not synchronized); apt refused our InRelease as not yet valid right after a publication
status: closed: cause found, mitigation in the procedure, no base-image change
```

## Measured (2026-10-13 22:08Z, target2 cold-booted from Clean-2; `time.txt`)

- `timedatectl`: System clock synchronized yes, NTP service active. The guest's UTC equals the builder's to the
  second.
- chrony 4.8 is the NTP client, with Ubuntu's NTS pools. systemd-timesyncd is not used.
- At this boot chrony found the clock 3.49 s wrong, and stepped it 30 s after it started.
- `/etc/chrony/chrony.conf` has `makestep 1 3`: chrony steps the clock only during its first three updates, and
  after that only slews it.
- VirtualBox's guest time sync is not running: the vboxguest module is loaded, `vboxadd-service` is inactive.

## Cause

A cold boot sets the clock right: the RTC comes from the host, and chrony steps any error within its first updates.
In a session that runs long, a host sleep or a VM pause leaves the guest clock behind. chrony then only slews it,
which corrects minutes slowly, and nothing else steps it. That fits the 2026-09-29 case: the clock was about 4.5 min
behind in a long-running session, and apt refused a just-published InRelease as "not yet valid".

## Mitigation (no change to the base image)

- Our procedure cold-cycles a target before every target test (poweroff, start), which steps the clock.
- In a long-running session that has drifted: `sudo chronyc makestep` before apt.
- An option, recorded but not applied: a drop-in `/etc/chrony/conf.d/90-unity-distro-vm.conf` with `makestep 1 -1`
  (step whenever the error exceeds 1 s). It needs a refresh of Clean-2 and of target-desktop's clean snapshot.
  Applying it is May's or C's decision.
