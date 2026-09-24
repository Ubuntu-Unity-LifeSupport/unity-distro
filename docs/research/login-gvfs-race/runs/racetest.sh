#!/bin/sh
# Deterministic model of the login race: a D-Bus activated unit, PartOf an
# INACTIVE target, still starting when the target is stopped.
. ~/envt.sh
mkdir -p ~/.config/systemd/user ~/.local/share/dbus-1/services
cat > ~/.config/systemd/user/race-test.target <<U
[Unit]
Description=race test target (never started)
U
cat > ~/.config/systemd/user/race-slow.service <<U
[Unit]
Description=race test service, slow to start
PartOf=race-test.target
[Service]
Type=dbus
BusName=org.example.RaceSlow
ExecStartPre=/bin/sleep 2
ExecStart=/usr/bin/python3 -c "from gi.repository import Gio, GLib; Gio.bus_own_name(Gio.BusType.SESSION, 'org.example.RaceSlow', 0, None, None, None); GLib.MainLoop().run()"
U
cat > ~/.local/share/dbus-1/services/org.example.RaceSlow.service <<U
[D-BUS Service]
Name=org.example.RaceSlow
Exec=/bin/false
SystemdService=race-slow.service
U
systemctl --user daemon-reload; sleep 1
call() { t0=$(date +%s.%N); gdbus call --session --timeout 150 --dest org.example.RaceSlow --object-path / --method org.freedesktop.DBus.Peer.Ping >/dev/null 2>&1; r=$?; echo "  call rc=$r after $(echo "$(date +%s.%N) - $t0" | bc | cut -c1-5) s"; }
echo "A: activation alone"; systemctl --user stop race-slow.service; call
echo "B: stop the inactive target 0.5 s into the activation (what run-systemd-session does)"
systemctl --user stop race-slow.service; sleep 1
T=$(date +%T); call & sleep 0.5; echo "  target active? $(systemctl --user is-active race-test.target)"; systemctl --user stop race-test.target; wait
journalctl --user --since $T --no-pager -o short-precise | grep -E "race-slow|RaceSlow" | cut -c17-160
echo "C: same, but stop only if the target is active"
systemctl --user stop race-slow.service; sleep 1
call & sleep 0.5; if systemctl --user -q is-active race-test.target; then systemctl --user stop race-test.target; else echo "  target inactive, not stopped"; fi; wait
systemctl --user stop race-slow.service
rm ~/.config/systemd/user/race-test.target ~/.config/systemd/user/race-slow.service ~/.local/share/dbus-1/services/org.example.RaceSlow.service; systemctl --user daemon-reload
