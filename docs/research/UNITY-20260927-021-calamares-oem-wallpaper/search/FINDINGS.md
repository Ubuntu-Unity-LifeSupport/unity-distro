# UNITY-20260927-021: search for an existing fix (basicwallpaper covers Calamares in the OEM session)

Search date: 2026-09-27. Fresh clone: scratchpad/search021/repo. The shared clone was not fetched.

## 1. Archive versions (rmadison -u ubuntu / -u debian)
- resolute: 1:26.04.12 (universe)
- resolute-updates, resolute-security, resolute-proposed: no entries
- stonking (26.10): 1:26.10.5
- stonking-proposed: no entry (26.10.5 has already migrated)
- noble 1:24.04.39, noble-updates 1:24.04.40 (for reference)
- Debian: none (rmadison -u debian returns nothing)

## 2. Packaging repo git.launchpad.net/~ubuntu-qt-code/+git/calamares-settings-ubuntu
- HEAD = refs/heads/ubuntu/resolute = c6997017d2fe (2026-04-21, "Uh, we kind of need Calamares on the OEM sessions..."). This is the same commit as tag ubuntu/1%26.04.12. There are no resolute commits after the tag.
- refs/heads/ubuntu/stonking = 64cfce81107c (2026-09-24, "Fix rmcdrom", changelog 1:26.10.5). The newest tag is ubuntu/1%26.10.4. No tag exists yet for 26.10.5.
- master = 3c1c1b2 (2021). It is stale.
- Commits c699701..origin/ubuntu/stonking that touch common/basicwallpaper/, ubuntuunity/oem/ or */oem/*:
  - 80d43f1 2026-09-14 Update Lubuntu welcome images (lubuntu welcome-oem.png)
  - e1c25ab 2026-06-02 Update Kubuntu branding and config for 26.10 (kubuntu oemid.conf, calamares-launch-oem.desktop, welcome-oem.png)
  - 0c1dc0f 2026-05-11 Welcome to Stonking! (version strings in */oem/calamares-launch-oem.desktop, ubuntuunity po/branding)
  - aa4909a 2026-05-11 Fix theming for the .desktop file (ubuntuunity/ubuntu-unity-calamares.desktop.in)
  - 0597c18 2026-05-11 Reconfigure to utilize pkgselectprocess ..., fix the OEM sed invocation (kubuntu/lubuntu oem/calamares-launch-oem, ubuntuunity modules)
  - 267c373 2026-05-11 Re-introduce the dynamic checkboxes for pkgselect ... (ubuntuunity/modules/pkgselect.conf)
  - No commit touches common/basicwallpaper/ or ubuntuunity/oem/ubuntu-unity-oem-env/.
  - `git diff c699701 origin/ubuntu/stonking -- common/basicwallpaper` is empty.
- All-time history of common/basicwallpaper: 4629bba (2024-02-14, OEM overhaul, added the tool), 95b9217 (2025-02-21, CMake bump), 53012ae (2025-09-25, removed menubar/statusbar from the .ui). None of these fixes focus or stacking.
- Current main.cpp window setup, identical on resolute and stonking:
  ```
  MainWindow *w = new MainWindow(wallpaperFile);
  w->setWindowFlags(Qt::WindowStaysOnBottomHint);
  w->setGeometry(screen->geometry());
  w->showFullScreen();
  w->show();
  w->applyWallpaper();
  ```
  The window already carries WindowStaysOnBottomHint (_NET_WM_STATE_BELOW). It has no desktop window type and no WindowDoesNotAcceptFocus, and it is fullscreen. On X11 this is not enough under xfwm4: a focused fullscreen window is moved into the fullscreen layer. There is no Wayland-specific code path upstream.
- start-ubuntu-unity-oem-env is unchanged on stonking: xfwm4 &, basicwallpaper ubuntu-unity-default.png &, sudo calamares -D8.
- Local clone ~/unity-distro/packages/calamares-settings-ubuntu HEAD: b6b546b "basicwallpaper: desktop window on X11, so it cannot cover Calamares" (+16/-2 in main.cpp). This is our local fix.

## 3. Issue search
Launchpad searchTasks with all statuses (New ... Fix Released, Invalid, Won't Fix, Expired, Opinion, Does Not Exist):
- ubuntu/+source/calamares-settings-ubuntu:
  - "wallpaper": 2 hits (#1965645 Studio logo, #2060845 Kubuntu branding). Not relevant.
  - "basicwallpaper": 0 hits.
  - "OEM wallpaper": 0 hits.
  - "Alt+Tab": 0 hits.
  - "focus": 3 hits, none relevant.
  - "OEM": 10 hits (#2063403, #2060928, #2107539, #2127123, #2064180, #2055799, #2125435, #2138456, #2149813, #2150381). None is about the wallpaper covering Calamares. #2149813 "Kubuntu's OEM installation mode is broken" is the fix in 26.04.12 (Calamares removing itself).
- ubuntu/+source/ubuntu-unity-meta:
  - "wallpaper", "basicwallpaper", "OEM wallpaper", "Alt+Tab", "OEM": 0 hits each.
  - "focus": 2 hits, not relevant.
- ubuntu/+source/calamares:
  - "wallpaper": 1 hit (#2003157 Lubuntu calamares window closed, Expired). Not relevant.
  - "basicwallpaper", "OEM wallpaper", "Alt+Tab": 0 hits.
  - "focus": 1 hit, not relevant.
- Upstream project "calamares-settings-ubuntu" on Launchpad: the API returned non-JSON (there is no such LP project; the bugs live on the source package).
- GitLab ubuntu-unity/issue-tracker (API /projects/ubuntu-unity%2Fissue-tracker/issues?search=...&state=all):
  - "wallpaper": 7 hits (#185, #168, #160, #128, #118, #22, #4). None is about OEM or Calamares. #160 "Add release notes for 26.04" does not contain the OEM wallpaper text.
  - "OEM": 0 hits.
  - "basicwallpaper": 0 hits.
  - "Alt+Tab": 0 hits.
  - "calamares": 1 hit (#147 daily uninstallable), not relevant.
  - "focus": 1 hit (#133), not relevant.
  - "installer": 56 fuzzy hits, none relevant.
- Result: no bug report exists for this defect. It is only mentioned in the release notes.

## 4. Lubuntu / Kubuntu
- Lubuntu (lubuntu/oem/lubuntu-oem-env/start-lubuntu-oem-env): an X11 session with openbox &, basicwallpaper &, then sudo calamares. It uses the same binary and the same window flags. It has not changed since tag c699701 (only the welcome image changed). Openbox also puts focused fullscreen windows into its fullscreen layer, so Lubuntu is plausibly affected too. This is not verified.
- Kubuntu: kwin_wayland --xwayland running kubuntu-oem-env-shim, which starts basicwallpaper & and then sudo calamares. This is the Wayland path. It has not changed apart from branding.
- Neither flavour has changed basicwallpaper since it was introduced.

## Result
- existing_fix_result: FIXED_LOCAL. The only fix is our local commit b6b546b. Nothing exists in resolute, in stonking 1:26.10.5 or its git branch, or in Debian.
- issue_search_result: NOT_FOUND. Trackers searched: Launchpad calamares-settings-ubuntu, ubuntu-unity-meta and calamares (Ubuntu source packages, all statuses), and GitLab ubuntu-unity/issue-tracker.
