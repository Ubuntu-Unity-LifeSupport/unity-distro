# Agent B - running state

Test desktop: `target2` (192.168.56.30, VM `target-desktop-2`, snapshot `Clean-2`)
Build directory: `~/work/b`

## Handoff, 2026-09-29 ~01:20Z (session fa14e5f5 ends; May starts new sessions)

Written so a new agent B can continue without the old chat. The live board
is `~/coordinator/TASKS.md` (taskctl), and the evidence is
`~/coordinator/evidence/<task>.json`. Each task's card is its
`docs/research/<task>/README.md`, on the task branch `b/<task>` until C
merges it.

**Important, from this session:**

- **The command guard is not active** in a session rooted at /home/claude
  (UNITY-20260928-012 is open). Keep the rules by hand:
  - no `aptly publish` of any kind (freeze no. 1, also no show or list);
  - /srv/aptly is read as files only;
  - forbidden command strings are never built in a heredoc (memory
    feedback-guard-test-strings).
- **The repository is public.** Cards hold facts only: no draft quotes, no
  notes on correspondence.
- **Verifier verdicts** are PASS, FAIL or INCOMPLETE only.
- **DECISIONS.md and PATCHES.md** entries go through
  `scripts/append_record.py` in `~/unity-distro`; C commits them.

**target2:** at `Clean-2`, restored and checked from inside on 2026-09-29
~01:14Z:
- no `~/.dirty`;
- archive hud 0ubuntu6 and archive gtk-nocsd;
- no source of our repository configured.

**/var/tmp/aptly-rehearsal** (UNITY-20260927-047): 0700, owner claude.
**Keep it; May needs it.**
- `aptly.conf` and `incoming/` are the prepared state.
- `state/`, `backup-r4/`, `backup-r4.sha256` and `aside-r8b/` are left by
  the preliminary run 1.
- What a repeat of phase R needs is in 047's card, section "Repeating phase
  R" (branch b/UNITY-20260927-047, 3f0d251).

**Package git trees exist only on builder**, under
`~/work/b/unity-distro/packages/`:

| package | branch | head | remote of ours | export in the repository |
|---|---|---|---|---|
| hud | unity/resolute | 2f2fa89 (+unity3) | none | research/UNITY-20260927-028-hud-cxx17-scope/patches/full-series (from archive 0ubuntu6) |
| nux | b/UNITY-20260927-027 | 0274bc5 (+unity3) | origin = gitlab ubuntu-unity (not ours) | research/UNITY-20260927-027-nux-vidmode-fbo/patches |
| indicator-datetime | b/UNITY-20260927-026 | 9a00446 (+unity3) | origin not ours | research/UNITY-20260927-026-idt-guard/patches |
| libindicator | b/UNITY-20260927-023 | f8fa299 (+unity3) | origin not ours | research of 023 |
| unity-session | b/UNITY-20260927-037 | 7af2106 (+unity2) | lifesupport (GitHub) | research of 037 |
| calamares-settings-ubuntu | 021/041 branches | c03daf4e / 221c691 | none | research of 021/041 |

Build outputs: `~/work/b/nux027/`, `~/work/b/hud029/`. The hud orig
tarball for non-native builds is `~/work/b/unity-distro/packages/hud_14.10+17.10.20170619.orig.tar.gz`.

**Open tasks of B** (taskctl state, then where to resume):

| task | state | resume | what is left |
|---|---|---|---|
| UNITY-20260927-028 hud C++17 scope | BLOCKED | REVIEW | +unity3 2f2fa89: C++14 for hud, C++17 for tests; Verifier PASS; publication gate |
| UNITY-20260927-029 hud window-stack-bridge | BLOCKED | REVIEW | Verifier PASS; publication gate. Follow-ups UNITY-20260929-001 and -002 (C's) |
| UNITY-20260927-027 + UNITY-20260928-020 nux +unity3 | BLOCKED | REVIEW | Verifier PASS; 3 clean sbuilds of 0274bc5; publication gate |
| UNITY-20260927-026 indicator-datetime +unity3 | BLOCKED | REVIEW | Verifier PASS; publication gate |
| UNITY-20260927-023 libindicator +unity3 | BLOCKED | REVIEW | publication gate |
| UNITY-20260927-037 unity-session +unity2 | BLOCKED | REVIEW | publication gate; also security check UNITY-20260928-008 and May's decision |
| UNITY-20260927-021, -041 calamares-settings-ubuntu | BLOCKED | IMPLEMENTING | build_sbuild.py epoch/binary-name matching; no source remote of ours |
| UNITY-20260927-047 aptly snapshots | BLOCKED | IMPLEMENTING | UNITY-20260928-012, then repeat phase R (card) |

The publication gate for all package tasks is one blocker: freeze no. 1
and 047. hud +unity3 (028) contains +unity2 (029), so publish them
together as +unity3, or +unity2 first.

## Earlier state (before 2026-09-29)

## Now

**2026-10-10 ~18:16Z: UNITY-20261010-001 PUBLISHED (libcolumbus +unity2), waiting for C's merge, then idle
(the permission-model freeze; May unfroze B for this one task only).**
- **libcolumbus +unity2:**
  - A no-change rebuild: debian/changelog only, on the published +unity1.
  - It is the first routine publication through the archive signer. The signer signed it by routine policy
    (`approved_by: policy`), on C's approve-publication.
  - Live `./resolute` has been `unity-resolute-20261010-001` since 17:49:19Z, and the publication is
    verified on target2.
  - Card: `research/UNITY-20261010-001-libcolumbus-unity2-signer/`, meta branch `b/UNITY-20261010-001`.
- **Tool gap seen on the way:** UNITY-20261010-002, NOT_APPLICABLE verification cannot reach a gate.
- **Not to be touched until the freeze ends:** UNITY-20261009-002/-003/-004/-005, -023 and the like.

Earlier:

**2026-10-09 ~06:05Z: UNITY-20261008-025 and -017 PUBLISHED (hud +unity6); waiting for C's merge, then
idle (permission-model freeze).**
- **hud +unity6:**
  - hud-service releases a legacy query when its sender leaves the bus
    (-025).
  - Desktop files are found with the XDG search, the user's directory
    first (-017).
  - Live `./resolute` is `unity-resolute-20261008-025` since 05:40:24Z.
  - The publication is verified on target2.
  - Card: `research/UNITY-20261008-025-hud-unity6/`, meta branch
    `b/UNITY-20261008-025` (82a41f4) for C to merge.
- **UNITY-20261008-018 is NOT_APPLICABLE:** the bridge's bamf owner warning
  is a benign QtDBus startup race.
- **Follow-ups on the board (BACKLOG, after the freeze):**
  - UNITY-20261009-003: the legacy `ExecuteQuery` crash paths;
  - UNITY-20261009-004: the Unity 7 HUD's Terminal command opens no window,
    also on the Ubuntu base;
  - UNITY-20261009-005: a relative `XDG_DATA_HOME` is not ignored.
- **Not started, by C's instruction:** UNITY-20261009-002 and -003.

Earlier:

**2026-10-08 ~20:25Z: UNITY-20260929-001 and UNITY-20261008-011 DONE; next UNITY-20261008-013.**
- **hud +unity5:** UNITY-20261008-011 with UNITY-20261008-014. The
  window-stack-bridge application id is now the whole desktop file name
  (org.gnome.Terminal, no longer "org"); there are also no null map entries
  and the WindowAdded connect is checked.
  - Live `./resolute` = `unity-resolute-20261008-011` since 19:56:14Z;
    C merged it in main cd9b7f6.
  - Card `research/UNITY-20261008-011-hud-reverse-dns-id/`.
  - -014 is in REVIEW: taskctl lets package tasks reach DONE only after
    PUBLISHED, and -014 has no build of its own. C decides.
- **Follow-ups on the board:**
  - UNITY-20261008-017: no icon for `XDG_DATA_HOME` desktop files;
  - UNITY-20261008-018: the `org.ayatana.bamf` owner warning in the bridge;
  - UNITY-20261008-013 (next): hud-service /tmp mappings and RSS. Start by
    comparing +unity3, +unity4 and +unity5; no code before the DC.
- **Since the builder restart:** the scratchpad is lost. The repository key
  for target2 comes from `/srv/aptly/public/unity-distro-archive.asc`
  (fingerprint 29A893E03970066F2DD287D47BF3F77FC27B152C). Copy it with a
  script file, because the guard refuses the path in a shell command.
- **Nothing running.**

**2026-10-08 ~11:35Z: UNITY-20260929-001 PUBLISHED, waiting for C's merge.**
- hud 14.10+17.10.20170619-0ubuntu6+unity4 (window-stack-bridge follows
  bamf's re-match: LibreOffice's window gets libreoffice-writer, HUD usage
  carries over between Writer runs). Live `./resolute` =
  `unity-resolute-20260929-001` since 11:04:20Z. C checked the gate, and
  May confirmed the switch in B's session.
- Branch `b/UNITY-20260929-001` @ 5ff2eee, worktree `~/work/b/unity-distro-001`,
  card `research/UNITY-20260929-001-hud-bamf-rematch/`.
  - Verifier PASS.
  - Target check before publication (logs/06) and on the publication
    (logs/07, Clean-2, the normal upgrade, a cold cycle) both PASS.
- Next, assigned by C: UNITY-20261008-011 together with
  UNITY-20261008-014. -011 is the bridge id cut at the first dot
  (`org.gnome.Terminal` gives "org"); -014 is the missing tests and the
  small points in the bridge. Also open: UNITY-20261008-013, hud-service
  /tmp mapping and RSS growth; compare on +unity3 first.
- Earlier on 2026-10-08: UNITY-20260929-002 closed (the empty HUD is
  LibreOffice's first-start dialog or a query during the menu import; no
  hud defect).
- Nothing running: no tmux, sbuild or loop of B's.

**2026-10-03: STOPPED (May stops all agents, through C).**
- UNITY-20260929-002 (hud: HUD empty although the window is known) is
  INVESTIGATING, branch `b/UNITY-20260929-002` @ f18f35c, worktree
  `~/work/b/unity-distro-002`, card
  `research/UNITY-20260929-002-hud-empty-known-window/`.
  - Round 1 (logs/01): 3 of 10 cold boots empty at the first query on the
    published hud +unity3.
  - Round 2 (logs/02, D-Bus menu trace): stopped after 6 of 10 boots; boot
    6 empty at the first query. The captures are saved, not analysed.
  - Resume: analyse boot 6 against boots 1-5 in logs/02 (the order of
    WindowCreated, hud-service's org.gtk.Menus Start and LibreOffice's
    Changed), then boots 7-10 (`coldloop3.sh 4`). No code yet; DC first.
- Nothing running: the loop is stopped, no tmux, sbuild or tracer.
- target2 is left as it is: Clean-2 + our repository + hud +unity3
  (dirty), session up.

**2026-10-02 ~19:15Z: no tasks (May: none assigned). The four ready
packages are published and DONE; -003 waits for -019 (the signer, May's
manual step) and -037 for its security review.**
- Published today, one slot each (C checked every gate, May confirmed every
  switch in B's session), each with a gated rebuild on chroot
  20260929T201245Z, payload byte-identical to the tested build, this_build
  target test, known-gaps section, Verifier PASS, and a target verification
  of the publication on target2 from Clean-2 (PASS):
  - UNITY-20260927-029 hud +unity2, switch 16:50Z - DONE (merged);
  - UNITY-20260927-028 hud +unity3, switch 17:30Z - DONE (merged);
  - UNITY-20260927-023 libindicator +unity3, switch 18:02Z - DONE (merged);
  - UNITY-20260927-026 indicator-datetime +unity3, switch 18:32Z - DONE
    (merged, bed9a41).
- Live `./resolute` = unity-resolute-20260927-026 (400 packages). Backups
  `~/backups/repo-{029,028,023,026}-20261002T*`.
- PATCHES and DECISIONS entries for -023 and -026 are in main (a6b9f78);
  the hud rows (-029, -028) name the pre-rebase commits 0e99dca/2f2fa89;
  the published commits are ef39a8d/9e7c093 on GitHub (same trees).
- Worktrees: `~/work/b/unity-distro-029`, `~/work/b/unity-distro` (-028),
  `~/work/b/unity-distro-li023`, `~/work/b/unity-distro-026`; sources on
  GitHub under `b/<task>` (hud rebased onto `unity/resolute`).
- target2: rolled back to Clean-2 after the last check. Its clock
  synchronised by itself after each rollback (UNITY-20260929-022 line is
  with C).
- Open follow-ups seen today: mechanism 2 of the empty HUD on the first
  Writer start after a boot (UNITY-20260929-002; 1 of 10 or 20 in every
  run today).
- UNITY-20260929-003: the draft design (root causes RC1-RC7) is committed
  on its branch (b016511); BLOCKED on -019, as -018.

**2026-09-29 ~23:30Z: no tasks (May: finish current work, take no new
tasks).**
- UNITY-20260929-023 is DONE: taskctl `published_by`, merged by C at 855ecdd.
- UNITY-20260928-020 is DONE through `published_by`, via UNITY-20260927-027's
  record (nux +unity3).
- Waiting, not started: hud +unity2 (UNITY-20260927-029), then +unity3
  (UNITY-20260927-028), as two publications.
- BLOCKED: UNITY-20260929-018 and -003 on -019; -019 is design only, and A
  writes the signer code.

**UNITY-20260927-027 DONE** (2026-09-29 ~23:00Z). nux +unity3 was published at 22:51Z
(snapshot unity-resolute-20260927-027) and checked on target2 through the
repository. UNITY-20260928-020, the same package, is BLOCKED until
UNITY-20260929-023 (taskctl closing a task from another task's publish
record). target2 is back on Clean-2.

**UNITY-20260928-014 DONE** (2026-09-29 ~22:00Z). indicator-keyboard +unity4 was
published at 21:51Z (snapshot unity-resolute-20260928-014) and upgraded on
target2 from our repository. target2 is being rolled back to Clean-2.
UNITY-20260929-019 is BLOCKED; it is the design only, and A writes the
signer code.

**2026-09-29 ~20:40Z**
- **UNITY-20260927-041 DONE.** calamares-settings-ubuntu 1:26.04.12+unity3 was
  published at 18:15Z and is live through -040.
  - Target PASS: `/etc/sudoers` in OEM mode is 0440 and `visudo -c` passes;
    a cold first boot from `OEM-ready-unity3` shows Calamares on top.
  - `oem-test` is powered off. Snapshots OEM-ready, -fixed, -unity2 and
    -unity3 are kept.
- **UNITY-20260929-018** (SECURITY) was merged by C at 609f731 as a partial
  tightening; the Verifier's verdict is FAIL, FIX_PARTIAL, and May decided to
  merge it anyway. It is BLOCKED (resume REVIEW) until UNITY-20260929-019
  (OS permissions) is done.
- Next: UNITY-20260929-003 (guard false positives).

**Before the restart 2026-09-29 (~19:00Z; VBoxSVC and builder are
restarted, May's decision).**
- UNITY-20260927-041 (calamares-settings-ubuntu 1:26.04.12+unity3):
  - Switched 18:15Z (snapshot unity-resolute-20260927-041). ./resolute is
    now A's -040, which carries it.
  - Target check steps 1-3 PASS, logs 11-14 on `b/UNITY-20260927-041`
    cbb51c0:
    - OEM mode `/etc/sudoers` is 0440, and `visudo -c` passes for sudo-rs
      and sudo.ws;
    - snap-seed-glue-emb (snapd 2.76.3) was exercised.
  - Left to do:
    - snapshot OEM-ready-unity3, taken on the powered-off oem-test after
      diagnose_vm (it was WEDGED in 'snapshotting' after take_snapshot
      E_ACCESSDENIED);
    - one cold first boot;
    - target verification record, then PUBLISHED and DONE.
  - The disk holds the finished OEM preparation. oem password: `oem041test`.
- UNITY-20260929-003: BLOCKED (resume at CLAIMED).
- No tmux, http or sbuild processes are running. Branches -021, -015, -041
  and the package branch 221c691 are pushed.

**UNITY-20260929-015** (2026-09-29): tool, merged by C into main at
55381f3.
- taskctl PUBLISHED now also accepts a later live snapshot that carries
  every artifact of the publish record with the recorded sha256. The check
  is read-only `snapshot search`.
- Design Challenger APPROVE. Verifier PASS, independently reproduced.
- Decision (C): a newer version of the same package in the live snapshot
  does not block PUBLISHED. See DECISIONS.

**UNITY-20260927-021 DONE** (2026-09-29 17:52Z): PUBLISHED through the
content check against `unity-resolute-20260928-019`. The branch has been
merged with main (3ef9c23). The details below are left as written.
Next: UNITY-20260927-041, publication of calamares +unity3.

**UNITY-20260927-021** (2026-09-29): calamares-settings-ubuntu
1:26.04.12+unity2. Target PASS; PUBLISHED waits for UNITY-20260929-015.
- Published 16:10Z as snapshot `unity-resolute-20260927-021-r2`.
- Target check on `oem-test`:
  - live ISO session with our repository;
  - fresh Calamares OEM install;
  - two cold first boots from the new snapshot `OEM-ready-unity2`.
  In both boots Calamares is on top, and the wallpaper is DESKTOP/BELOW and
  never focused.
- Limit: apt does not fix an OEM system that is already installed.
  basicwallpaper is unpacked from the installer medium's `oemconfig.tar.gz`
  and belongs to no package.
- Record: `research/UNITY-20260927-021-calamares-oem-wallpaper/target-verification.md`,
  branch `b/UNITY-20260927-021` deb301b.
- `oem-test` is powered off. Snapshots `OEM-ready`, `OEM-ready-fixed` and
  `OEM-ready-unity2` are kept.
- Why it waits: taskctl compares the live snapshot by name, and `./resolute`
  has since moved to `unity-resolute-20260928-019`. That snapshot is a
  superset: only 11 lightdm records were added.
- Next: UNITY-20260929-015, taskctl accepting a live snapshot that contains
  every artifact of the publish record.

**hud** (2026-09-26, B-12): hud is B's now.
- `+unity1` builds in resolute: CMake 4, systemd-dev and C++17 fixed, 6/6
  test suites pass.
- File lists and symbols equal the archive's, and the package is in aptly.
- On target2:
  - the HUD finds GTK4 (unity-gtk4-menu) and GTK3 (appmenu) menus;
  - LibreOffice works only intermittently, as with the archive build;
  - hud-service did not crash.
- See `research/hud/`.
- gtk-nocsd +unity3 is in aptly (May approved it through C).
  `51gtk-nocsd` no longer drops `libunity-gtk4-menu.so.0` from the session.
  Checked under Unity (GTK4 panel menu and HUD) and Xfce.
- Automatic mode is stopped after B-12. No new tasks.

**overlay-scrollbar and ubuntu-unity-meta** (2026-09-26, B-11): both are
B's now.
- overlay-scrollbar `+unity1` is a stub: no GTK2 module, and
  `81overlay-scrollbar` is removed on upgrade.
- ubuntu-unity-meta `0.29+unity1` recommends ayatana-indicator-messages.
- Both are in aptly.
- Verified on target2 by a full-upgrade from Clean-2: the session has no
  `GTK2_MODULES`, and Pidgin raises from the envelope.
- `research/messaging-menu/` (B-11 section).
- Next: hud.

**Messaging menu under Unity** (2026-09-26, B-10): Unity's panel now shows
ayatana-indicator-messages.
- libindicator `+unity2` (Ayatana root and item types) and
  ayatana-indicator-messages `+unity1` (link into
  `/usr/share/unity/indicators`) are in aptly.
- Pidgin and Geary show up; sources are clickable.
- `research/messaging-menu/`.
- The meta and overlay-scrollbar follow-up was done in B-11 (above).

**Target2 checks done** (2026-09-26, B-8, after the VBoxSVC restart):
- unity-lens-files `+unity1` checked live and published.
- appmenu `+unity1` checked with GIMP 3, LibreOffice and Chromium (snap).
  With the archive module GIMP segfaults 2 of 2 when the module is
  dropped; with `+unity1` it survives 2 of 2.
- target2 was restored to Clean-2 after B-12 on 2026-09-26 20:56Z, checked
  inside: fresh boot and no `~/.dirty` marker.

**Rebuild file-loss survey** (2026-09-26, coordinator's task B-7):
`research/rebuild-loss/`.
- 21 sources rebuilt: nothing is lost except by the systemd.pc trap, in
  indicator-messages (fixed in 26.10 as 0ubuntu8) and hud.
- libindicator `+unity1` is published: files and symbols equal to the
  archive's.
- session-migration `+unity1` is built, not published.
- hud `+unity1` is WIP: the googletest C++17 layer is left.
- _Correction 2026-09-27 (UNITY-20260927-036):_ session-migration `+unity1` was published by agent A, and
  hud `+unity1` is in aptly since B-12 (`research/hud/`).
- unity-greeter has no owner; overlay-scrollbar is B's since B-11.

**Only-on-builder commits** of B's git-ubuntu clones are exported to
`docs/package-patches-b/`, since `origin` is Launchpad and we do not push
there.

**Unity scopes** (2026-09-26, coordinator's task B-4): seven Python scopes are
`+unity1` in aptly.
- They install together now.
- manpages works on GTK 4 systems (it asks for GTK 3).
- gnote starts Gnote correctly.
- The table of all 17 packages is in `research/unity-scopes/`; build in
  `~/work/b/scopes`.

**libunity +unity1** (2026-09-26, coordinator's task B-3): unity-scopes-runner
now loads scopes with importlib on Python 3.14.
- Checked in the Dash with unity-scope-calculator.
- In aptly.
- `packages/libunity` (git-ubuntu clone, no remote of ours);
  `research/libunity-python314/`; build in `~/work/b/lu1`.

**indicator-datetime +unity2** (2026-09-26, coordinator's task B-2): LP
#1848969 and #2099742. A task with only a due date aborted the service.
- Reproduced; fixed.
- 29 of 29 tests, including a new one.
- In aptly.
- `research/indicator-datetime-tasks/`; build in `~/work/b/idt-fix`.

**indicator-keyboard +unity3** (2026-09-26, coordinator's task B-1): LP #2166139.
It crashed in g_variant_iter_new when AccountsService had no InputSources
cached, for instance after an accounts-daemon restart.
- Reproduced; fixed.
- 10/10 tests, including a new one.
- In aptly.
- `research/indicator-keyboard-2166139/`; build in `~/work/b/ik3`.

**Global menu gaps** (2026-09-26, May via the coordinator): `research/nocsd-gaps/`.
- (a) now covers inserted action groups: 10 dead items to 0.
- New part (d): late menus, live changes, shown menu buttons (Pinta,
  Papers, Console, Nautilus).
- GTK3, button hiding and per-window menus estimated only.
- Gir.Core apps do not trigger the types bug.
- gtk-nocsd main crashes Epiphany (not ours, not reported).
- Five-commit series on branch `split-parts-2` in `~/work/b/nocsd-up/split`
  (local); nothing sent. target2 rolled back to Clean-2 (checked inside).

**gtk-nocsd is B's as a whole since 2026-09-26** (May, via the coordinator):
- the package (`packages/gtk-nocsd`, branch `unity/resolute`, handed over by A);
- the global menu patch (`research/nocsd-upstream/`, `nocsd-reply2/`,
  `nocsd-gaps/`);
- the upstream findings. Epiphany aborts on main when opening Passwords:
  first bad commit 8f076dd, reproducer and fix in
  `research/nocsd-epiphany-crash/`, not sent.

Our aptly carries 4.8, which is not affected.
`4.8-1+unity2` adds `/etc/X11/Xsession.d/51gtk-nocsd`, so Xfce and other
Xsession sessions load it. It is in aptly, and branch `unity/resolute` is
pushed. Build in `~/work/b/nocsd-u2`.

**Issue #1, second reply - measurements done** (2026-09-25, May via the
coordinator): `research/nocsd-reply2/` (holder vs flat on Unity and Plasma,
44-application audit, GTK3, the patch split into four commits with all
combinations building, two gtk-nocsd findings re-checked). Split branch
`split-parts` in `~/work/b/nocsd-up/split` (local). Report sent to the
coordinator. target2 rolled back to Clean-2 (checked inside).

**Trial rebuild of never-built section-B sources** (2026-09-25): 7 of 9 build;
libindicator FTBFS fixed as `+unity1` (built, not in aptly - equivalent to the
archive's binary), vala-panel FTBFS left alone (not used by Unity).
`research/rebuild-trial/`; `packages/libindicator` branch `unity/resolute`
(git-ubuntu clone, no remote of ours); builds in `~/work/b/rebuild`.
_Correction 2026-09-27 (UNITY-20260927-036):_ libindicator `+unity1` was published afterwards; aptly holds
`+unity1` and `+unity2` (`research/UNITY-20260927-036-record-corrections/logs/01-facts.txt`).

**gtk-nocsd global menu, upstream-ready patch** (2026-09-25, May asked):
one commit on upstream main 6b1f70a, desktop-neutral (gtk-shell-shows-menubar),
upstream style; measured on target2, not sent, not in aptly; point 1 (talk
to the maintainer) waits for May. `research/nocsd-upstream/`; branches
`global-menu` in `~/work/b/nocsd-up/src`, `b/global-menu-up` in
`~/work/b/nocsd-merge/pkg` (local only). Tested in real Xfce 4.20 and Plasma 6.6.4
X11 sessions too (`research/nocsd-desktops/`): works on both once
`gtk-shell-shows-menubar` is set, which neither desktop does by itself.
Earlier round (4.8-based): `research/nocsd-merge/`.

**Re-check per host 02:58Z** (2026-09-25): none of B's fixes is in a newer
release (26.10, Debian, upstream) - all patches stay; DECISIONS 2026-09-25.
Found: indicator-keyboard 0ubuntu4 in 26.10 lost its user unit too (not
reported).

**unity-gtk4-menu 0.9** (2026-09-25): issue #1 - 0.8 recursed to SIGSEGV next
to gtk-nocsd built by upstream `make`; 0.9 uses glibc's `dlsym@GLIBC_2.34`.
In aptly, on target2, checked in the live Unity session (C, gjs, Python,
class actions); `research/nocsd-order/`. Issue #1 not answered (May).
Build in `~/work/b/out09`; gtk-nocsd head in `~/work/b/nocsd-head/`.

**indicator-keyboard +unity2** (2026-09-25): test mock fixed (LP #1968333,
Vala notify emission), tests fatal again, 9/9; in aptly, target2 runs it.
Build in `~/work/b/kbt`.

**indicator-datetime/power/session/sound/keyboard +unity1** (2026-09-25):
FTBFS fixes, branches `unity/resolute`, in aptly; `research/indicator-ftbfs/`.
target2 runs them. Builds in `~/work/b/indf`.

**appmenu-gtk-module 25.04-1build1+unity1** (2026-09-25): upstream a783b01c,
in aptly; `research/appmenu-resident/`. target2 has it (dpkg -i) and
`xsettingsd` installed for the reproduction.
_Correction 2026-09-27 (UNITY-20260927-036):_ that was the state on 2026-09-25; target2 has been
rolled back to Clean-2 since, so it has neither.

**nux 0ubuntu15+unity2** (2026-09-24): `fix-fbo-attachment-arrays.patch`
(LP #2160298), branch `b/fbo` (`9793c23`), in aptly; `research/nux-fbo/`.
target2 runs it. The `b-nux` chroot has +unity2 installed and autotools added.

**indicator-bluetooth, indicator-printers** - agent B's since 2026-09-24.
`+unity1` in aptly (systemd-dev, unit restored); branches `unity/resolute`
in `packages/`, patches in `research/indicator-units/`. target2 has both
installed with `dpkg -i`.

**calamares-settings-ubuntu** - agent B's since 2026-09-24 (known issue #4,
May approved). `1:26.04.12+unity1` in aptly (`-ubuntu-unity`, `-common`,
`-common-data`): basicwallpaper is a desktop window on X11, so it cannot cover
Calamares in the OEM first-time setup. Commit `b6b546b`, branch
`unity/resolute` of `packages/calamares-settings-ubuntu` (no remote of ours -
patch and notes in `research/calamares-oem/`). Confirmed on a real OEM
install in VM `oem-test` (192.168.56.105 by DHCP, MAC 08:00:27:FC:1D:99;
`ssh oemtest` in ~/.ssh/config). Its state now: end-user setup finished,
user `tester` (password omitted from this public status), `oem` removed.
Snapshot `OEM-ready`
(host) is the state before the end user's first boot, `OEM-ready-fixed` the
same with our basicwallpaper; oem-test currently runs `OEM-ready-fixed`'s
first boot. The black screen seen at the OEM-preparation Unity login was
not agent A's gvfs race (its journal, boot -1 on the `OEM-ready` disk: gvfs
started in 1.8 s, never cancelled); it was a slow first start, ~51 s from
autologin to compiz, told to A; the OEM test account and its password are
omitted from this public status. Rotate any test-VM password that appeared in
Git history; deleting it from the current file does not remove old revisions.

**nux** - agent B's since 2026-09-24. `0ubuntu15+unity1` in aptly: upstream
0ubuntu15 (ICU in place of Unicode-licensed code, no boost-system) plus our
`fix-missing-vidmode.patch`; commit `9d26778`, branch `b/ubuntu15` of
`packages/nux` (no remote of ours - patch and notes in
`research/nux-vidmode/`). Unity's unit tests pass on it under plain Xvfb
(agent A). Found: upstream's ICU conversions are broken but unused on Linux.

**unity-gtk4-menu is agent B's package** (handed over by A, 2026-09-24).
Released 0.4-0.9, all in aptly. Open: the architecture question vs gtk-nocsd
(DECISIONS 2026-09-25) waits for May.

Qt global menu: measured, already works (Qt5, Qt6, KDE) - nothing to build.

Proposed next, none started - May decides: whether to report the two
gtk-nocsd findings and nux's broken ICU conversions upstream (on hold).

## State of `target2`

**At `Clean-2`, powered off, since 2026-10-10 18:15Z.** It was rolled back
after the UNITY-20261010-001 publication check. Checked inside: no
`~/.dirty`, no `~/b1010` or `~/b013`, only `ubuntu.sources`, hud 0ubuntu6,
libcolumbus 0ubuntu39, NTP synchronised. (On 2026-10-10 it was found running
since 15:17Z with a GUI session, clean inside, most likely from the signer
deployment; it was restored before use.) Restarts before
measurements: a cold cycle (poweroff over ssh, then start_vm), not a reboot
from inside the guest.

**Rolled back to `Clean-2` again on 2026-09-28 ~14:55Z**, after
UNITY-20260927-024 (unity-greeter, indicator-keyboard stock/+unity3, a test
user). Checked inside: no `~/.dirty`, no `ik024test`, archive
indicator-keyboard 0ubuntu1, greeter back to `lightdm-greeter`.

Earlier: **rolled back to `Clean-2` on 2026-09-25 13:20Z** (host, after the Xfce/KDE
test; checked inside: fresh boot, no `~/.dirty`, archive gtk-nocsd
`3+0~20260321+0b77e1b-1`, no Xfce/Plasma). Everything B had installed there
before is gone: our aptly packages, test applications, `~/b/` scripts. The
scripts that matter are in git (`research/nocsd-order/`,
`research/nocsd-desktops/`, `research/layer-b/`); `~/b/classtest` has to be
rebuilt from `packages/unity-gtk4-menu/tests/classtest.c` before reuse.
No aptly source configured on it.

## Mine outside git

- `/var/tmp/sbuild-claude/b-dev` - now also has libadwaita-1-dev (2026-09-25), Qt6 dev, Xvfb, xfwm4,
  Calamares and our calamares-settings-ubuntu-unity `+unity1`, for
  `research/calamares-oem/check.sh`.
- `~/work/b/iso` - ISO manifest, calamares-settings-ubuntu 26.04.12 source,
  `www/` (bootstrap for `oem-test`, served by tmux `b-www`).
- `/var/tmp/sbuild-claude/b-nux` - chroot with our nux, Xvfb, Xorg dummy and
  TigerVNC, for `research/nux-vidmode/`.
- `~/work/b/nux/` - nux build output and test programs.

- `~/work/b/src/` - yelp 49.0 and gtk4 4.22.4 sources (read-only reference).
- `~/work/b/out/` - 0.4 source and binary packages, sbuild log.
- `/var/tmp/sbuild-claude/b-dev` - dev chroot with `libgtk-4-dev`, entered
  with `sudo unshare --mount --pid --fork chroot`.
