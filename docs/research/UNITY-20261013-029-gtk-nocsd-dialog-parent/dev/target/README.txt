gtk-nocsd 4.8-1+unity5 (build/, the final commit) on target-desktop: restored from Published-stack-2026-10-08,
full-upgraded from the live repository on 2026-10-14 (u-s-d +unity16, cinnamon-session +unity7, light-locker +unity4,
unity +unity13, unity-gtk4-menu 0.13, gtk-nocsd +unity4); then libgtk-nocsd0 4.8-1+unity5 and epiphany-browser
49.2-3ubuntu1 installed, Firefox made the default http handler (~/.config/mimeapps.list) so that epiphany asks to
become the default browser; cold boot. Times EEST on the target, 2026-10-17.

01-sigterm-with-question.txt (029t.sh): epiphany started with compiz's environment (the session's LD_PRELOAD,
libunity-gtk4-menu and libgtk-nocsd), SIGTERM after 15 s: 5/5 exit 143, libgtk-nocsd mapped in each, no ERROR or
CRITICAL lines, no crash file. With 4.8-1+unity4 the same start aborted (exit 134, assertion (!ephy_shell)) on this
machine and on target2 (B, 9/9).
02-question-open-before-sigterm.png (029s.sh): the "Set as Default Browser?" question open in its own window at the
time of the SIGTERM; epiphany exited, no crash file.
03-dialogs-still-work.txt (029p.sh): the question answered with "Ask Again Later" (ask-for-default stays true, as
that answer leaves it); Preferences opened through the app action, closed with Escape and opened again, 3 times, a
window each time and none after Escape, epiphany alive; SIGTERM with nothing open: exit 143, no criticals, no crash file.
An earlier run of 029t.sh, before the session had started (no compiz), aborted on an unrelated fatal libportal
critical without a display; it is not counted, and its crash file was removed.

Not shown per run / not tested on target:
- In 01 the "windows:" field is empty in all 5 runs (the xdotool lookup by pid returned nothing); that the question
  was open in those runs follows from the setup (Firefox the default handler, ask-for-default true) and is shown in
  the separate 029s run (02, screenshot). The before-fix aborts on target-desktop are from 2026-10-13 (4.8-1+unity4).
- Closing the main window through the window manager while the question is open: a close request sent with wmctrl
  on 2026-10-13 closed the modal question instead of the main window, with and without the change; the main-window
  path (gtk_window_close on the parent) is covered by the build-time test T1b.
- Preferences re-opened in a session with two windows: not tested (03 is one window).
