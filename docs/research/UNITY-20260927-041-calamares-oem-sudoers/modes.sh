#!/bin/bash
# modes.sh - on oem-test as oem (NOPASSWD in OEM mode): how sudo-rs and
# classic sudo (sudo.ws) and their visudo -c react to /etc/sudoers modes.
# Changes the mode of /etc/sudoers; the VM is restored from its snapshot after.
ws=/usr/bin/sudo.ws; rs=/usr/lib/cargo/bin/sudo
vws=$(command -v visudo.ws || ls /usr/sbin/visudo.ws 2>/dev/null); vrs=$(ls /usr/lib/cargo/bin/visudo 2>/dev/null)
for m in 0644 0440 0400; do
  sudo -n chmod $m /etc/sudoers
  echo "-- mode $(stat -c '%a %U:%G' /etc/sudoers)"
  echo "sudo-rs true:  $($rs -n true 2>&1 && echo ok)"
  echo "sudo.ws true:  $($ws -n true 2>&1 && echo ok)"
  echo "visudo(rs) -c: $($rs -n $vrs -c 2>&1 | tr '\n' ' ') rc=$?"
  echo "visudo(ws) -c: $($rs -n $vws -c 2>&1 | tr '\n' ' ') rc=$?"
done
sudo -n chmod 0644 /etc/sudoers; echo "restored: $(stat -c '%a' /etc/sudoers)"
