# The messaging menu under Unity on 26.04

Agent B, 2026-09-26, coordinator's task B-10. Measured on `target2`: a Unity
session from Clean-2 plus the packages named below. target2 was rolled back
to `Clean-2` afterwards.

## The problem

- **The library is Ayatana's.** The only messaging menu library in 26.04
  is `libmessaging-menu0` 24.5.1 from **ayatana-indicator-messages**. It
  talks to `org.ayatana.indicator.messages`.
- **Unity's indicator is Canonical's.** `indicator-messages`
  (Canonical, `com.canonical.indicator.messages`) has no client library
  any more, so no client can reach it. See
  `research/rebuild-loss/`: after a direct D-Bus registration its envelope
  appears.
- **Unity's panel doesn't load Ayatana indicators.** The panel reads
  `/usr/share/unity/indicators` only. It rejected Ayatana indicators
  ("indicator menu item must be of type 'com.canonical.indicator.root'").
- **Result.** Under Unity the messaging menu stayed empty for every
  client.
- **Not even installed.** A default Unity install does not have Canonical
  indicator-messages at all.

**Clients in resolute that link `libmessaging-menu0`** (`apt-cache
rdepends`): geary, pidgin, hexchat-indicator, telepathy-indicator,
ayatana-webmail (through the GIR), plus the date-time indicators (ours
included), which link it but do not show messages.
- Thunderbird is a snap (a transitional deb).
- Evolution does not use it.

Pidgin registers itself on start, with its status items (Available, Away,
Busy, Invisible, Offline). Geary's application entry and actions (Compose,
New window) are what `mmclient.py` registers under its desktop id, through
the same library.

## The three options, measured or estimated

| option | cost | risk | what the user sees |
|---|---|---|---|
| **1. Show ayatana-indicator-messages on Unity's panel** (chosen) | small, two packages: libindicator (ours) learns Ayatana's root type and item types; ayatana-indicator-messages `+unity1` links its indicator file into `/usr/share/unity/indicators` | low: only Ayatana indicators take the new code path, and Unity's own indicators are unchanged (sound menu checked); the service already starts in Unity from its XDG autostart (`OnlyShowIn=Unity;…`) | Unity's classic envelope and menu: status items, per-application sections, sources with counts, Clear |
| 2. Build Canonical's libmessaging-menu next to Ayatana's | the Canonical source no longer builds the library; bringing it back gives a second `libmessaging-menu.so.0` / `libmessaging-menu0` with the same name and soname | high: the two packages conflict, and one replaces the other for every client. Ayatana and Lomiri users of the library break. We would carry a dead library | the same as 1, at a much higher price |
| 3. A D-Bus bridge `org.ayatana…` ↔ `com.canonical…` | a new daemon of ours that mirrors applications, sources and actions between two protocols that have diverged | medium: every protocol difference is a bug surface, and it is a new component doing a job an existing one already does (CLAUDE.md rule) | the same as 1, once it works |

Option 1 reuses the maintained Ayatana service and the Ayatana client
library that every client already links. Unity gains only a reader.

## The fix

**libindicator `16.10.0+18.04.20180321.1-0ubuntu8+unity2`**
(`packages/libindicator`, `67bfe16`, `package-patches-b/libindicator/0002`):
- `indicator-ng.c` accepts a root item with
  `x-ayatana-type=org.ayatana.indicator.root`, and `x-ayatana-scroll-action` /
  `x-ayatana-secondary-action`.
- An Ayatana indicator's popup is bound through a small `GMenuModel`
  wrapper. The wrapper gives each Ayatana item type the matching
  `x-canonical-type`, where Unity's IDO (`libido3-0.1`) has that item.
  - The table covers application, alarm, appointment, basic, calendar,
    location, messages.source, progress and switch, plus media-player,
    playback-item and slider as `com.canonical.unity.*`.
  - Other types stay plain. An unknown `x-canonical-type` makes GTK drop
    the item. A first build, which mapped every type by prefix, lost the
    application rows that way.
- Without the wrapper, sources show as plain, greyed rows (GTK's model
  binding leaves a stateful action without a target insensitive).

**ayatana-indicator-messages `24.5.1-1build1+unity1`** (debdiff in
`package-patches-b/debdiff/`):
- `debian/ayatana-indicator-messages.links` links
  `usr/share/ayatana/indicators/org.ayatana.indicator.messages` into
  `usr/share/unity/indicators/`.
- The package's 3 tests pass.

Both are in aptly.

**Still needed for a default install.** Clients depend only on
`libmessaging-menu0`, and nothing in the Unity set installs
ayatana-indicator-messages; only Lomiri pulls it in. `ubuntu-unity-desktop`
(ubuntu-unity-meta) now recommends it (B-11, below).

## Checked on target2

After a reboot with both packages installed:
- **One starter.** The service is started once, by its XDG autostart
  entry; its systemd unit stays inactive, since nothing in Unity wants
  it.
- **Envelope and menu.** `mmclient.py` registers Geary's desktop id with an
  "Inbox" source of 3 messages that draws attention. The envelope turns
  "new" (`shots/ayatana-messages-panel.png`). The menu shows Geary with
  Compose and New window, Inbox with a count bubble of 3, and Clear
  (`shots/ayatana-messages-menu.png`).
- **Click Inbox.** The client receives `activate-source inbox`, and the
  envelope clears.
- **Click Geary** while it is not running: Geary starts. It asks to unlock
  the login keyring (autologin), which was cancelled
  (`shots/ayatana-messages-geary.png`).
- **Pidgin.** It registers itself with its status section
  (`shots/ayatana-messages-pidgin.png`).
- **Unity's own indicators** render as before
  (`shots/unity2-sound-menu.png`: sliders and media player).

## Found on the way: overlay-scrollbar breaks GTK2 clients

Clicking Pidgin's entry while Pidgin runs starts a second Pidgin, which
should hand over to the first. The second one dies at once:

`/usr/lib/x86_64-linux-gnu/gtk-2.0/modules/liboverlay-scrollbar.so: undefined symbol: ubuntu_gtk_set_use_overlay_scrollbar`

- **Why.** `/etc/X11/Xsession.d/81overlay-scrollbar` (overlay-scrollbar-gtk2)
  exports `GTK2_MODULES=overlay-scrollbar` for the whole session. The
  module needs Ubuntu's old GTK2 patch, which is gone; this is the same
  dead package as in `research/rebuild-loss/`.
- **Proof.** With the service restarted without `GTK2_MODULES`
  (`nogtk2.sh`), the same click raises Pidgin's buddy list.
- **Who pulls it in.** `ubuntu-unity-desktop` (source ubuntu-unity-meta,
  no owner) recommends overlay-scrollbar-gtk2. Fixed in B-11, below.

## Canonical indicator-messages and its double start

Canonical indicator-messages is started twice: systemd, through
`unity-panel-service.service.wants`, and XDG autostart. The second
instance exits on the bus-name loss.
- It is superseded by option 1.
- It is not in a default Unity install.
- Under Unity it can have no client.

It stays in aptly as `0ubuntu8~26.04.1` (it builds), but nothing should
install it for Unity. Removing one of its starters is not worth a change.
Ayatana's service, which Unity now uses, has a single starter.

## B-11: overlay-scrollbar and the metapackage (2026-09-26, agent B)

**Rule 0.** Nobody has fixed it:
- 26.10 (stonking) ships the same overlay-scrollbar 0ubuntu5, with the
  same dead module and Xsession script.
- Its ubuntu-unity-meta 0.30 swaps some applications but still recommends
  overlay-scrollbar-gtk2.
- Debian never had the package.

**Choice: a stub package, not Breaks in the metapackage.**
- **Stub (chosen).** `overlay-scrollbar 0ubuntu5+unity1` reaches every
  system that has the package, whether or not the metapackage is still
  installed. Its maintscript `rm_conffile`s
  `/etc/X11/Xsession.d/81overlay-scrollbar`. `overlay-scrollbar-gtk2`
  becomes an empty transitional package, so a plain `apt upgrade` takes it
  without removing anything.
  - Nothing is compiled any more.
  - `overlay-scrollbar` keeps only the `com.canonical.desktop.interface`
    schemas, which unity-tweak-tool still reads.
- **Breaks (rejected).** Breaks in `ubuntu-unity-desktop` would only reach
  users who keep the metapackage. `apt upgrade` holds back a package whose
  upgrade must remove another. Dropping a Recommends alone uninstalls
  nothing, so the variable would stay.

**ubuntu-unity-meta 0.29+unity1.** In `desktop-recommends-*` (all four
architectures):
- `overlay-scrollbar-gtk2` is replaced by `ayatana-indicator-messages`;
- the built deb differs from the archive's by exactly these two Recommends
  entries.

The rest of both lists was checked against resolute:
- every entry exists, and none is dead;
- the lists name packages without versions, so the packages we override
  in aptly (unity, the indicators, u-s-d, u-c-c, …) are taken by version
  number, with no change to the lists.

Both debdiffs are in `package-patches-b/debdiff/`, and both packages are in
aptly.

**Checked on target2.** The test ran from Clean-2, which has the archive
0.29, overlay-scrollbar 0ubuntu5 and `GTK2_MODULES=overlay-scrollbar` in
the session. Adding our aptly and running `apt-get full-upgrade` gave:
- dpkg: `Removing obsolete conffile /etc/X11/Xsession.d/81overlay-scrollbar`;
- installed: ayatana-indicator-messages +unity1, libindicator3-7 +unity2,
  overlay-scrollbar(-gtk2) +unity1, ubuntu-unity-desktop 0.29+unity1;
- `liboverlay-scrollbar.so` is gone.

After a reboot:
- **No `GTK2_MODULES`.** The compiz environment has no `GTK2_MODULES`,
  and `GTK_MODULES` is `appmenu-gtk-module:gail:atk-bridge`.
- **Pidgin** (archive, GTK2), installed afterwards, starts with no module
  error. The envelope menu shows its status items and entry
  (`shots/b11-pidgin-menu.png`).
- **Clicking Pidgin** while it runs raises its buddy list, which becomes
  the active window (`shots/b11-pidgin-raised.png`). The hand-over
  instance exits normally; one `pidgin` process is left.

**Found, not fixed.** GTK2 applications log `Failed to load module
"appmenu-gtk-module"`, which is harmless.
- `GTK_MODULES` names the appmenu module, and its GTK2 build,
  `appmenu-gtk2-module`, was last shipped in noble (and Debian bookworm);
  it left along with GTK2 support.
- So GTK2 applications keep their menu inside the window, with no global
  menu.
