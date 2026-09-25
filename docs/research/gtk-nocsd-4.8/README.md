# gtk-nocsd 4.8 for Chromium decorations (LP #2158965)

Agent A, 2026-09-25. Result: `gtk-nocsd 4.8-1+unity1` in aptly, installed and
verified on target.

## The bug

[LP #2158965](https://bugs.launchpad.net/bugs/2158965) =
[codeberg #67](https://codeberg.org/MorsMortium/GTK-NoCSD/issues/67): Chrome,
Edge and other Chromium browsers lose their window buttons in a window under
Unity, shortly after start. `env -u LD_PRELOAD` avoids it. Upstream fixed it
in [ecd66fe](https://codeberg.org/MorsMortium/GTK-NoCSD/commit/ecd66fe95850b2416ba85fbfcac9f0d248837dcf)
(2026-04-28, in 4.0): Chromium creates a window it never shows only to read
GTK settings from it, and gtk-nocsd emptied `gtk-decoration-layout` in those
settings. Chromium reads the layout and draws no buttons. The reporter
confirmed 4.x fixes it. Resolute still has the 2026-03-21 snapshot and no SRU
is under way.

Reproduced on target with Google Chrome 154 and our `+unity2`:
no buttons with the library preloaded, buttons on the left without it
(`runs/01-chrome-old-vs-new.png`, `runs/09-tests.txt`).

## What we ship

A merge of Debian's `4.8-1` (salsa `ubports-team/gtk-nocsd`, the same version
as 26.10) into our `unity/resolute` branch, as `4.8-1+unity1`. Our two quilt
backports (d851645, 664d8c6, crash handler) are part of 4.0 and are dropped;
the series is empty. The orig tarball is codeberg's `4.8.tar.gz`; it is
identical to the `4.8` git tag.

Why the whole of 4.8 rather than cherry-picking ecd66fe: ecd66fe does not apply
to our snapshot (33 earlier commits change the same file, and it conflicts), the version is the one Debian
and 26.10 ship, upstream calls all 4.x releases bugfix releases, and it fixes
more than #67 (gnome-sound-recorder below). The price is six months of
behaviour changes, so they were checked application by application.

Binary version: Debian dropped the `3+` prefix that `debian/rules` added to
the binary packages. `4.8-1+unity1` still sorts above
`3+0~20260321+0b77e1b-1+unity2`; apt on target offers it as the upgrade.

## Checked on target

Old and new library side by side: the old `.so` copied to `/tmp/nocsd-u2` and
preloaded in place of the installed one, every process checked in
`/proc/PID/maps`. Scripts: `chrome-deco.sh`, `nocsd-ab.sh`.

- **Chrome**: buttons with 4.8, none with `+unity2`, same session.
- **13 applications**, GTK3, GTK4, libadwaita, libhandy, file chooser, zenity
  dialog: all keep server-side decorations. The only differences are
  upstream's title handling: gnome-text-editor drops the header title that
  repeats the window title; gnome-characters, seahorse and yelp show a title
  in the header that was empty (`runs/02..07`). transmission-gtk started in
  neither run; not investigated.
- **gnome-sound-recorder**: crashed with `+unity2` (core dump, 2 of 2; the
  crash in DECISIONS 2026-09-24), runs with 4.8 (2 of 2).
- **Crash handler**: a GTK3 program that segfaults is restarted by the
  handler, and the handler itself does not crash. compiz killed with SIGSEGV
  in a session started with 4.8 comes back within 2 s, decorated
  (`runs/08`).
- **Logout and relogin** with 4.8: no bad journal lines, no activation
  timeouts, no crash files.

A first round of screenshots was taken with `xwd -root` and showed GTK4
windows without a title bar; that was the `xwd` artifact already recorded in
DECISIONS, and `gnome-screenshot` shows them decorated. All screenshots here
are `gnome-screenshot`.

## Side finding

uutils `timeout` (`/usr/lib/cargo/bin/coreutils/timeout`) re-raises a child's
SIGSEGV with core dumps enabled, so apport files a `timeout` crash whenever a
child segfaults. GNU timeout disables core dumps first. Not ours, not
investigated, not reported.

## Not done

- Nothing reported upstream or on Launchpad. For #2158965 a comment that a
  4.8 SRU fixes it would help Ubuntu; May's call.
- Chrome's "use system title bar" mode and Edge not tested.
