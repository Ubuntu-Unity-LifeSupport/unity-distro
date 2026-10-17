light-locker 1.8.0-3ubuntu4+unity5 (build-ll/), before the unity change. Times EEST on the target.

red-green.txt: test-lock-after.c built against a helper that returns the configured value (the behaviour without
d/p/0008) fails at the first Unity case (5 != 0); against gs-lock-after.c all 4 cases pass. In the sbuild
build make check runs test-lock-after and test-listener-inhibit: 2/2 PASS (build-ll/ log).

target-desktop, live stack (unity +unity13) plus light-locker +unity5 from build-ll/, cold boot:
- target-ll5-owner.txt: light-locker owns org.gnome.ScreenSaver, compiz queued behind it.
- target-ll5-with-unity13.txt: saved lock-after-screensaver is 5. SetActive(true) on org.gnome.ScreenSaver:
  GetActive true for 12 s, VT 7, LockedHint no (no lock armed); mouse input: GetActive false. Ctrl+Alt+L:
  greeter on VT 8, LockedHint yes.

Side observations from this session:
- A LightDM restart while the user's bus and the old compiz were still alive (not a cold login) left
  light-locker of the new session exiting with "screensaver already running" (journal 00:51:20); after the cold
  boot light-locker owned the name as above.
- /var/crash/_usr_bin_light-locker.1000.crash (00:49:47, SIGABRT) is from a light-locker started by hand from
  ssh with an empty XDG_SESSION_PATH (libdbus "_dbus_check_is_valid_path" assertion); not a session start.
