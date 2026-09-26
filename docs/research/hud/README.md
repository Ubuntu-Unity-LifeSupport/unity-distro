# hud on 26.04: rebuild and live check

Agent B, 2026-09-26, coordinator's task B-12. Measured on `target2`: Clean-2,
then our aptly and `full-upgrade`. target2 was rolled back to `Clean-2`
afterwards.

## Rule 0

- resolute and stonking (26.10) both carry `14.10+17.10.20170619-0ubuntu6`,
  the noble upload. It was never rebuilt, and hud is not in Debian.
- Launchpad has no hud bug created or changed since 2026-04-01. The two FTBFS
  bugs are old: LP #1257861 (arm64, 2013, fixed) and LP #1812904 (gtk-doc,
  2019, no patch).
- Upstream `lp:hud` (trunk.15.10) was last changed in 2020. The ubuntu-unity
  group on GitLab has no hud project.

Nobody has fixed the build, so the fix is ours.

## The build: `14.10+17.10.20170619-0ubuntu6+unity1`

The source failed to build in resolute for three reasons, one after another:

| layer | cause | fix |
|---|---|---|
| 1 | CMake 4 dropped compatibility with `cmake_minimum_required` < 3.5 | 3.10 in `CMakeLists.txt` and `cmake/*.cmake` |
| 2 | `systemd.pc` moved to `systemd-dev`, `systemduserunitdir` came out empty, and CMake refused to install `hud.service` and `window-stack-bridge.service` | Build-Depends `systemd-dev` |
| 3 | resolute's googletest needs C++17; the tests did not compile | `-std=c++17` (was `-std=c++14`, 0ubuntu6's own bump for googletest) |

The debdiff is `package-patches-b/debdiff/hud_+unity1.debdiff`.

**Result.** The package builds in a clean `sbuild -d resolute` with the tests
on, as before:
- 6 of 6 ctest suites pass (integration 6, libhud 10, libhud-client 15,
  service 44 gtest cases, and others). `test-qtgmenu-unit-tests` has 0 cases,
  upstream's own state.

**Against the archive binaries (14 packages):**
- File lists are equal. This includes `usr/lib/systemd/user/hud.service`,
  `window-stack-bridge.service` and its `unity-session.target.wants` link.
- The exported symbols of libhud, libhud-client and libhud-gtk are equal.
- Depends differ only by higher lower bounds, which resolute satisfies.

The package is in aptly, source included.

## Live check on target2

HUD by a tap of Alt, then a query. The script is `ht.sh`.
- Applications must be started with the session's environment, taken here
  from compiz.
- Started from a bare ssh shell, they lack `GTK_MODULES` and `LD_PRELOAD`.
  They then have no global menu, and the HUD finds only "Window actions".
  The first attempt in this check made exactly this mistake.

| application | menu path | result |
|---|---|---|
| gnome-text-editor 50 (GTK4) | unity-gtk4-menu 0.9 | "сохран" → Сохранить, Сохранить как… (`shots/hud-gtk4-text-editor.png`) |
| GIMP 3.2 (GTK3) | appmenu-gtk-module | "Размыть" → Размыть / Повысить резкость (Инструменты, Рисование) (`shots/hud-gtk3-gimp.png`). The first queries right after start were empty while hud-service walked GIMP's large menu for the first time (`AboutToShow` timeout in the journal). Queries after that answer at once |
| LibreOffice 26.2 Writer (own GMenu export) | `_GTK_MENUBAR_OBJECT_PATH` | intermittent, see below |

hud-service did not crash once over the whole check:
- no crash file;
- no coredump;
- its PID changed only on the restarts done on purpose.

The legacy D-Bus interface Unity's HUD uses (`com.canonical.hud.StartQuery`)
and `hud-cli` gave the same results.

## LibreOffice: found, predates our rebuild, not fixed

`lo3.sh N` starts Writer N times in the session environment. After each start
it asks `StartQuery "Сохранить"` twice, 5 s apart.

| hud | runs with results |
|---|---|
| archive 0ubuntu6 (noble build) | 4/5, 6/10: 10 of 15 |
| ours +unity1 | 3/5, 2/4, 1/5, 5/10: 11 of 24 |

A failed run stays empty; waiting does not help. Both builds fail, and the
difference is within the noise of these samples, so our rebuild did not
introduce this.

Two mechanisms were seen:

1. **window-stack-bridge drops the window** (1 run in each build).
   - `BamfWindow`'s constructor asks bamf for the application's
     `DesktopFile()`. When bamf has not exported that application object yet,
     the call fails (`Could not get desktop file … UnknownMethod`) and
     `m_error` is set.
   - `addWindow` then never adds the window, and nothing retries.
   - The window is missing from `GetWindowStack` for its whole life, and the
     HUD has nothing for it.
   - The code already falls back to the window id when the desktop file is
     empty; an error could take the same fallback.
2. **The window is known, but its GMenu yields nothing** (the other failures).
   - `dbus-monitor` shows that hud-service gets complete window properties
     on every start, failed ones included: LO's bus name,
     `/org/libreoffice/window/N/menus/menubar`, the application and window
     action paths, and appmenu's `_UNITY_OBJECT_PATH`.
   - So the loss is later, in collecting the menu model (LibreOffice fills
     its GMenuModel after the window is up). Not traced further.

Also seen, harmless: window-stack-bridge takes the application id from
`QFileInfo::baseName()`, so every reverse-DNS desktop file
(`org.gnome.TextEditor.desktop`) becomes the id `org`.

## Found on the way: gtk-nocsd +unity2 removed unity-gtk4-menu from the session (fixed in +unity3)

**The bug in +unity2.**
- Our `/etc/X11/Xsession.d/51gtk-nocsd` (gtk-nocsd 4.8-1+unity2,
  `research/nocsd-gaps/`) set `LD_PRELOAD=libgtk-nocsd.so.0` in the X
  session.
- `95dbus_update-activation-env --all` then wrote that over the value the
  user manager had built from environment.d.
- Compiz, the user manager and every application started from the session
  were left with gtk-nocsd only, so no GTK4 application had a global menu or
  HUD.
- Proof: with the script moved aside and a reboot, the same session had
  `libunity-gtk4-menu.so.0:libgtk-nocsd.so.0`. The GTK4 row above was
  measured in that session.

**Fix: gtk-nocsd `4.8-1+unity3`** (May's approval through the coordinator;
commit `a2a0747` on `unity/resolute`,
https://github.com/Ubuntu-Unity-LifeSupport/gtk-nocsd).
- When the session has no `LD_PRELOAD`, `51gtk-nocsd` starts from
  `systemctl --user show-environment`, that is from environment.d's full
  list, and then adds gtk-nocsd if it is missing.
- It always exports the result.
- The debdiff against +unity2 is `51gtk-nocsd` and the changelog only.

**Checked.**
- Simulation with a stand-in `systemctl`, four cases: the user manager has
  both libraries; it has gtk-nocsd only; there is no user manager; the
  session already has a preload. Each gives the expected value in
  `LD_PRELOAD` and `STARTUP`.
- **Unity on target2**, Clean-2 + aptly + unity-gtk4-menu + +unity3, after
  a reboot:
  - the user manager, compiz, unity-panel-service and hud-service all
    have `libunity-gtk4-menu.so.0:libgtk-nocsd.so.0`;
  - gnome-text-editor's menu is on the panel
    (`shots/gtk4-menu-after-nocsd-unity3.png`);
  - the HUD finds Сохранить / Сохранить как….
- **Xfce on target2** (minimal xfce4-session, xfwm4, panel; autologin):
  - xfce4-session, xfwm4 and xfce4-panel have the same `LD_PRELOAD`, so
    gtk-nocsd is still loaded, which was the point of +unity2;
  - the GTK4 editor keeps its in-window menu button, so unity-gtk4-menu
    takes nothing away without a Unity panel;
  - the window looks the same as with gtk-nocsd alone
    (`shots/xfce-nocsd-unity3.png`). Its missing xfwm4 title bar is there
    in both runs, from the minimal Xfce install.

## Known limitation: no global menu for GTK2 applications

- GTK2 applications (Pidgin) log `Failed to load module
  "appmenu-gtk-module"`: `GTK_MODULES` names the module, and its GTK2 build
  `appmenu-gtk2-module` was last shipped in noble and Debian bookworm.
- Their menus stay in the window.
- Not planned (coordinator, B-12).
