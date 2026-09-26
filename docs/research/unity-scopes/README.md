# Unity scopes and lenses in the 26.04 archive

Agent B, 2026-09-26, on `target2`: Unity session, Python 3.14.4, our
`libunity +unity1` (the scope runner without `imp`,
`research/libunity-python314/`). target2 was rolled back to `Clean-2`
afterwards.

All 17 `unity-scope-*` and `unity-lens-*` packages of the resolute archive
were installed and started by D-Bus activation (`load.sh`), and queried in
the Dash.
- The Dash test types a scope keyword (`calc:`, `man:`, `vbox:`,
  `gnote:`) or opens a lens with its shortcut (`dash.sh`).
- `direct.py` imports a Python scope's module and calls its `search()`, to
  see the error without the Dash.

The eight Python scopes have the same versions in 26.10 (`rmadison`); the
lenses were not compared.

## Installing together

- **Ten Python scopes** each shipped `/usr/lib/python3/dist-packages/__init__.py`
  (`src/__init__.py` installed by setup.py), so dpkg refused a second one.
  The ten are calculator, devhelp, gnote, launchpad, manpages, soundcloud,
  tomboy, virtualbox, yahoostock and zotero. The scope itself loads from
  `/usr/share/unity-scopes/<name>/`, where its own `__init__.py` stays.
- **`unity-scope-home`** (installed by default) declares `Conflicts:` with
  `unity-scope-soundcloud` and `unity-scope-yahoostock`, among other removed
  online scopes. That is intentional and left as it is. Installing either of
  them removes the home scope.

**Fix:** `debian/rules` of seven packages removes that file after
`setup.py install`. The seven are calculator, devhelp, gnote, manpages,
tomboy, virtualbox and zotero.
- **launchpad is not rebuilt.** Its build runs tests against
  api.launchpad.net and fails without network, and it is an online scope.
  It is now the only package with the file, so nothing conflicts any more.

With the seven `+unity1` and the archive's launchpad, all 8 Python scopes,
the 5 lenses, video-remote and home are installed together.

## Table

The load column is D-Bus activation: the service owns its name after 6 s.
The Dash column is a real query in the Dash.

| scope | installs together | loads | answers in the Dash | fixed |
|---|---|---|---|---|
| lens-applications (C) | yes | yes | yes: "calcul" → LibreOffice Calc (`shots/apps.png`); logs a harmless "software-center xapian" error | - |
| lens-files (C) | yes | yes | yes: recent file and folder (`shots/files.png`); its global search calls `locate`, which is not installed | - |
| lens-music (C) | yes | yes | yes: "no music on this computer" (`shots/music.png`); no library to show | - |
| lens-video, scope-video-remote (C) | yes | yes | yes: "nothing found" for a non-video file (`shots/video.png`); the remote part is online | - |
| lens-photos: shotwell | yes | yes | yes: "no results" (`shots/photos.png`); no Shotwell library | - |
| lens-photos: picasa | yes | yes | not queried: `RemoteContent=true`, remote search is off | online, left alone |
| lens-photos: facebook, flickr | yes | **no**: `ImportError: Requiring namespace 'Soup' version '2.4', but '3.0' is already loaded`, and apport files a crash | not queried: `RemoteContent=true`, remote search is off, so no crash from the Dash (checked: 0 new crash files after a photos search) | online, left alone |
| scope-home (C) | yes | yes | aggregates the rest | - |
| calculator | **yes (+unity1)** | yes | yes: `calc: 2*21` → 42 (`shots/calc-42.png`) | `__init__.py` |
| manpages | **yes (+unity1)** | yes | yes: `man: printf` → 25 pages (`shots/man-printf.png`); before: none, `TypeError` | `__init__.py`; GTK 3 required, see below |
| gnote | **yes (+unity1)** | yes | yes: `gnote: B4probe` → the note, with Gnote not running (`shots/gnote-note.png`); before: none | `__init__.py`; activation retry, see below |
| virtualbox | **yes (+unity1)** | yes | only with VirtualBox installed (`QueryBinary=virtualbox`, by design). With stub `virtualbox`/`vboxmanage` it gives the VM (`shots/vbox-stub.png`) | `__init__.py` |
| devhelp | **yes (+unity1)** | yes | nothing to show: no `.devhelp2` books in `/usr/share/gtk-doc/html` in 26.04; `QueryBinary=devhelp` | `__init__.py` |
| tomboy | **yes (+unity1)** | yes | cannot work: Tomboy is not in the archive (`org.gnome.Tomboy` unknown) | `__init__.py` |
| zotero | **yes (+unity1)** | yes | cannot work: it reads Zotero's Firefox-extension profile under `~/.mozilla/firefox`; no Zotero in the archive | `__init__.py` |
| launchpad | yes (only owner of the file) | **no**: `Exec=/usr/bin/python`, which 26.04 does not have | - | online, left alone |
| soundcloud, yahoostock | only by removing scope-home (Conflicts) | - | - | online, removed on purpose, left alone |

A scope installed while the home scope is running is not used until the
home scope restarts, at the next login. That is how the home scope reads
its registry, not a bug.

## The two code fixes

**manpages.** `unity_manpages_daemon.py` imports `Gtk` without a version.
PyGObject then loads GTK 4, and `Gtk.IconTheme.lookup_icon(name, 128, 0)`
raises `TypeError` (GTK 4's takes 7 arguments), so every search failed.
- The package depends on `gir1.2-gtk-3.0`, so the fix is
  `gi.require_version('Gtk', '3.0')`.
- Checked with and without `DISPLAY`: 25 results for "printf".

**gnote.**
- The scope makes its `org.gnome.Gnote` proxy at import. A search while
  Gnote is not running starts it by D-Bus activation
  (`gnote --shell-search`).
- Gnote 49 registers `/org/gnome/Gnote/RemoteControl` only once it is up,
  so the call fails with `UnknownMethod`. The `--shell-search` instance
  quits when idle, so every later search failed the same way.
- The fix retries the call for up to 3 s (15 × 0.2 s). Checked in the Dash
  with Gnote not running.

## Found, not ours

- Files lens: global search runs `locate`, and neither `plocate` nor
  `mlocate` is installed or depended on. Recent files still work.
- The Python scopes print invalid-escape `SyntaxWarning`s (`"\s"`, `"\("`),
  and yahoostock uses `"is" with 'int' literal`. They are warnings only.
- yahoostock imports `feedparser` without depending on it. It is online
  and removed anyway.

## Files

- `debdiff/`: the seven source changes against the archive.
- `load.sh`, `direct.py`, `dash.sh`, `gnote_fix.py`.
- `shots/`: the Dash screenshots cited above.

The seven `+unity1` source packages are in aptly. Their build is in
`~/work/b/scopes`; there is no git tree, since these are small
Ubuntu-native packages and aptly holds the sources.
