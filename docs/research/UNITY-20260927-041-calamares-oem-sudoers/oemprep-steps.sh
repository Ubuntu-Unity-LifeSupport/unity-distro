#!/bin/bash
# oemprep-steps.sh TARBALL - on oem-test as oem: repeat calamares-oemprep.sh's
# sudoers steps (tar xvzf ... --strip-components=2 as root into a root dir,
# then mv etc/sudoers.oem etc/sudoers) in a scratch root, and check the result
# with visudo -c -f of sudo-rs and of sudo.ws.
t=$1; root=$(mktemp -d /tmp/oemroot.XXXX)
sudo -n tar xzf "$t" -C "$root" --strip-components=2
sudo -n mv "$root/etc/sudoers.oem" "$root/etc/sudoers"
echo "== $t -> $(stat -c '%A %a %U:%G' "$root/etc/sudoers")"
echo "visudo(rs) -c -f: $(sudo -n /usr/lib/cargo/bin/visudo -c -f "$root/etc/sudoers" 2>&1 | tr '\n' ' ')"
echo "visudo(ws) -c -f: $(sudo -n /usr/sbin/visudo.ws -c -f "$root/etc/sudoers" 2>&1 | tr '\n' ' ')"
sudo -n rm -rf "${root:?}"
