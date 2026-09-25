# Conversation: MorsMortium (gtk-nocsd) - issue #1

The project's first contact with an upstream maintainer. Read this before
writing anything else to him.

Issue: `Ubuntu-Unity-LifeSupport/unity-distro#1`, "Notice about GTK-NoCSD and
global menu". He is the maintainer of gtk-nocsd (codeberg.org/MorsMortium/GTK-NoCSD),
which Ubuntu Unity already preloads.

## How he found us, and why it matters

Nobody wrote to him. All our repositories are public, and the README of
`unity-gtk4-menu` mentions gtk-nocsd twice - including a claim that both
libraries preload together and both see every call. He almost certainly watches
for mentions of his project. He learned that an LLM was involved from our own
commit trailers, which is exactly why they are there: he was not left to
discover it by accident.

## What he said first (2026-09-24)

1. Preloading two libraries at this level is unwise; in his testing, with his
   library first in `LD_PRELOAD`, it **always** segfaulted.
2. Cases he already handles and we did not: Gir.Core applications using raw
   `dlsym`, Ardour's GTK2 fork, one statically linked application.
3. Two libraries mean duplicated code and more edge cases than one. The feature
   has been requested from him for XFCE, KDE could use it, and he might
   implement it himself.
4. Report bugs if you like, but test against git head: 26.04 ships a commit
   from before all his releases.
5. Closing line: not sure what to say about rehashing his code with an LLM.

All of 1 and 2 turned out to be **correct** - see `research/nocsd-order/`. The
crash was ours: gtk-nocsd replaces `dlsym`, so asking it for `g_module_symbol`
returned our own shim, which called itself until the stack ran out. It crashed
with either preload order. Ubuntu's `-Bsymbolic-functions` hid it from us; his
own `make` does not use it. Fixed in unity-gtk4-menu 0.9 via glibc's
`dlsym@GLIBC_2.34`. Only Ardour was off target - that is GTK2, our shim is GTK4.

## What May sent (2026-09-25 15:54Z)

Written by May, from a draft, under his name. It: admitted the crash was ours
and gave the mechanism; admitted the two uncovered cases; said the feature now
lives inside gtk-nocsd, measured 18/18 on target2, works in real Xfce and
Plasma once `gtk-shell-shows-menubar` is set, which neither sets itself;
said the patch exists as one commit on his current main, in his style, ~890
lines - **and did not attach it**, offering instead: patch, an issue describing
the approach, or nothing. Stated the LLM involvement plainly. Mentioned the
packaging model and the two backported commits (664d8c6, d851645). Said a
couple of bugs were found in gtk-nocsd but deliberately not reported until
re-checked against current main.

## What was deliberately held back for a second message

The first letter was cut roughly in half to be readable. These are ready and
were **not** sent - use them when he asks, or in the follow-up:

- **Why `realize` is replaced in the window class.** The menu must be set
  before the window is realized, because GTK publishes
  `_GTK_MENUBAR_OBJECT_PATH` at realize. His own style of hook - an emission
  hook like `GTKNoCSDHooker` on map - was tried and fires too late: **0 of 16
  applications**. Replacing realize is what `appmenu-gtk-module` has done for
  GTK3 in Ubuntu for years (`hijack.c:287-292`). This is the part we most want
  a second opinion on, and he has now said he will check it himself.
- **The full list of known gaps**: items backed by
  `gtk_widget_insert_action_group` appear but do not activate; the menu is
  copied once, when the first window appears; a plain `GtkWindow` gets no
  stand-ins for window actions; toggling the setting at runtime only affects
  the next window.
- **The desktop survey** in full (`research/nocsd-desktops/`): Xfce 4.20 and
  Plasma 6.6.4 on X11 both work with the flag set; Xfce needs an xfconf key,
  Plasma needs a line in `~/.config/gtk-4.0/settings.ini` that nothing writes.
  A possible improvement, not written: also enable when
  `com.canonical.AppMenu.Registrar` is on the bus, the way appmenu-gtk-module
  does, and hide the window's own menu button.
- Found on the way, not reported anywhere: under Xfce the Debian gtk-nocsd
  package (environment.d) never reaches applications at all, and neither do
  window frames.

## What he answered (2026-09-25 17:0xZ)

He built our patch over his source. Summary, with his own emphasis:

- **He wants part of it upstreamed.** The model cleanup - removing custom
  entries and making proxies - is "functionally perfect in your version, which
  is about half the code. That I would like you to upstream."
- He will check the `realize` replacement himself.
- **He disagrees about the switch.** Nothing in his library is gated by
  settings, everything by environment variables. He would add one to enable it.
  Enabling automatically is odd while the menu button is still there; but
  hiding the button (his implementation does) makes custom entries
  unreachable, so it can never be perfect. He is thinking about the minimal set
  of options, and notes someone may want a menubar in the window instead of a
  hamburger.
- **A defect to check, ours:** our implementation creates a container menu and
  drops all submenus into it. On KDE the entries do not end up in one menu -
  KDE does not expand the holder. He has not tested on Unity. **Verify whether
  Unity expands it; if not, this is our bug, not a difference of taste.**
- His implementation finds menus better, and also covers GTK3, where hamburger
  menus behave differently.
- **His proposed division of work**: he finishes the base - enable/disable,
  menu finding and setting - and then we upstream our part: the cleanup and
  proxies, the realize replacement, possibly the setting-driven loading.

## Open, for May to decide

1. Accept his division of work as proposed?
2. The container-menu finding is a technical question and can be measured
   without deciding anything - ask agent B.
3. The two gtk-nocsd bugs we found are still unreported. He explicitly invited
   reports, provided they are re-checked against current main.

Nothing is sent without May reading the exact text. He answered within about an
hour and read the patch line by line; there is no reason to hurry a reply, and
every reason to make it accurate.
