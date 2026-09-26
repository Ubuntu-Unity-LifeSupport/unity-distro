# unity-control-center: every panel run on target (A-7, 2026-09-26, agent A)

target = clean snapshot + our aptly (u-c-c `0ubuntu13+unity1`, then `+unity2`).
Each panel opened on its own (`tools/ucc-panels.sh`), then one setting per
panel changed **through the panel** (AT-SPI actions = the widget's own click
path, `tools/a11y.py`, `tools/ucc-apply.sh`) and checked at the consumer, then
changed back. Results: `A7-panels.log`, `A7-apply.log`.

**Harness trap, recorded so nobody repeats it:** started from ssh without the
session's `XDG_CURRENT_DESKTOP`, u-c-c shows only the three external items
(language, printers, software) and "Could not find settings panel" for every
panel - the panels' desktop files say `OnlyShowIn=Unity7`. Run it with the
session's environment (`tools/ucc-open.sh` copies it from nemo-desktop).

| Panel | Opens | Setting changed through the panel | Reached the consumer | Found |
|---|---|---|---|---|
| Оформление (appearance) | yes | theme Yaru-dark -> Yaru -> back | yes: a new GTK process sees `Yaru` (u-s-d XSETTINGS), back to `Yaru-dark` | 7x "Unknown Tag: filename-dark" (GNOME wallpaper XML), icon themes Yaru-bark/viridian without index.theme - cosmetic |
| Экран (display) | yes | - (one virtual monitor; resolution not changed in a VM) | - | "Unknown Display" name (no EDID in VirtualBox) |
| Клавиатура (keyboard) | yes | key repeat off/on | yes: `xset q` auto repeat off/on (u-s-d) | - |
| Мышь (mouse) | yes | primary button right/left | yes: X button map 3 2 1 / 1 2 3 (u-s-d) | - |
| Ввод текста (region) | yes | per-window input sources on/off | yes: `org.gnome.libgnomekbd.desktop group-per-window` true/false - read by indicator-keyboard and u-s-d | depends on libgnomekbd schemas (see below) |
| Сеть (network) | yes | - (switching the NIC would cut ssh) | - | **2 GLib CRITICALs** `g_utf8_collate` on a device without title yet - **fixed in +unity2** |
| Bluetooth | yes | "show in menu bar" off/on | yes: `com.canonical.indicator.bluetooth visible` | no adapter in the VM |
| Звук (sound) | yes | mute on/off; "show volume in menu bar" off/on | yes: PulseAudio sink mute yes/no; indicator-sound `visible` | VM stream warnings only |
| Питание (power) | yes | - | - | no battery in the VM |
| Время и дата (datetime) | yes | show seconds on/off | yes: `com.canonical.indicator.datetime show-seconds` | - |
| Яркость и блокировка (screen) | yes | require password after suspend off/on | yes: `ubuntu-lock-on-suspend` | "Screen backlight not available" (VM) |
| Специальные возможности (universal-access) | yes | large text on/off | yes: Unity `text-scale-factor` 1.25 -> Xft DPI 96 -> 120 -> 96 | sub-options insensitive until their switch is on - correct |
| Учётные записи (user-accounts) | yes | - (changes need the polkit password) | - | "Automatic login" shows off although target logs in automatically: accountsservice reads only `/etc/lightdm/lightdm.conf`, target's autologin is in `lightdm.conf.d` (our test snapshot) - **accountsservice** |
| Сведения о системе (info) | yes | - | - | the updates button accepts only PackageKit 0.8.x (1.3.4 here) and has been permanently off since PackageKit 0.9 - old, not a regression; recorded |
| Security & Privacy (activity-log-manager) | yes | lock when returning from blank screen off/on | yes: `org.gnome.desktop.screensaver lock-enabled` | untranslated (English) - **activity-log-manager** |
| Цвет (color) | yes | - | - | "device does not support colour management" (VM) |
| Sharing | yes | - (would start services) | - | "Unknown state alias for sshd.service" - warning |
| Планшет Wacom | yes | - | - | no tablet |
| Принтеры | external | - | - | system-config-printer, by design |

No crash, no CRITICAL left after `+unity2`, no empty panel.

## libgnomekbd (LP #2136945) - assessment only

Removed from Debian (RM #1144251, 2026-08-13), archived upstream; still in
resolute and 26.10 - Unity is its last user in 26.10. **26.04 LTS is not
affected** (nothing is removed from a released series). If Ubuntu removes it
(most likely 27.04): u-c-c (Depends gkbd-capplet, Build-Depends
libgnomekbd-dev) and indicator-keyboard (libgnomekbd-common) become
uninstallable; without the schema indicator-keyboard aborts at start, u-c-c's
region panel and u-s-d's Fcitx path (unguarded `g_settings_new`) crash. Our
code uses no gkbd_ API - only the two GSettings schemas and
`gkbd-keyboard-display` - so the exit is cheap: ship the schemas ourselves,
drop the unused build-dependencies, replace the "show layout" program (tecla)
or hide it. Not done.
