#!/bin/bash
# probe-sudoers.sh LABEL - on oem-test as user oem: identity of the boot, the
# sudoers files as installed, which sudo implementation runs, and how it
# reacts. Read-only apart from sudo's own logging.
echo "== $1"
echo "boot_id: $(cat /proc/sys/kernel/random/boot_id) uptime: $(cut -d' ' -f1 /proc/uptime)s user: $(id -un)"
stat -c '%A %a %U:%G %n' /etc/sudoers /etc/sudoers.orig /etc/sudoers.d 2>&1
echo "sudo: $(readlink -f "$(command -v sudo)") ($(dpkg -S "$(readlink -f "$(command -v sudo)")" 2>/dev/null | cut -d: -f1))"
sudo --version 2>&1 | head -1
update-alternatives --query sudo 2>/dev/null | grep -E '^(Value|Alternative):'
dpkg-query -W sudo sudo-rs calamares-settings-ubuntu-unity 2>&1
echo "sudo -n true: $(sudo -n true 2>&1 && echo ok) rc=$?"
echo "sudo -n -l (first lines):"; sudo -n -l 2>&1 | head -6
echo "calamares running: $(pgrep -x calamares >/dev/null && echo yes || echo no)"
echo "journal (sudo, this boot):"; journalctl -b --no-pager 2>/dev/null | grep -iE 'sudo(-rs)?\b.*(mode|permission|writable|owner|sudoers)' | tail -5
