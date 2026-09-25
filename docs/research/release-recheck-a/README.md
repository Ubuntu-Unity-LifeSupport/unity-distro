# Rule 0, last step: release re-check of agent A's fixes (2026-09-25)

Host request 2026-09-25 02:58Z: for every fix we carry, has a newer release
already fixed it, and if so, what does carrying that version cost - measured
by a build in a clean 26.04 chroot. Decision: `docs/DECISIONS.md`, same date.

## Measurement builds

`sbuild -d resolute --no-run-lintian`, default chroot (resolute archive only,
not our aptly), in `~/work/a/relcheck/out-*/`. The `du failed` lines at the end
of every log are the usual sbuild-unshare noise, not a failure.

| Source | From | Result |
|---|---|---|
| cinnamon-session 6.6.4-1 | stonking / Debian sid | **dependency failure**: `libcinnamon-desktop-dev (>= 6.6)`, resolute has cinnamon-desktop 6.4.2-1 |
| cinnamon-session 6.6.4-1+relaxtest1 | same, `>= 6.6` relaxed to `>= 6.4` in debian/control (build-dep and `cinnamon-desktop-data`) | **successful**, 46 s. Upstream `meson.build` asks for `cinnamon-desktop >= 6.0.0`; the 6.6 bound is Debian's "Bump breaks and deps to 6.6" (6.6.3-1), not a code need. The code uses only `gnome_idle_monitor_*` and the schemas 6.4.2 already uses |
| unity-settings-daemon 26.10.1ubuntu.build1 | stonking | successful, 270 s |
| xorg-server 2:21.1.24-1ubuntu1 | stonking-proposed | successful, 363 s; debian/control unchanged from resolute's 21.1.22-1ubuntu1.2 |
| lightdm 1.33.1-3 | Debian sid | successful, 111 s (new build-deps `dh-sequence-installsysusers`, `qt6-base-dev` resolve) |

## What each newer version contains of ours

Found by subagents comparing code (not commit messages); scratch clones were in
`/tmp/claude-1000/`.

**cinnamon-session** (our 6.4.2-1+unity3, five patches). 6.6.4 contains **none**
of them. Upstream master (6.7.x-unstable, `06c8582`), not a release, contains two:
- `csm-systemd-wait-for-logind-s-PrepareForShutdown...` = upstream 9409c18
  line for line; later only 51cb449 (ConsoleKit side, irrelevant under systemd).
- `Don-t-ask-a-Cinnamon-that-is-not-running...` - equivalent in cbcc364 "Clean
  up some end-session warnings" (same `g_dbus_proxy_get_name_owner() == NULL`
  check). Warning: on master our patch applies only with fuzz, into the wrong
  function - drop it there, do not fuzz it.
- Not upstream anywhere: `Ask-the-shell-...` (no `org.gnome.Shell` code in
  master), `Ask-for-a-dialog-when-inhibitors-...`, `Request-the-reboot-or-shutdown-only-once`.
- **Overlap with #214 (host's question):** none. 9409c18 changes
  `csm_manager_quit()` and csm-systemd; our inhibitor patch changes
  `end_session_or_report_inhibitors()` in the query phase. Our quit-once guard
  is still needed on master: `end_phase()` in EXIT still calls
  `csm_manager_quit()` repeatedly, each call reconnects `on_shutdown_prepared`
  and calls Reboot/PowerOff again, logind answers OperationInProgress and the
  session quits "not confirmed by logind". All five patches apply cleanly
  (`git apply --check`) to 6.6.4.
- 6.6.4 behaviour change to keep in mind: it starts/stops
  `cinnamon-session.target` (Wants/PropagatesStopTo `graphical-session.target`),
  which touches the same area as our unity-session login race fix. Master also
  reads `org.cinnamon` schema (b3930ba), shipped only by `cinnamon` - an abort
  risk for us.

**lightdm** (0009 `_exit()` in the SIGTERM handler, LP #2168421). canonical/lightdm#484
is open; `main` (`29b06b45`) still calls `exit()` in `signal_cb()`. Not fixed
in 1.33.0/1.33.1. Our patch applies to 1.33.1 with offset. 1.33.x: no
liblightdm ABI change; greeter cancel path changed (unity-greeter would need a
retest); fixes user switching (`CanMultiSession`). Not in Ubuntu.

**unity-settings-daemon** (cursor, two color fixes, xvfb tests). 26.10.1ubuntu is
the same tree as our base 0ubuntu7 (216f054); the only code difference is
`plugins/color/gcm-self-test.c` (no `gtk_init`, DMI test skipped on
s390x/ppc64el). None of our four changes is in it; the files they touch are
byte-identical. Its packaging moves plugins to `/usr/lib/unity-settings-daemon-1.0/`
while the binary still looks in the multiarch path (stonking `.deb`, from the
paths and `strings`, not run), and drops the session-migration script.

**unity, compiz, unity-session.** No newer version anywhere: stonking = resolute,
gitlab `ubuntu/devel` = our bases, lp:compiz master = our base. None of our
fixes exists upstream. Related work only:
- Gentoo overlay c4pp4/gentoo-unity7: `prevent-compiz-segfault-by-guarding-pthread_join.patch`
  (2026-05-06) is equivalent to our ThumbnailGenerator fix;
  `prevent-duplicate-reboot-shutdown-dialog.patch` switches to RequestReboot/
  RequestShutdown (different approach to the double dialog); `add-nemo-support.patch`
  replaces Nautilus rather than falling back (cf. LP #2160299).
- ubuntu-unity issue tracker #162 (menu dead after cancel = our known issue #2),
  #170 (one confirmation too many): no fix linked.
- LP MP 508187 (LP #2160299): Needs review, two Needs Fixing votes (sponsoring
  bot: no changelog entry/version/LP ref; ~vpa1977: no text).
- unity-session's `run-systemd-session` is a copy of Ubuntu gnome-session's
  script, which Ubuntu dropped in 49~beta; gnome-session's own
  `leader-systemd.c` never stops the targets at start-up (51.0 refuses to start
  if `graphical-session.target` is active). Same conclusion as our guard, no
  code to take.

**gtk-nocsd** 4.8 is still the latest release; main has 20 commits after it,
mostly libadwaita header titles (could change titles in the Unity panel), none
about Chromium/compiz/X11.

**light-locker** unchanged since the 2026-09-23 decision: 1.9.0 still aborts on
missing `XDG_SESSION_PATH`, master last touched 2019.

**xorg-server** (not patched by us): 21.1.23 fixes CVE-2026-50256..50264, 21.1.24
CVE-2026-55999/56000. Ubuntu's tracker has all 11 at needs-triage for resolute;
no security upload visible. LP #2163497 (FindGlyphRef) is **not** in 21.1.24
(fix `8d604fa14` on server-21.1-branch after the tag).
