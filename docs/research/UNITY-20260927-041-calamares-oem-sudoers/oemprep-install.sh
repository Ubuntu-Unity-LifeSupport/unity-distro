#!/bin/bash
# oemprep-install.sh TARBALL - on oem-test as oem (OEM mode, NOPASSWD): extract
# the oemconfig as calamares-oemprep.sh does and move its sudoers.oem to
# /etc/sudoers (mv keeps the extracted mode), then check what sudo sees.
# Destructive for the VM's /etc/sudoers; restore the snapshot afterwards.
t=$1; root=$(mktemp -d /tmp/oemroot.XXXX)
sudo -n tar xzf "$t" -C "$root" --strip-components=2
sudo -n mv "$root/etc/sudoers.oem" /etc/sudoers
echo "== $t: /etc/sudoers $(stat -c '%A %a %U:%G' /etc/sudoers)"
echo "sudo-rs -n true: $(/usr/lib/cargo/bin/sudo -n true 2>&1 && echo ok)"
echo "sudo.ws -n true: $(/usr/bin/sudo.ws -n true 2>&1 && echo ok)"
echo "visudo(rs) -c: $(sudo -n /usr/lib/cargo/bin/visudo -c 2>&1 | tr '\n' ' ')"
echo "visudo(ws) -c: $(sudo -n /usr/sbin/visudo.ws -c 2>&1 | tr '\n' ' ')"
sudo -n rm -rf "${root:?}"
