# UNITY-20261012-001: GTK-NoCSD main fd4b76a, re-checked

Owner: agent B (target2). A research task with no package. It re-checks GTK-NoCSD main `fd4b76a`
(MorsMortium/GTK-NoCSD on codeberg, 2026-10-09) against `b76f3fb`, the build measured in UNITY-20261008-001. The
same rig is used, on the current live stack.

The commits after `b76f3fb`:

| commit | subject |
|---|---|
| `7f49f81` | Do not strip accelerators in global menus |
| `52fa72e` | Hide LibAdwaita title widget if title would show without subtitle and should not |
| `5f5acae` | Hide labels which are exactly the application name, in the header |
| `98264c2`, `dfc6066` | the theme setting |
| `f76b9a8` | an option to disable it for undecorated windows |
| `fd4b76a` | no crash handler after the application wanted to stop |

## Results

| question | result |
|---|---|
| (a) Alt mnemonics on the Unity panel | **fixed by `7f49f81`.** The exported labels keep their underscores again (`_File`, `_Edit`, `Со_хранить`; 9 of 11 Text Editor items). With real keys, Alt+F opens Pinta's File menu, and Alt+F10 opens the Text Editor holder with the mnemonic letters underlined. `b76f3fb` (labels stripped) gives the HUD instead. |
| (b) where our session sets `GTK_NOCSD_MENU` | **nowhere.** No package of ours sets it. Our gtk-nocsd 4.8-1+unity3 has no global-menu code. GTK4 global menus come from our libunity-gtk4-menu, which is active only when `XDG_CURRENT_DESKTOP` is Unity. Upstream's dropped `gtk-shell-shows-menubar` check does not affect us. |
| (c) the types bug (UNITY-20260927-038 claim 14) | **still reproduces on `fd4b76a`.** With a GObject created before GTK is loaded, `GTKNoCSDGTKWindow` stays 0 at exit; the control fetches the type. The early return in `GTKNoCSDGetReferences` is unchanged. |
| (d) `52fa72e`, `5f5acae` in Unity | **they work as described.** A custom `AdwWindowTitle` equal to the window title, or to the application name, is hidden, and it shows again when its text changes. Of 6 applications, only Nautilus changes visibly: the sidebar header «Файлы» (the application name) is hidden. The other five headers are unchanged. |

## Where it ran

- **target2:** restored to Clean-2 and confirmed from inside (no `~/.dirty`, no work directories, only
  `ubuntu.sources`). Then our live archive the usual way and `apt full-upgrade`, which installed gtk-nocsd
  4.8-1+unity3, hud +unity6 and unity +unity13 (logs/01).
- **Installed for the task from the archive:**
  - the build tools: build-essential, libgtk-4-dev, libgtk-3-dev, libadwaita-1-dev, gdb, git, dotnet-sdk-10.0;
  - the test tools: xdotool, x11-utils;
  - Text Editor, Nautilus, Loupe, Calculator, Clocks, Baobab;
  - libunity-gtk4-menu0 0.9, explicitly: an upgrade does not bring it in, the known UNITY-20260927-037.
- **Not available:** fractal is not in resolute, so `52fa72e`'s own case (Fractal Room Details) is replaced by
  `tests/titletest.c`.
- **Builds on target2,** `make` on `git archive` of each commit, 0 warnings:
  - `b76f3fb`, sha256 `81bcb168…`, byte-identical to UNITY-20261008-001's U build;
  - `fd4b76a`, sha256 `03e751de…`;
  - `2d50fe9`, our series as upstream carries it (authored by NeiroNext), sha256 `4535bda5…`, byte-identical to
    UNITY-20261008-001's S build.
  - Pinta 3.1.2 from its release tag (`b3df1e5`), with dotnet-sdk-10.0.
- **The session:** Unity, `XDG_CURRENT_DESKTOP=Unity:Unity7:ubuntu`,
  `LD_PRELOAD=libunity-gtk4-menu.so.0:libgtk-nocsd.so.0`, `GTK_MODULES=appmenu-gtk-module:gail:atk-bridge`. No
  `GTK_NOCSD_*` variable is set in the session or in the systemd user environment (logs/02).
- **Method:** `start.sh` installs one build as `libgtk-nocsd.so.0` and starts the application with
  `LD_PRELOAD=libgtk-nocsd.so.0` alone, because our libunity-gtk4-menu would export a second menu. It sets the
  build's switch (`GTK_NOCSD_MENU=1`; `GTK_NOCSD_GLOBAL_MENU=1` for `2d50fe9`) and prints the exported menu
  (research/nocsd-gaps `audit.py`). The keys come from the host: vbox `send_keys`, with screenshots.

## (a) Alt mnemonics (logs/03)

| build | exported labels | Pinta Alt+F | Text Editor Alt+F10 |
|---|---|---|---|
| `b76f3fb` | `File`, `Сохранить` (stripped) | the HUD opens | (UNITY-20261008-001: the holder opens, nothing underlined) |
| `fd4b76a` | `_File`, `Со_хранить`, 9 of 11 Text Editor items with an underscore | File menu opens (3 of 4 starts) | the holder opens, the letters underlined (2 of 2 after focus) |
| `2d50fe9` (control) | `_File` | File menu opens | - |

- `7f49f81` changes the accelerator marker of `pango_parse_markup` from `'_'` to `0` (GTK-NoCSD.c:3933). That is
  exactly the place UNITY-20261008-001 found.
- The first start of an application in a session did not react to the key until the window was focused again
  (Pinta with `fd4b76a`, then with `2d50fe9` in a new session; Text Editor with `fd4b76a`). Later starts reacted at
  once. The behaviour is the same for both builds, so it is not a difference between them.
- The menus of the first starts were exported correctly (`audit.py`). INFERENCE: the panel takes the menu up only
  after a focus change for an application it sees for the first time. Not investigated further.
- Pinta's items carry no mnemonic of their own. The guest's keyboard layouts (gb, us) cannot type Cyrillic item
  letters, so activating an item by its letter inside an open menu is not tested, as before.
- A side note on UNITY-20261008-001: counted in the label column only, its logs give 228 labels with an underscore
  for S and 0 for U. That card says 229 for S.

## (b) `GTK_NOCSD_MENU` in our session

The live packages, read as files from the published pool:

- **gtk-nocsd 4.8-1+unity3:**
  - It installs `usr/lib/environment.d/50-gtk-nocsd.conf` and `/etc/X11/Xsession.d/51gtk-nocsd`. Both only add
    `libgtk-nocsd.so.0` to `LD_PRELOAD`.
  - Its library reads `GTK_NOCSD_CSD`, `_CSD_PADDING`, `_GNOME`, `_NO_CSS`, `_NO_GTK3` and `_NO_GTK4`. It has no
    `GTK_NOCSD_MENU`, no `org.gtk.Menus` and no menubar code: the 4.8 release has no global menus.
- **libunity-gtk4-menu0 0.9:**
  - Its `usr/lib/environment.d/60-unity-gtk4-menu.conf` adds the library to `LD_PRELOAD` in every systemd user
    session.
  - The library itself checks `XDG_CURRENT_DESKTOP` ("XDG_CURRENT_DESKTOP=%s is not Unity") and stays inactive
    elsewhere unless `UNITY_GTK4_MENU_FORCE` is set.
- **In the live session (logs/02):** the variables listed under "Where it ran", and no `GTK_NOCSD_*` anywhere.

So upstream's removal of the `gtk-shell-shows-menubar` check changes nothing for us today.

**Rule for the future:** if we ever ship upstream's menu code instead of libunity-gtk4-menu, `GTK_NOCSD_MENU=1`
must be set for Unity sessions only. Not in a global `environment.d` file, which every session reads.

## (c) The types bug (logs/02)

`typesorder` (UNITY-20260927-038 `tests/typesorder.c`) under gdb with `trace.gdb`, with each build preloaded:

| build | with the early GObject | control (`SKIP_EARLY_OBJECT=1`) |
|---|---|---|
| `b76f3fb` | at exit `version=4 gottypes=1 GTKNoCSDGTKWindow=0` | the GtkWindow type fetched |
| `fd4b76a` | at exit `version=4 gottypes=1 GTKNoCSDGTKWindow=0` | the GtkWindow type fetched |

The condition `(GTKNoCSDGotTypes && OldGTKVersion == GTKNoCSDNewGTKVersion) || !GetTypes` (GTK-NoCSD.c:1522) is
unchanged. Real Gir.Core applications (Pinta) load GTK first and are not affected, as measured before.

## (d) `52fa72e` and `5f5acae` (logs/04, logs/05)

`tests/titletest.c` builds an `AdwHeaderBar` with a custom `AdwWindowTitle` and no subtitle. The window title is
"Document One". After 3 s the `AdwWindowTitle` text changes to "Changed text 42".

| mode (start text) | `b76f3fb` | `fd4b76a` |
|---|---|---|
| same ("Document One") | shown throughout | hidden (`show-title=0`, unmapped) until the change, then shown |
| appname ("titletest") | shown throughout | hidden until the change, then shown |
| differ ("Something else") | shown throughout | shown throughout |

- **Reading the code:** in `52fa72e` the inner `else`, the restore of the original `show-title`, can never run,
  because the outer condition already requires `gtk_widget_get_child_visible(WindowTitle)`. The measurement shows
  it does not matter: `AdwHeaderBar` hides the title without clearing child-visible. So the outer branch runs again
  on the next change and sets `show-title` back to TRUE.
- **Real applications** (`headers.sh`, `logs/05-headers.png`, b76f3fb left, fd4b76a right):
  - Nautilus: the sidebar header «Файлы» is hidden with `fd4b76a` (`5f5acae`). In Unity the application name is
    still on the panel and in the launcher.
  - Text Editor, Calculator, Clocks, Loupe, Baobab: no visible change in the header.

## Summary

- `7f49f81` restores the Alt mnemonics on the Unity panel: Pinta and GNOME Text Editor, real keys.
- The types bug (`typesorder`) still reproduces on `fd4b76a`.
- `52fa72e` and `5f5acae` behave as described in Unity; the hidden title comes back when its text changes.
- Nothing to fix on our side from this re-check. Our packages do not use upstream's menu code.
