# UNITY-20260927-022: gtk-nocsd 4.8-1+unity3, normal upgrade path and non-empty LD_PRELOAD

Owner: agent B, `target-desktop-2` (`target2`). Legacy item B-L33
(`docs/research/legacy-migration-20260927/B.md`).

```yaml
task_id: UNITY-20260927-022
package: gtk-nocsd
target_series: resolute
issue: local - verify 4.8-1+unity3 through the repository upgrade path; the
  non-empty-LD_PRELOAD path "is still overwritten" (legacy B-L33)
status: REPRODUCED  # the non-empty overwrite; see Result for whose defect it is
issue_search_result: NOT_FOUND  # exact issue; related reports in search/FINDINGS.md
source_version: 4.8-1+unity3
binary_version: libgtk-nocsd0 4.8-1+unity3 (installed from our aptly by apt)
source_commit: a2a074786f6139a82d08f88f4aa42f35fb0a8e7a  # unity/resolute, lifesupport remote
observed: >
  Empty session LD_PRELOAD: the user manager and every session process carry
  libunity-gtk4-menu.so.0:libgtk-nocsd.so.0 (Unity and Xfce). With
  ~/.xsessionrc exporting LD_PRELOAD=libm.so.6 they carry
  libgtk-nocsd.so.0:libm.so.6 - libunity-gtk4-menu.so.0 is dropped. With
  51gtk-nocsd moved aside (control) they carry libm.so.6 only.
expected: >
  gtk-nocsd is loaded in every X session started through Xsession, and its
  Xsession script never leaves the session with fewer environment.d preloads
  than the same session would have without the script.
reproduction: see Reproduction below (probe.sh, reboot-probe.sh, logs/)
evidence: logs/00..11, boot_id recorded in every probe
root_cause: >
  Not in gtk-nocsd. /etc/X11/Xsession.d/95dbus_update-activation-env
  (dbus-x11 1.16.2-2ubuntu4) runs dbus-update-activation-environment --systemd
  --all; systemd 259 merges the imported (client) block over the
  environment.d block, so an imported LD_PRELOAD replaces the environment.d
  value by design (search/FINDINGS.md 1-2). Any preload that is not re-added
  by an Xsession script of its own package is lost when the session has its
  own LD_PRELOAD.
root_cause_mechanism: >
  ~/.xsessionrc (40x11-common_xsessionrc) exports LD_PRELOAD=libm.so.6;
  51gtk-nocsd prepends libgtk-nocsd.so.0 (non-empty branch); 95dbus imports
  LD_PRELOAD=libgtk-nocsd.so.0:libm.so.6, which replaces environment.d's
  libunity-gtk4-menu.so.0:libgtk-nocsd.so.0. Without 51gtk-nocsd the import is
  libm.so.6 and both environment.d libraries are lost.
root_cause_evidence: logs/06-B-unity3-nonempty.txt, logs/07-C-noscript-nonempty.txt
invariant: >
  gtk-nocsd is preloaded in every Xsession-started session (holds in A, B, D);
  51gtk-nocsd never narrows the preload list compared to the same session
  without it (holds: B is a superset of C, A equals the no-script value).
existing_fix_result: NOT_FIXED  # for the unity-gtk4-menu loss; nothing to fix in gtk-nocsd
candidate_approaches:
  - gtk-nocsd 51 script re-reads the user manager also in the non-empty case -
    rejected: gtk-nocsd would manage another package's preload
  - unity-gtk4-menu ships its own Xsession.d snippet that re-adds
    libunity-gtk4-menu.so.0, as 90atk-adaptor does for GTK_MODULES - the
    owning package; not done here (different package, new task)
chosen_approach: NONE for gtk-nocsd (task closes NOT_APPLICABLE)
why_chosen: >
  The non-empty loss happens with or without gtk-nocsd's script (control C),
  gtk-nocsd itself stays loaded in every case, and the existing convention
  (GTK_MODULES, LP #1644323 / #1843997, 90atk-adaptor) is that each package
  re-adds its own entry in Xsession.
alternatives_rejected:
  - fixing it in gtk-nocsd - wrong layer (see candidate_approaches)
  - changing 95dbus / --all - dbus-x11's file works as designed; systemd #41357
    is the general discussion
code_risks:
  ownership_lifetime: not_applicable
  callbacks_cancellation: not_applicable
  threading_reentrancy: not_applicable
  ABI_API_file_list: not_applicable
design_challenger_required: false
design_review_result: NOT_REQUIRED
architectural_task: false
root_cause_mechanism_layer: dbus-x11 import + systemd merge (by design)
correct_layer: >
  unity-gtk4-menu owns its preload entry and must re-add it in Xsession; the
  gtk-nocsd script owns only libgtk-nocsd.so.0 and already re-adds it.
defensive_workaround_rejected: >
  A generic "merge every environment.d preload" in 51gtk-nocsd would hide the
  missing snippet of another package and make gtk-nocsd responsible for it.
unknowns:
  - sessions not started through /etc/X11/Xsession (e.g. startx without
    Xsession.d) were not measured
  - MATE, LXQt and plain window managers were not measured; the mechanism
    (Xsession.d order) is the same
```

## Reproduction

`probe.sh LABEL` (run on target2 as `mike`) prints the boot id, package
versions, `~/.xsessionrc`, the environment.d preload lines, and `LD_PRELOAD`
of the systemd user manager and of the session processes. `reboot-probe.sh`
reboots target2, waits for compiz or xfwm4, and runs it.

1. Clean-2 → our aptly (`/etc/apt/sources.list.d/unity-distro.sources`) →
   `apt-get full-upgrade` → `apt-get install libunity-gtk4-menu0
   gnome-text-editor xdotool hud-tools` (logs/01, 02).
   The guest clock was 16 h behind, so apt rejected `resolute-updates`
   ("not yet valid"); it was set from the builder before the upgrade
   (logs/01a). The VM's RTC resets it on every reboot, which the later probes'
   `date_utc` shows; it does not affect them.
2. A: reboot, probe (logs/03); GTK4 menu and HUD in gnome-text-editor
   (logs/04).
3. B: `~/.xsessionrc` = `export LD_PRELOAD=libm.so.6` (a library every
   process already maps, so the preload itself changes nothing), reboot,
   probe (logs/05, 06).
4. C (control): `51gtk-nocsd` moved aside, same `~/.xsessionrc`, reboot,
   probe (logs/07). Script put back afterwards, `dpkg -V libgtk-nocsd0` clean
   (logs/08).
5. D: `~/.xsessionrc` removed, `apt-get install xfce4 xfce4-goodies`
   (Xfce 4.20), LightDM autologin session `xfce`, reboot, probe (logs/08,
   09); gnome-text-editor started with the Xfce session environment and with
   `LD_PRELOAD` removed (logs/11, `xfce-check2.sh`).

## Result

| case | session | 51gtk-nocsd | `~/.xsessionrc` | user manager and session `LD_PRELOAD` |
|---|---|---|---|---|
| Clean-2 | Unity | absent (archive 3+0~20260321+0b77e1b-1) | - | `libgtk-nocsd.so.0` |
| A | Unity | +unity3 | - | `libunity-gtk4-menu.so.0:libgtk-nocsd.so.0` |
| B | Unity | +unity3 | `LD_PRELOAD=libm.so.6` | `libgtk-nocsd.so.0:libm.so.6` |
| C | Unity | moved aside | `LD_PRELOAD=libm.so.6` | `libm.so.6` |
| D | Xfce 4.20 | +unity3 | - | `libunity-gtk4-menu.so.0:libgtk-nocsd.so.0` |

Functional checks:
- A: gnome-text-editor maps both libraries; `com.canonical.hud.StartQuery
  "Сохранить"` returns Сохранить / Сохранить как… (Текстовый редактор).
- D: gnome-text-editor with the session environment has
  `_GTK_FRAME_EXTENTS = 0,0,0,0` and an xfwm4 frame, and keeps its in-window
  menu button (`logs/11-D-xfce-session.png`); with `LD_PRELOAD` removed it
  draws client-side decorations, `_GTK_FRAME_EXTENTS = 25,25,25,25`
  (`logs/11-D-xfce-no-preload.png`). A first attempt with mousepad
  (`xfce-check.sh`, logs/10) does not discriminate: mousepad 0.7 draws no
  client-side decorations under Xfce with or without the preload.

**gtk-nocsd 4.8-1+unity3 is verified through the normal upgrade path** on
Unity with unity-gtk4-menu and on a full Xfce.

**The non-empty-LD_PRELOAD loss is not a gtk-nocsd defect.** The control
shows the same session without the script losing both environment.d
libraries; with the script gtk-nocsd stays. What remains lost is
`libunity-gtk4-menu.so.0`, whose package has no Xsession snippet of its own.
That is reported to the coordinator as a separate finding for
unity-gtk4-menu.

Outcome: `NOT_APPLICABLE` for a gtk-nocsd change.

## Files

- `probe.sh`, `reboot-probe.sh`, `xfce-check.sh`, `xfce-check2.sh`
- `logs/`: probe outputs 00-11, the apt log, screenshots
- `search/FINDINGS.md`: existing-fix and issue search
