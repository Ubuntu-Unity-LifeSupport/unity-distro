#!/bin/sh
# Bootstrap for agent B: ssh access into the OEM test VM (live session or oem user).
set -e
# Wait for the NAT side: it carries the default route.
n=0
until ip -4 route show default | grep -q dev; do
  n=$((n+1)); [ $n -gt 60 ] && { echo "no default route after 60 s"; exit 1; }
  sleep 1
done
nat=$(ip -4 route show default | sed -n 's/.* dev \([^ ]*\).*/\1/p' | head -n1)
sudo apt-get update -q
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y openssh-server xdotool
mkdir -p ~/.ssh && chmod 700 ~/.ssh
wget -qO- http://192.168.56.10:8088/key.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
# The host-only NIC is the one that is neither lo nor the NAT one. Give it
# 192.168.56.40 only when DHCP left it without an address.
for i in $(ls /sys/class/net); do
  [ "$i" = lo ] && continue
  [ "$i" = "$nat" ] && continue
  if ! ip -4 addr show "$i" | grep -q inet; then
    sudo ip addr add 192.168.56.40/24 dev "$i"
  fi
  sudo ip link set "$i" up
done
sudo systemctl start ssh
ip -4 -br a
echo B-BOOTSTRAP-OK
