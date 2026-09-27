# Legacy migration 2026-09-27: agent B

One-off PROCESS BOOTSTRAP / HISTORICAL STATE RECONCILIATION of agent B's
work before `docs/ENGINEERING-PROCESS.md`. Read-only: no package code
changed, nothing built for publication, nothing published, no VM restored,
no task created. Written by agent B (registered in
`~/coordinator/AGENT-REGISTRY.json` 2026-09-27 16:23Z).

## Method

- Scope: C's list for B (nux, unity-gtk4-menu, the indicators,
  libindicator, libunity, appmenu-gtk-module, calamares-settings-ubuntu with
  oem-test, hud, overlay-scrollbar, ubuntu-unity-meta, unity-lens-files, the
  seven scopes, gtk-nocsd, findings outside aptly, git-ubuntu clones) plus
  what the collectors found in the same areas.
- Five read-only collector subagents (G1 nux/unity-gtk4-menu/calamares,
  G2 indicators/libindicator, G3 libunity/appmenu/hud/meta/scopes,
  G4 gtk-nocsd, G5 findings/exports/work dirs) worked from the repository,
  `~/AGENTS-LOG.md`, `/srv/aptly`, `~/work/b` and the coordinator snapshot
  `~/coordinator/migration-20260927/`. Their command legends are kept in the
  appendix; each entry keeps the collector's ID ("collected as Gn-NN") so
  cross-references inside entries still resolve.
- B then reviewed every proposed result, re-checked the sharpest claims
  personally (below), and changed results where a rule was applied
  inconsistently (marked "[B's review]").
- Source↔aptly means: the aptly `.dsc` (or, where aptly holds no source, the
  `.dsc` sbuild consumed) unpacked and compared with `git archive <commit>`
  or with the committed debdiff, plus sha256 of every published `.deb`
  against B's build directory.

Labels: **HISTORICAL_FACT** (cited record or commit), **CURRENTLY_VERIFIED**
(checked 2026-09-27, command given), **UNVERIFIED**.

Personally re-checked by B on 2026-09-27 [CURRENTLY_VERIFIED]:
- `git -C packages/calamares-settings-ubuntu show --stat b6b546b`:
  `debian/changelog | 1496 +---`; the file went from 1491 lines
  (`b6b546b~1`) to 11 lines.
- `git -C packages/unity-gtk4-menu ls-remote --tags origin`: annotated tag
  `0.9` peels to `b6251537…` (the 0.8 commit); 0.9 is `7ce9092`.
- `nm -D --defined-only` on `libindicator3.so.7` from
  `~/work/b/li2/out/libindicator3-7_…0ubuntu8+unity2_amd64.deb`: 41 symbols,
  including the new `indicator_ng_ayatana_menu_get_type` (+unity1: 40, per
  `research/rebuild-loss/`).
- vbox `list_snapshots oem-test`: `OEM-ready`, `OEM-ready-fixed` (the latter
  "basicwallpaper … swapped in from a live session"), current
  `OEM-ready-fixed`; `list_snapshots target-desktop-2`: `Clean-2` only.
- `ssh target2`: no `~/.dirty`, only `ubuntu.sources` (clean).

## Result rules used

- **SUPERSEDED**: replaced by a later published version or approach of ours.
- **LEGACY_VERIFIED**: the historical evidence is complete and consistent,
  and source↔aptly (or, for a finding, the recorded state) was checked now.
  It still has the provenance gap below; it does not mean the item passes
  the new gates.
- **LEGACY_PARTIAL**: done, but part of the evidence, record, source package
  or export is missing or inconsistent.
- **REQUIRES_REVALIDATION**: root cause, correct layer, test or target
  verification is doubtful or missing for a behaviour change.
- A source that exists only as an export in `docs/package-patches-b/` (a
  git-ubuntu clone with no remote of ours) is a provenance gap, not by itself
  a reason for PARTIAL.

## Summary

57 items: LEGACY_VERIFIED 19, LEGACY_PARTIAL 17, SUPERSEDED 14, REQUIRES_REVALIDATION 7.

- LEGACY_VERIFIED: B-L10, B-L11, B-L12, B-L22, B-L24, B-L25, B-L26, B-L28, B-L29, B-L31, B-L43, B-L46, B-L48, B-L49, B-L50, B-L51, B-L53, B-L55, B-L56
- LEGACY_PARTIAL: B-L03, B-L04, B-L06, B-L08, B-L09, B-L14, B-L18, B-L19, B-L23, B-L27, B-L37, B-L39, B-L40, B-L41, B-L42, B-L45, B-L57
- SUPERSEDED: B-L01, B-L02, B-L05, B-L13, B-L15, B-L16, B-L20, B-L32, B-L34, B-L35, B-L36, B-L38, B-L44, B-L52
- REQUIRES_REVALIDATION: B-L07, B-L17, B-L21, B-L30, B-L33, B-L47, B-L54

| legacy_id | item | migration_result |
|---|---|---|
| B-L01 | nux: XF86VidMode crash fix | SUPERSEDED |
| B-L02 | nux: rebase onto upstream 0ubuntu15 (0ubuntu15+unity1) + ICU finding | SUPERSEDED |
| B-L03 | nux: FBO colour-attachment vectors | LEGACY_PARTIAL |
| B-L04 | nux: PCRE2 reproducer re-check (B-5 point 4), prep only | LEGACY_PARTIAL |
| B-L05 | unity-gtk4-menu 0.4–0.8 | SUPERSEDED |
| B-L06 | unity-gtk4-menu 0.9: issue #1 recursion fix | LEGACY_PARTIAL |
| B-L07 | calamares-settings-ubuntu: basicwallpaper over Calamares in OEM setup, 1:26.04.12+unity1 | REQUIRES_REVALIDATION |
| B-L08 | indicator-bluetooth: restore systemd user unit | LEGACY_PARTIAL |
| B-L09 | indicator-printers: restore systemd user unit | LEGACY_PARTIAL |
| B-L10 | indicator-session: FTBFS fix, CMake 4 | LEGACY_VERIFIED |
| B-L11 | indicator-power: FTBFS fix, CMake 4 + GCC 15 | LEGACY_VERIFIED |
| B-L12 | indicator-sound: FTBFS fix cherry-picked from 26.10 0ubuntu10 | LEGACY_VERIFIED |
| B-L13 | indicator-datetime: FTBFS fix | SUPERSEDED |
| B-L14 | indicator-datetime: VTODO without DTSTART placed at DUE | LEGACY_PARTIAL |
| B-L15 | indicator-keyboard: build fix lightdm-vala + systemd-dev | SUPERSEDED |
| B-L16 | indicator-keyboard: test mock notify fix, tests fatal | SUPERSEDED |
| B-L17 | indicator-keyboard: NULL InputSources guard | REQUIRES_REVALIDATION |
| B-L18 | indicator-messages: no-change backport of 26.10 0ubuntu8 as 0ubuntu8~26.04.1 | LEGACY_PARTIAL |
| B-L19 | ayatana-indicator-messages: link indicator into /usr/share/unity/indicators | LEGACY_PARTIAL |
| B-L20 | libindicator: build fix systemd-dev, keep indicators-pre.target | SUPERSEDED |
| B-L21 | libindicator: accept Ayatana indicators on Unity's panel, GMenuModel wrapper | REQUIRES_REVALIDATION |
| B-L22 | libunity: Python scope runner without `imp` | LEGACY_VERIFIED |
| B-L23 | appmenu-gtk-module: make the GTK3 module resident | LEGACY_PARTIAL |
| B-L24 | hud: FTBFS fixes | LEGACY_VERIFIED |
| B-L25 | overlay-scrollbar: stub package, remove 81overlay-scrollbar | LEGACY_VERIFIED |
| B-L26 | ubuntu-unity-meta: 0.29+unity1 | LEGACY_VERIFIED |
| B-L27 | unity-lens-files: 7.1.0+17.10.20170605-0ubuntu6+unity1 | LEGACY_PARTIAL |
| B-L28 | unity-scope-{calculator,devhelp,tomboy,virtualbox,zotero}: drop shared dist-packages/__init__.p | LEGACY_VERIFIED |
| B-L29 | unity-scope-manpages: __init__.py + `gi.require_version('Gtk', '3.0')` | LEGACY_VERIFIED |
| B-L30 | unity-scope-gnote: __init__.py + 3 s retry while Gnote activates | REQUIRES_REVALIDATION |
| B-L31 | session-migration: B's debdiff | LEGACY_VERIFIED |
| B-L32 | gtk-nocsd: 4.8-1+unity2, /etc/X11/Xsession.d/51gtk-nocsd for Xsession-started desktops | SUPERSEDED |
| B-L33 | gtk-nocsd: 4.8-1+unity3, 51gtk-nocsd seeds LD_PRELOAD from the systemd user manager | REQUIRES_REVALIDATION |
| B-L34 | gtk-nocsd: unity-gtk4-menu merged into gtk-nocsd 4.8 | SUPERSEDED |
| B-L35 | gtk-nocsd: global menu as upstream patch on main 6b1f70a | SUPERSEDED |
| B-L36 | gtk-nocsd: split-parts | SUPERSEDED |
| B-L37 | gtk-nocsd: split-parts-2 | LEGACY_PARTIAL |
| B-L38 | gtk-nocsd: exp-flat | SUPERSEDED |
| B-L39 | gtk-nocsd upstream: Epiphany Passwords abort on main (first bad 8f076dd) + fix | LEGACY_PARTIAL |
| B-L40 | gtk-nocsd upstream: other findings | LEGACY_PARTIAL |
| B-L41 | gtk-nocsd (Debian packaging): environment.d does not reach Xfce | LEGACY_PARTIAL |
| B-L42 | gtk-nocsd: issue #1 | LEGACY_PARTIAL |
| B-L43 | vala-panel: FTBFS in resolute, left alone | LEGACY_VERIFIED |
| B-L44 | overlay-scrollbar: "dead" | SUPERSEDED |
| B-L45 | hud / LibreOffice: intermittent empty HUD | LEGACY_PARTIAL |
| B-L46 | appmenu: GTK2 applications have no global menu | LEGACY_VERIFIED |
| B-L47 | unity-scope-home: new scope unused until next login | REQUIRES_REVALIDATION |
| B-L48 | nux: upstream ICU conversions broken, unreached on Linux | LEGACY_VERIFIED |
| B-L49 | unity-scope-launchpad: not rebuilt, broken `Exec=/usr/bin/python` | LEGACY_VERIFIED |
| B-L50 | unity-lens-photos: facebook/flickr Soup 2.4 vs 3.0 ImportError | LEGACY_VERIFIED |
| B-L51 | misc scope findings: files-lens locate, SyntaxWarnings, yahoostock feedparser | LEGACY_VERIFIED |
| B-L52 | Canonical indicator-messages: double start | SUPERSEDED |
| B-L53 | Vala codegen bug (detailed notify emission) and LP #1968333 fix: not reported | LEGACY_VERIFIED |
| B-L54 | indicator-keyboard 0ubuntu4 in 26.10 lost its user unit | REQUIRES_REVALIDATION |
| B-L55 | appmenu-gtk-module: GIMP segfault on module drop | LEGACY_VERIFIED |
| B-L56 | rebuild-trial / rebuild-loss survey results | LEGACY_VERIFIED |
| B-L57 | gtk-nocsd global menu under Xfce/Plasma | LEGACY_PARTIAL |

## Provenance gap (all published items)

Every item B published was published under the old process: no build
manifest, no release gate, no version-safety record, no aptly snapshot
(`aptly snapshot list`: none), no §2 evidence card, no independent
verifier; `aptly publish list` shows `./resolute [amd64]` with no source
index [CURRENTLY_VERIFIED]. On top of that:

- **Source commit not on any remote of ours** (only on builder; the export or
  debdiff in the pushed meta-repo is the only copy): nux `9793c23`/`9d26778`/
  `be561f9` (B-L01..03), calamares `b6b546b` (B-L07; export in
  `research/calamares-oem/`, not in `package-patches-b/`), all indicator
  and libindicator/libunity/appmenu clones (B-L08..L23), gtk-nocsd branches
  `split-parts*`, `exp-flat`, `global-menu*`, `fix-dialog-title` (B-L34..L39).
- **No git tree at all** (debdiff only): hud, overlay-scrollbar,
  ubuntu-unity-meta, unity-lens-files, seven scopes, ayatana-indicator-messages.
- **No source package in aptly**: nux, unity-gtk4-menu, calamares,
  indicator-bluetooth, indicator-printers, appmenu-gtk-module,
  session-migration (A's publication); gtk-nocsd +unity2 dbgsym missing.
- **Published source is a regeneration**: unity-lens-files source was
  rebuilt from the debdiff after the binary build (B-L27).
- **Built from a working tree before the commit existed**: indicator-datetime
  +unity2, indicator-keyboard +unity3, libindicator +unity2 (trees match now).
- **Target check by `dpkg -i`, not the repository upgrade path**: nux
  (all three), unity-gtk4-menu 0.4–0.9, gtk-nocsd +unity3 (B-L33), the
  calamares fix on oem-test (binary swapped in). overlay-scrollbar, the
  meta and hud were checked through `apt full-upgrade` from our aptly.
- **No AGENTS-LOG START line** before publishing in B-11 and B-12
  (overlay-scrollbar, meta, hud, gtk-nocsd +unity3): only DONE lines.
- **Mislabelled pushed tag**: unity-gtk4-menu `0.9` → 0.8 commit (B-L06).
- **Superseded versions still in aptly**: nux 0ubuntu13+unity1,
  15+unity1; unity-gtk4-menu 0.3–0.8; datetime/keyboard/libindicator
  +unity1/2; gtk-nocsd +unity2. Orphaned pool files: unity-gtk4-menu
  0.1/0.2 `.deb`s outside the repo.

## Unfinished work (each needs a new UNITY-* task ID from C if pursued)

1. calamares-settings-ubuntu: restore the full `debian/changelog` (a
   packaging defect of ours, shipped in the published `.deb`), then
   revalidate the fix (B-L07). Also open from the record: no keyboard
   focus on cold boot, sudoers.oem chmod slip, greeter choice after OEM.
2. gtk-nocsd +unity3: verify through the normal upgrade path on a clean
   target (Unity with unity-gtk4-menu; a full Xfce), and cover the
   non-empty-`LD_PRELOAD` path, which still overwrites (B-L33).
3. libindicator +unity2: Design Challenger / ABI review; decide on the new
   exported symbol (B-L21).
4. indicator-keyboard +unity3: establish why AccountsService leaves
   `InputSources` NULL on a loaded user and which layer owns it (B-L17).
5. unity-scope-gnote: trace Gnote's registration order; decide whether the
   consumer retry stays (B-L30).
6. hud / LibreOffice empty HUD: window-stack-bridge drops a window when
   bamf's application is not exported yet; the second mechanism (window
   known, GMenu empty) is untraced (B-L45; also `QFileInfo::baseName`
   app id `org`).
7. unity-gtk4-menu: move tag `0.9` to `7ce9092` (B-L06); A's target still
   runs 0.8.
8. indicator-bluetooth/-printers, appmenu-gtk-module: get the source
   package into aptly or republish through the §6 flow (B-L08, B-L09,
   B-L23).
9. gtk-nocsd upstream (May's decision, via C-L01): rebase `split-parts-2`
   and the Epiphany fix (`2cfc8f1`) on current main (`e817d80`, moved from
   `6b1f70a`) and recheck the "types never fetched" bug (B-L37, B-L39,
   B-L40).
10. aptly hygiene (with A/C): first gated snapshot; retire superseded
    versions, the source-less gtk-nocsd `3+0~…+unity2` binaries (A's) and
    orphaned pool files.
11. Record corrections (docs only): `PATCHES.md:64` and
    `status/B.md:125` still say libindicator +unity1 is not in aptly;
    `research/indicator-units/README.md:41` says "in aptly" (binaries only);
    `research/rebuild-loss/README.md:33,35` (hud row, "overlay-scrollbar
    deleted from resolute" — rmadison shows it in resolute and stonking);
    `status/B.md:56-57,160-161`, `research/unity-scopes/README.md:91-92`
    stale; `package-patches-b/README.md` misses indicator-messages
    (base `origin/ubuntu/stonking`) and calamares; unity-lens-files has no
    PATCHES row.

## Doubtful fixes (§2 correct_layer, §4, §5 finding values)

- **indicator-keyboard +unity3, NULL InputSources (B-L17)** —
  ROOT_CAUSE_UNPROVEN. The record asserts AccountsService "documents" the
  NULL without a source; the inconsistent state (user `is-loaded`, property
  gone) comes from AccountsService, and the guard sits at the consumer.
  With NULL, `migrate_input_sources()` still writes the greeter's settings;
  nothing shows the layouts recover when accounts-daemon returns. The
  LightDM user-name guard has no test.
- **indicator-datetime +unity2 (B-L14)** — main change (a VTODO without
  DTSTART placed at DUE) is at the producer and has a fail-before/pass-after
  test: sound. The added skip of components without a time is a defensive
  backstop the range query never reaches: untested, PATCH_TOO_BROAD
  (minor). The `g_debug` guard is redundant.
- **libindicator +unity2 (B-L21)** — shared-library behaviour change
  without a Design Challenger; unintended new exported symbol (no
  `.symbols` file caught it); the action-name fallbacks apply to every
  indicator, not only Ayatana ones as the record says; implementer-only
  manual verification.
- **gtk-nocsd +unity3 (B-L33)** — mechanism proven and our script is the
  right package, but the fix only runs when the session `LD_PRELOAD` is
  empty (FIX_PARTIAL for the non-empty case); simulation script not
  committed; target check by `dpkg -i`. +unity2 (B-L32) itself shipped a
  regression because its Unity check ran without unity-gtk4-menu.
- **unity-scope-gnote (B-L30)** — ROOT_CAUSE_UNPROVEN: a 3 s retry at the
  consumer; Gnote's late registration was not traced in Gnote.
- **calamares (B-L07)** — fix narrow and measured, but the commit also
  replaced the whole `debian/changelog` (PATCH_TOO_BROAD, packaging).
- **nux vidmode patch (carried in B-L03)** — two hunks for a double free
  "found by reading", never reproduced (PATCH_TOO_BROAD); the FBO fix has
  an out-of-tree regression program only.
- **hud (B-L24)** — `-std=c++17` is set for the whole project, not only the
  tests (broader than needed; file lists and symbols equal the archive's).
- **ubuntu-unity-meta (B-L26)**, **unity-scope-manpages (B-L29)** — two
  changes in one upload (§4 "one defect per patch"); both measured.
- **unity-scope-home relogin finding (B-L47)** — the mechanism is stated,
  not evidenced.

## Items attributed to others (not counted)

- unity-gtk4-menu 0.1–0.3: A's (before B existed; B took over at 0.3).
- gtk-nocsd `0~20260321+0b77e1b-1+unity2` and `4.8-1+unity1`: A's
  (the latter handed to B).
- nux `Validator::Validate` finding, `research/recheck-2026-09-26/`: A's.
- `packages/unity-scope-home`, `packages/unity-indicators`: reference
  clones, no local commits; B's rebuild trial used the archive `.dsc`.
- session-migration: B prepared the debdiff (B-L31, B's part only); A
  built and published.
- Items B has that C's list did not name: nux PCRE2 reproducer re-check
  (B-L04), gtk-nocsd global menu under Xfce/Plasma (B-L57), the rebuild
  survey (B-L56), the Vala codegen / LP #1968333 upstream items (B-L53),
  B's 2026-09-25 re-check of the 26.10 archive (B-L54).

## Entries

### B-L01 — nux: XF86VidMode crash fix (0ubuntu13+unity1)
- legacy_id: B-L01 (collected as G1-01)
- package: nux [HISTORICAL_FACT: LOG:87-98]
- goal: stop SIGSEGV in `GraphicsDisplay::CreateOpenGLWindow` (`GraphicsDisplayX11.cpp:296-297`) when the X server has no XFree86-VidModeExtension (Xvfb, Xvnc), so Unity's unit tests run under plain Xvfb. Unity itself stated not affected. [HISTORICAL_FACT: research/nux-vidmode/README.md:9-41]
- commits/branches: `be561f92002cdb9f0feace21b8527e9f29bbfc08`, branch `b/vidmode` of UD/packages/nux, parent `3c56e898d112e9ec4e7212d78a548bab82e60079` (upstream 0ubuntu13, contained in origin/ubuntu/devel). NOT pushed: origin is gitlab.com/ubuntu-unity/unity/nux (not ours); no remote ref contains it. [CURRENTLY_VERIFIED: `git rev-parse be561f9`; `git branch -a --contains be561f9` -> only local `b/vidmode`,`b/ubuntu15`,`b/fbo`; `git ls-remote origin | grep be561f9` -> nothing]. Patch copy `docs/research/nux-vidmode/fix-missing-vidmode.patch` byte-identical to `git show be561f9:debian/patches/fix-missing-vidmode.patch` [CURRENTLY_VERIFIED: `diff` -> identical]. Not in package-patches-b/nux (that export starts at 2c1878a, i.e. only the ubuntu15 line). [CURRENTLY_VERIFIED: UD/docs/package-patches-b/README.md nux row]
- versions: source `4.0.8+18.10.20180623-0ubuntu13+unity1` (format 1.0 native tarball); binaries libnux-4.0-0, libnux-4.0-common, libnux-4.0-dev, nux-tools same version. [CURRENTLY_VERIFIED: ~/work/b/nux/out/nux_*.dsc]
- build_state: sbuild ok after one abort (changelog date). [HISTORICAL_FACT: LOG:91-94; ~/work/b/nux/out/sbuild.log `EXIT=0`]
- test_state: nux suites 130/9/18/113 pass at build; vidmode.cpp SIGSEGV before / window after on Xvfb and Xtigervnc; Xorg-dummy unchanged; agent A: TestGnomeSessionManager 51/51, TestSessionController 20/20 under plain Xvfb with this libnux via dpkg -i (Unity binaries not rebuilt). Double-free part "not reproduced". [HISTORICAL_FACT: research/nux-vidmode/README.md:25-31,64-83]
- target_state: target2 `dpkg -i` + reboot, Dash/HUD work. target2 later rolled back to Clean-2 (2026-09-25 13:20Z). [HISTORICAL_FACT: LOG:95; SB (State of target2 section)]
- aptly_state: 0ubuntu13+unity1 present for all 4 binaries (still published, superseded). Also present: plain `0ubuntu13` (not B's: A's unmodified upstream build, DEC:256 "nux -0ubuntu13 verified on target", PAT:49). [CURRENTLY_VERIFIED: `aptly repo search unity-resolute 'Name (libnux-4.0-0) | Name (nux-tools)'`]
- source↔aptly: MATCH — local .dsc tree == `git archive be561f9` (0 differences); all 4 .debs sha256-identical to pool. [CURRENTLY_VERIFIED: `dpkg-source -x --no-check ~/work/b/nux/out/nux_...13+unity1.dsc`; `diff -rq`; `sha256sum` vs `find /srv/aptly/pool -name '*_<deb>'`]
- records: research/nux-vidmode/README.md (whole); PAT:29; DEC:607-625 (A's harness finding that motivated it), DEC:858; STATUS.md:250-253; SB:191-196. No DEC heading of its own. [CURRENTLY_VERIFIED: grep]
- current_state: superseded by 0ubuntu15+unity1 then +unity2, which carry the same patch unchanged. [CURRENTLY_VERIFIED: `diff <(git show 9d26778:debian/patches/fix-missing-vidmode.patch) <(git show be561f9:...)` -> identical]
- gaps_unknowns: "Unity itself is not affected" rests on code reading (`CreateFromForeignWindow` path) and no full Unity-under-Xvnc run. [HISTORICAL_FACT: research/nux-vidmode/README.md:33-40]
- provenance_gap: old process — no build manifest, release gate, version-safety record, aptly snapshot; source not pushed to any git remote of ours (patch copy only in meta-repo); no .dsc in aptly; target install was dpkg -i. [CURRENTLY_VERIFIED as above]
- unfinished: upstream submission on hold (May). [HISTORICAL_FACT: research/nux-vidmode/README.md "Not done"]
- doubtful_fix: root cause proven (gdb frame 0 in CreateOpenGLWindow, before/after table). No regression test added to nux's suite; proof is an out-of-tree program (vidmode.cpp). Patch is broader than the proven defect: it also NULLs the list after the fullscreen-path XFree and frees an old list before re-query — both "found by reading", double free not reproduced (EP §4 "one underlying defect per patch"). It also removes the unconditional `XF86VidModeQueryVersion` call. Independent check by agent A was of Unity's tests running, not of the patch's extra hunks. [HISTORICAL_FACT: fix-missing-vidmode.patch header; README.md:48-55]
- proposed migration_result: SUPERSEDED — replaced by published 0ubuntu15+unity2 (G1-03), which carries the patch; its doubts transfer to G1-03.

### B-L02 — nux: rebase onto upstream 0ubuntu15 (0ubuntu15+unity1) + ICU finding
- legacy_id: B-L02 (collected as G1-02)
- package: nux [HISTORICAL_FACT: LOG:100-109]
- goal: move to upstream 0ubuntu15 (0ubuntu14 LP #2147049 ICU replacement of Unicode-licensed code; 0ubuntu15 drops libboost-system-dev) and carry fix-missing-vidmode.patch. [HISTORICAL_FACT: research/nux-vidmode/README.md "Rebased onto upstream 0ubuntu15"]
- commits/branches: `9d267784c8c3e6634633a8e4f2c8019be8561de9`, branch `b/ubuntu15`, parent `2c1878a8dae9c63ccc1efb9fad0943d14fe782a6` (= origin/ubuntu/devel). Not pushed (no remote ref contains it). Exported as UD/docs/package-patches-b/nux/0001-Rebase-onto-upstream-0ubuntu15-carry-fix-missing-vid.patch; `git format-patch 2c1878a..b/fbo --stdout` equals the concatenated 0001+0002 exports except the leading `From <hash>` lines and one blank separator line from concatenation. [CURRENTLY_VERIFIED: `git ls-remote origin`; `diff` of format-patch vs exports]
- versions: source/binaries `4.0.8+18.10.20180623-0ubuntu15+unity1` (4 binaries). [CURRENTLY_VERIFIED: ~/work/b/nux/out15]
- build_state: 1st sbuild segfaulted in GL test `EmbeddedContextMultiWindow.ForeignFrameEndedPresentNone`; 2nd identical source passed; declared flaky, not investigated. Logs ~/work/b/nux/out15/attempt1/. [HISTORICAL_FACT: LOG:103-104; README "Verified"; CURRENTLY_VERIFIED: attempt1 dir exists]
- test_state: suites 130/9/18/113 on 2nd attempt; ABI: libnux-core loses `nux::tr_utf8_validate`, `nux::isLegalUTF8Sequence` with same SONAME; B checked nm -D of unity/compiz/u-s-d on target2, A checked 86 ELF files — no importers; A: Unity tests 51/51, 20/20 (after discarding two runs that were actually on 0ubuntu13). [HISTORICAL_FACT: research/nux-vidmode/README.md ABI + agent A sections]
- target_state: target2 dpkg -i + reboot, Dash/HUD Cyrillic checks. [HISTORICAL_FACT: LOG:105; README "Verified"]
- aptly_state: 0ubuntu15+unity1 present (4 binaries). [CURRENTLY_VERIFIED: aptly repo search]
- source↔aptly: MATCH — .dsc tree == `git archive 9d26778`; 4 .debs sha256-identical. [CURRENTLY_VERIFIED: same method]
- records: research/nux-vidmode/README.md second half; PAT:29; SB:191-196; DEC:1050-1060 (re-check). [CURRENTLY_VERIFIED: grep]
- current_state: superseded by +unity2 (built on top of 9d26778). [CURRENTLY_VERIFIED: `git log --format='%H %P' -1 b/fbo`]
- gaps_unknowns: flaky GL test not investigated; ABI symbol removal with unchanged SONAME accepted by rdepends scan only; "Typing loses characters at 200 ms" not compared on old nux. [HISTORICAL_FACT: README "Verified"]
- provenance_gap: as G1-01; plus the upstream rebase is not our change but ships under our +unity suffix with a symbol removal and no Design Challenger record (EP §2 "package version / ABI" choice). [CURRENTLY_VERIFIED: no DEC heading for the rebase — `grep -n '^## ' DEC | grep -i nux` shows only 2026-09-22 entries]
- unfinished: **nux ICU finding** — upstream `icu_conversions.cpp` ConvertUTF8toUTF32/32toUTF8 wrong (length off by one, capacity units, pointers not advanced, BOM/endianness); stated unreached on Linux by code reading; not fixed, not reported (upstream on hold). Needs a new task ID if pursued. [HISTORICAL_FACT: research/nux-vidmode/README.md "The ICU replacement is broken"; SB:196,205; research/nux-vidmode/utfconv.cpp]
- doubtful_fix: no new fix of ours in this version beyond G1-01's patch. The "ICU unused on Linux" claim is code reading (`TCHARToUTF8` identity under `#ifndef _UNICODE`), not measured on a running Unity. [HISTORICAL_FACT: README]
- proposed migration_result: SUPERSEDED — replaced by published 0ubuntu15+unity2; ICU finding to be carried as an open item.

### B-L03 — nux: FBO colour-attachment vectors (LP #2160298), 0ubuntu15+unity2 (current)
- legacy_id: B-L03 (collected as G1-03)
- package: nux [HISTORICAL_FACT: LOG:160-171]
- goal: `FormatFrameBufferObject()` `clear()`s `texture_attachment_array_`/`surface_attachment_array_` right after `SetupFrameBufferObject()` sized them; later calls index empty vectors (UB, abort under `_GLIBCXX_ASSERTIONS`, attachment ref leak). Fix: reset elements to null ObjectPtr instead of clear(). [HISTORICAL_FACT: research/nux-fbo/README.md:13-26,45-52]
- commits/branches: `9793c2329dd99f0fe779c51409a79f2c4ab077cc`, branch `b/fbo` (checked-out HEAD), parent `9d26778…` (G1-02). Not pushed (no gitlab ref contains it). Export UD/docs/package-patches-b/nux/0002-Keep-the-FBO-colour-attachment-vectors-sized-LP-2160.patch matches format-patch (see G1-02). research/nux-fbo/fix-fbo-attachment-arrays.patch identical to `git show 9793c23:debian/patches/fix-fbo-attachment-arrays.patch`. [CURRENTLY_VERIFIED: `git rev-parse`, `git ls-remote origin`, `diff`]
- versions: source/binaries `4.0.8+18.10.20180623-0ubuntu15+unity2` (libnux-4.0-0, -common, -dev, nux-tools). [CURRENTLY_VERIFIED: ~/work/b/nux/outu2]
- build_state: sbuild ok (first start failed on host-side clean; restarted with --no-clean-source). [HISTORICAL_FACT: LOG:163-167; CURRENTLY_VERIFIED: outu2/sbuild.log `EXIT=0`]
- test_state: suites 130/9/18/113; exported symbols identical to +unity1; fbo.cpp: tree with `-D_GLIBCXX_ASSERTIONS` aborts in SetTextureAttachment before fix, runs after; package +unity1 refcount 1->2->2 (leak), +unity2 1->2->1; agent A: Unity TestGnomeSessionManager 51/51, TestSessionController 20/20 against +unity2 (old test binaries). Leak frequency in real Unity not measured. [HISTORICAL_FACT: research/nux-fbo/README.md:28-43,54-63]
- target_state: target2 dpkg -i + reboot (Dash blur via FBO, HUD); later target2 rolled back. Agent A's clean re-check 2026-09-26 installed nux 0ubuntu15+unity2 via apt full-upgrade on target and walked known issues #1-#6 (not an FBO-specific test). [HISTORICAL_FACT: LOG:167; research/recheck-2026-09-26/README.md:8-12]
- aptly_state: 0ubuntu15+unity2 present, latest of 4 nux versions (0ubuntu13, 13+unity1, 15+unity1, 15+unity2). [CURRENTLY_VERIFIED: `aptly repo search unity-resolute 'Name (libnux-4.0-0) | Name (nux-tools)'`; 04-aptly-latest-by-source.txt:20]
- source↔aptly: MATCH — .dsc tree == `git archive 9793c23` (0 diffs); 4 .debs sha256-identical to pool. (No .dsc in aptly itself.) [CURRENTLY_VERIFIED: same method]
- records: research/nux-fbo/ (README, fbo.cpp, build-with-assertions.sh, run-against-*.sh, patch); PAT:59; STATUS.md:44-47; STACK-HEALTH.md:74; SB:163-165; DEC:1054-1060 (re-check: not fixed elsewhere; MP 508190 unmerged). No DEC heading for the fix itself. [CURRENTLY_VERIFIED: grep]
- current_state: latest published nux; carries fix-missing-vidmode.patch (G1-01) and fix-fbo-attachment-arrays.patch; source only on builder (branch b/fbo) + patch exports in pushed meta-repo. [CURRENTLY_VERIFIED]
- gaps_unknowns: how often Unity leaks via this path not measured; runtime check on target2 was smoke (session, Dash, HUD, no crash reports). [HISTORICAL_FACT: research/nux-fbo/README.md:43,60]
- provenance_gap: old process — no build manifest / release gate / version-safety record / aptly snapshot; commits not on any remote (only format-patch export); no .dsc in aptly; target2 install by dpkg -i. [CURRENTLY_VERIFIED]
- unfinished: upstream (LP #2160298 / MP 508190) on hold; flaky GL test from G1-02 not investigated; ICU finding (G1-02). [HISTORICAL_FACT: PAT:59 "unreviewed"; DEC:1057-1058]
- doubtful_fix: FBO part — root_cause_mechanism proven (assertion abort + refcount leak measured before/after); correct_layer plausible (the function that empties the vectors), and a rejection of the reporter's alternative is recorded (extra GPU query could hit null GpuDevice); no explicit `defensive_workaround_rejected` field. Regression test: out-of-tree fbo.cpp, shown failing before / passing after, NOT added to nux's test suite. Patch is minimal (one hunk). Independent verification: agent A ran Unity's unrelated session tests only; nobody but B ran fbo.cpp. Carried vidmode patch retains G1-01's bundled unreproduced hunks. [HISTORICAL_FACT: research/nux-fbo/README.md; patch]
- proposed migration_result: LEGACY_PARTIAL — source↔aptly MATCH and export verified now, but source commits exist only on builder (no pushed git ref), no in-tree regression test, no independent verifier, and the carried vidmode patch bundles unreproduced changes.

### B-L04 — nux: PCRE2 reproducer re-check (B-5 point 4), prep only
- legacy_id: B-L04 (collected as G1-04)
- package: nux (upstream material in docs/upstream/nux-pcre2, originally A's work) [HISTORICAL_FACT: DEC:127-213; 07-upstream-queue.md:7-12 "nux is B's"]
- goal: re-run the nux-pcre2 upstream reproducer for the upstream queue. [HISTORICAL_FACT: LOG:345; 07-PENDING-MAY.md:46]
- commits/branches: meta-repo `0b34d94fcd43fa9394e1075ca9b2ee4c4a99f80b` (docs/upstream/nux-pcre2/README.md +13), on origin/main. [CURRENTLY_VERIFIED: `git show --stat 0b34d94`; `git branch -a --contains 0b34d94` -> remotes/origin/main]
- versions: n/a (no package built). build/test/target/aptly: n/a. Result recorded: reproducer still fails on resolute 0ubuntu12. [HISTORICAL_FACT: 07-PENDING-MAY.md:55]
- source↔aptly: NOT_CHECKED (no package).
- records: docs/upstream/nux-pcre2/README.md; 07-PENDING-MAY.md:55.
- current_state / unfinished: upstream submission on May's hold. [HISTORICAL_FACT: 07-upstream-queue.md:3-5]
- provenance_gap: n/a (docs only). doubtful_fix: n/a. PAT:40 `Validator::Validate` Windows-branch row ("draft") — authorship not established from records [UNVERIFIED].
- proposed migration_result: LEGACY_PARTIAL — documentation-only prep, pushed; nothing published.

### B-L05 — unity-gtk4-menu 0.4–0.8 (superseded releases)
- legacy_id: B-L05 (collected as G1-06)
- package: unity-gtk4-menu (native, our own project) [HISTORICAL_FACT: SB:198]
- goal per version [HISTORICAL_FACT: git log subjects; DEC headings]:
  - 0.4 `ab811958cb5b248361a1d2bb53e486520ec37959` stand-ins for widget-class actions (DEC:706)
  - 0.5 `c0557df5542669e3a2aac654c2d2202874cc9028` choose the main menu (DEC:739)
  - 0.6 `0ce1eb1fed3708a4ffb46a34395ca849f437c19d` reach gjs/PyGObject via g_module_symbol (DEC:752)
  - 0.7 `4380c4d5061decf6a86510e6b6697cba1fcc9257` stand-ins follow enabled state via interposed setter (DEC:773)
  - 0.8 `b6251537d047537e38958559ae99162f653f3e81` stateful stand-ins for property actions (research/layer-b/README.md:1496)
- commits/branches: all on `main`, which equals GitHub `refs/heads/main` (7ce9092); each is an ancestor, so contained in a pushed ref. Anomaly: annotated tag `0.9` (object 9c1fcb1606d41cd1030848f671f434f5fee3caba, pushed) peels to `b6251537…` = the **0.8** commit, not 0.9. No tags for 0.1–0.8. [CURRENTLY_VERIFIED: `git ls-remote origin`; `git show 0.9`]
- versions: source `unity-gtk4-menu` 0.4…0.8 (3.0 native .tar.xz), binary `libunity-gtk4-menu0` same. Changelog trailer anomaly: 0.7 dated `Thu, 24 Sep 2026 08:30:00 +0000` though committed 05:20Z and published 05:29Z, i.e. later than 0.8's `06:40:00 +0000` (non-monotonic; looks like EEST local time written as +0000). [CURRENTLY_VERIFIED: `git show <c>:debian/changelog | grep -m1 '^ --'`; LOG:58-61]
- build_state: sbuild `Status: successful` for each. [CURRENTLY_VERIFIED: `grep -m1 ^Status ~/work/b/out/unity-gtk4-menu_<v>_amd64.build`]
- test_state: `make check` only asserts the .so has no GTK/GLib NEEDED entry — no behavioural tests. Behaviour verified by B on target2 with breadth runs (17-21 GTK4 apps), classtest.c, screenshots. [CURRENTLY_VERIFIED: UD/packages/unity-gtk4-menu/Makefile:39-46; HISTORICAL_FACT: research/layer-b/README.md sections 1054-1549; ~/work/b/breadth-*.txt]
- target_state: target2 dpkg -i per version (LOG:26,37 …); target2 since rolled back. Agent A's `target` still lists `libunity-gtk4-menu0 0.8` installed. [HISTORICAL_FACT: SB State of target2; status/A.md:23]
- aptly_state: 0.4, 0.5, 0.6, 0.7, 0.8 all still in repo. [CURRENTLY_VERIFIED: aptly repo search]
- source↔aptly: MATCH for each of 0.4–0.8 — local .dsc tree == `git archive <commit>` except `.gitignore` (excluded by dpkg-source default ignores); .deb sha256 identical to pool. [CURRENTLY_VERIFIED: loop over ~/work/b/out/unity-gtk4-menu_<v>.dsc]
- records: research/layer-b/README.md (0.4 @1054, 0.5 @1249, 0.6 @1310, 0.7 @1401, finding-4 correction @1461, 0.8 @1496); DEC:706,739,752,773,800; STATUS.md:224-231; SB:198-199; LOG:21-79. No PAT row (own package). [CURRENTLY_VERIFIED: grep]
- current_state: superseded by 0.9. 0.8 has the issue-#1 recursion next to a gtk-nocsd built without -Bsymbolic-functions (G1-07); not triggered with Ubuntu's gtk-nocsd build. [HISTORICAL_FACT: research/nocsd-order/README.md:25-45]
- gaps_unknowns: 0.7 interposes an exported GTK symbol in every GTK4 process; ABI-risk reasoning recorded (DEC:773-785) but no Design Challenger record. Late-menu placeholder written, not shipped (research/layer-b/late-menu-placeholder.diff). [HISTORICAL_FACT]
- provenance_gap: old process — no manifest / gate / snapshot / version-safety record; no .dsc in aptly (local .dsc only on builder); dpkg -i on target2. Source is pushed. [CURRENTLY_VERIFIED]
- unfinished: none specific beyond 0.9's.
- doubtful_fix: these are feature increments, not defect fixes; EP §2 fields absent. 0.6's "Order is load-bearing" and 0.7's interposition are design choices verified only by B (DEC entries marked "(agent B)"). The 2026-09-23 "works in either load order" claim was later shown false for 0.8 (DEC:1086-1095).
- proposed migration_result: SUPERSEDED — replaced by published 0.9.

### B-L06 — unity-gtk4-menu 0.9: issue #1 recursion fix (current)
- legacy_id: B-L06 (collected as G1-07)
- package: unity-gtk4-menu [HISTORICAL_FACT: LOG:210-220]
- goal: next to gtk-nocsd built by upstream `make` (no -Bsymbolic-functions), `dlsym(RTLD_NEXT,"g_module_symbol")` returned our own function via gtk-nocsd's dlsym override → infinite recursion/SIGSEGV in most GTK4 apps in both preload orders; fix: resolve "next" through glibc's `dlsym@GLIBC_2.34` (`dlvsym(RTLD_DEFAULT,"dlsym","GLIBC_2.34")`) and never call a "next" that is ourselves. [HISTORICAL_FACT: research/nocsd-order/README.md:27-61; commit 7ce9092 message]
- commits/branches: `7ce9092ab1b5c9e5316eb9a9ee31ecbbfa662ecf` on `main` = GitHub `refs/heads/main` (Ubuntu-Unity-LifeSupport/unity-gtk4-menu) — pushed. Tag `0.9` points at the 0.8 commit (see G1-06). [CURRENTLY_VERIFIED: `git ls-remote origin`]
- versions: source `unity-gtk4-menu 0.9`, binary `libunity-gtk4-menu0 0.9`. [CURRENTLY_VERIFIED: ~/work/b/out09]
- build_state: sbuild `Status: successful`; ~/work/b/out09/sbuild-0.9.log is 0 bytes (wrapper log empty; .build log complete). [CURRENTLY_VERIFIED: `grep -m1 ^Status`; `ls -la`]
- test_state: `make check` = NEEDED check only. order-0.8.sh reproduces SIGSEGV (gdb: thousands of `g_module_symbol` frames); order-0.9.sh 10 programs × 5 orders no crash (gjstest rows rc=1 due to invocation, re-run with `gjs -m` alive per README); live Unity session on target2: C/gjs/Python menus and class-action enabled state via classtest over D-Bus. [HISTORICAL_FACT: research/nocsd-order/README.md:30-45,66-110; order-0.9.txt]
- target_state: target2 dpkg -i 0.9 (LOG:217); target2 later rolled back to Clean-2. Agent A's `target` still reports 0.8 installed. [HISTORICAL_FACT: SB State of target2; status/A.md:23]
- aptly_state: 0.9 present; repo holds 0.3–0.9 (7 versions). [CURRENTLY_VERIFIED: aptly repo search; 04-aptly-latest-by-source.txt:27]
- source↔aptly: MATCH — ~/work/b/out09/unity-gtk4-menu_0.9.dsc tree == `git archive 7ce9092` except `.gitignore`; .deb sha256-identical to pool. [CURRENTLY_VERIFIED]
- records: research/nocsd-order/ (README, order-0.8.sh, order-0.9.sh, order-0.9.txt, live.sh, classlive.sh, screenshots); DEC:1086 "0.9: issue #1's crash is real, and ours", DEC:1097, DEC:1122; STATUS.md:224; SB:145-148,198-199. [CURRENTLY_VERIFIED]
- current_state: latest published; architecture question (fold into gtk-nocsd upstream) open, waiting on May; issue #1 unanswered. [HISTORICAL_FACT: SB:147,198-199; DEC:1097-1120]
- gaps_unknowns: Gir.Core raw-dlsym, statically linked GTK4 not covered; gtk-nocsd-first order silently loses gjs/Python menus and nothing enforces the order. [HISTORICAL_FACT: research/nocsd-order/README.md:73-80,112-122; DEC:1110-1112]
- provenance_gap: old process — no manifest / gate / snapshot / version-safety; no .dsc in aptly; mis-pointed pushed tag `0.9`; source is pushed. [CURRENTLY_VERIFIED]
- unfinished: (a) fix/move tag `0.9` (needs a task; do not do here); (b) reply to issue #1 and retire-vs-keep decision vs gtk-nocsd (May); (c) A's target runs 0.8 — needs upgrade or note. [CURRENTLY_VERIFIED / HISTORICAL_FACT]
- doubtful_fix: root_cause_mechanism proven (gdb recursion + build-flag comparison); the second path (RTLD_NEXT counted from gtk-nocsd at -O0) "found by reading, consistent with the table". Correct layer: our shim's "next" lookup — reasonable, since the recursion is in our code. Regression test: out-of-tree order scripts in research, failing on 0.8 and passing on 0.9 — not in the package (`make check` cannot catch it). Change also rewrites README (doc, same commit). Verified only by B. [HISTORICAL_FACT]
- proposed migration_result: LEGACY_PARTIAL — source pushed and source↔aptly MATCH verified now, but pushed tag `0.9` mislabels the 0.8 commit, no in-package regression test, no independent verifier.

### B-L07 — calamares-settings-ubuntu: basicwallpaper over Calamares in OEM setup, 1:26.04.12+unity1 (known issue #4)
- legacy_id: B-L07 (collected as G1-08)
- package: calamares-settings-ubuntu (binaries published: -ubuntu-unity, -common, -common-data; -kubuntu/-lubuntu built, not published) [HISTORICAL_FACT: LOG:113-138; research/calamares-oem/README.md "Fix"]
- goal: in the OEM first-time-setup session (xfwm4 + basicwallpaper + Calamares) basicwallpaper maps a focusable NORMAL+FULLSCREEN window; xfwm4 puts a focused fullscreen window above others → covers Calamares. Fix: on X11 map `_NET_WM_WINDOW_TYPE_DESKTOP`, frameless, stays-on-bottom, no-focus; Wayland path unchanged. [HISTORICAL_FACT: research/calamares-oem/README.md "Cause","Fix"; DEC:863-878]
- commits/branches: `b6b546b1726812d354bdd4ccb35e0c500add2624` on local branch `unity/resolute`, parent `c6997017d2fe72221f91a22646acab3e8caab608` (= origin/ubuntu/resolute, tag ubuntu/1%26.04.12). Only remote is Launchpad ~ubuntu-qt-code (not ours); no remote ref contains b6b546b. Export: UD/docs/research/calamares-oem/0001-basicwallpaper-desktop-window-on-X11-so-it-cannot-co.patch — identical to `git format-patch c699701..unity/resolute --stdout` (ignoring the `From <hash>` line). NOT listed in UD/docs/package-patches-b/README.md (that README claims to cover B's builder-only git-ubuntu clones). [CURRENTLY_VERIFIED: `git ls-remote origin` (no match); `git branch -a --contains b6b546b` -> only local; `diff` -> EXPORT_MATCH]
- versions: source `1:26.04.12+unity1` (3.0 native .tar.xz at UD/packages/calamares-settings-ubuntu_26.04.12+unity1.{dsc,tar.xz}, gitignored); binaries calamares-settings-ubuntu-unity_1:26.04.12+unity1_all, -common_…_amd64, -common-data_…_all. [CURRENTLY_VERIFIED: `ls`, `git check-ignore`, .changes]
- build_state: sbuild successful after one restart with --no-clean-source (host clean needed build-deps). .changes is binary-only (no source in upload). [HISTORICAL_FACT: LOG:118-120; CURRENTLY_VERIFIED: `grep ^Status` = successful; .changes `Architecture: all amd64`]
- test_state: pixel tests in Xvfb on target2 and in b-dev chroot (archive: wallpaper on top at start/Alt+Tab/late map; fixed: Calamares on top); real two-stage OEM install from official ISO in VM oem-test; cold first boots from snapshots: archive 3/3 hide Calamares, fixed 0/2. Fixed binary tested on oem-test by replacing /usr/bin/basicwallpaper (not by installing the package into the ISO). [HISTORICAL_FACT: research/calamares-oem/README.md tables; LOG:129,138; PAT:57]
- target_state: VM `oem-test` — snapshots `OEM-ready` (before end-user first boot) and `OEM-ready-fixed` (same + our basicwallpaper); SB says it was running OEM-ready-fixed's first boot; test account/password deliberately omitted and SB asks to rotate any test-VM password that appeared in git history. VM NOT touched in this reconciliation. target2 had calamares packages installed for Xvfb tests; since rolled back. [HISTORICAL_FACT: SB (calamares paragraph); 07-PENDING-MAY.md:14]
- aptly_state: 1:26.04.12+unity1 present for -ubuntu-unity, -common, -common-data (1 version). [CURRENTLY_VERIFIED: aptly repo search; 04-aptly-latest-by-source.txt:3]
- source↔aptly: MATCH — UD/packages/calamares-settings-ubuntu_26.04.12+unity1.dsc (the file sbuild consumed, build log line 47/4451) tree == `git archive b6b546b` except `.gitignore`; the 3 published .debs sha256-identical to pool. [CURRENTLY_VERIFIED]
- records: research/calamares-oem/ (README, check.sh, oemenv.sh, probe.sh, live.sh, coldrun.sh, coldwatch.sh, reboots.sh, vm-bootstrap.sh, patch); DEC:863 "known issue #4: fix basicwallpaper, not the session script"; DEC:1064 (re-check: 26.10 untouched); PAT:57; SB calamares paragraph; STATUS.md:22. [CURRENTLY_VERIFIED]
- current_state: published; effective only if in the image the vendor installs from (ships inside /etc/calamares/oemconfig.tar.gz) — matters for our ISO, not installed systems. Agent A's 2026-09-26 re-check explicitly did not test #4. [HISTORICAL_FACT: README "Fix" last para; research/recheck-2026-09-26/README.md:27]
- gaps_unknowns: on cold boot with fix, Calamares on top but without keyboard focus until clicked (xfwm4 `_NET_WM_USER_TIME` hypothesis, not established); finished system boots lightdm-gtk-greeter not unity-greeter (not investigated); Makefile `chmod 400` hits Kubuntu's sudoers.oem instead of Ubuntu Unity's (0644 ships) — seen, not fixed; fixed-binary cold runs n=2. [HISTORICAL_FACT: research/calamares-oem/README.md "Seen along the way", "Cold first boot" tail]
- provenance_gap: old process — no manifest / gate / snapshot / version-safety record; commit only on builder (export in pushed meta-repo, but not in package-patches-b index); no .dsc in aptly; OEM validation used a swapped binary, not the package via apt. [CURRENTLY_VERIFIED]
- unfinished: restore full debian/changelog (rebuild as +unity2); keyboard-focus-on-cold-boot; sudoers.oem chmod slip; greeter choice after OEM; upstream on hold; add calamares row to package-patches-b README; oem-test password rotation note (07-PENDING-MAY.md:14). Each needs a task ID. [HISTORICAL_FACT]
- doubtful_fix: root_cause_mechanism measured (window type/state via xprop, focus timeline by uptime, archive vs fixed); correct_layer argued (fix the window, not reorder the session script, since Alt+Tab still raises it — DEC:865-870), which covers defensive_workaround_rejected in substance. No regression test in package (no test seam); check.sh pixel test is out-of-tree, fail-before/pass-after shown. Code change narrow (common/basicwallpaper/main.cpp 18 lines, X11 branch only), BUT the commit also replaced the whole `debian/changelog`: 1491 lines of archive history -> 11 lines (only the +unity1 entry); diffstat `debian/changelog | 1496 +---`, 24 insertions / 1490 deletions. The published `calamares-settings-ubuntu-unity` .deb ships `/usr/share/doc/.../changelog.gz` with 1 entry (10 lines). This is a packaging defect far broader than the fix and contradicts the README's framing ("on top of c699701, byte for byte the archive's 26.04.12"); not mentioned in any record. [CURRENTLY_VERIFIED: `git show --stat b6b546b`; `git show c699701:debian/changelog | wc -l` = 1491; `git show b6b546b:debian/changelog | wc -l` = 11; `dpkg-deb -x <pool deb>`; `zcat .../changelog.gz | grep -c '^calamares-settings-ubuntu ('` = 1]. Verified only by B. Small n on cold boots (2 fixed runs).
- proposed migration_result: REQUIRES_REVALIDATION — functional evidence for the basicwallpaper fix is strong and source↔aptly MATCH, but the published source/binaries carry a truncated debian/changelog (archive history deleted, unrecorded), the commit exists only on builder, and nobody but B verified it; needs a corrected rebuild (+unity2) under the new process.

### B-L08 — indicator-bluetooth: restore systemd user unit (+unity1)
- legacy_id: B-L08 (collected as G2-01)
- package: indicator-bluetooth
- goal: Build-Depends systemd → systemd-dev so `/usr/lib/systemd/user/indicator-bluetooth.service` is installed again [HISTORICAL_FACT: research/indicator-units/README.md:21-30,34-38]
- commits/branches: `a373dcf20f7620cf46d97950a68593448a5819f9` on `unity/resolute`; base `origin/ubuntu/resolute` = `3540ba215ffbb117d899e24b6fb5192176518e31` (0ubuntu7) [CURRENTLY_VERIFIED: git rev-parse]. Not pushed [CURRENTLY_VERIFIED: CMD-REMOTE]. Export `docs/package-patches-b/indicator-bluetooth/0001-Build-depend-on-systemd-dev-so-the-systemd-user-unit.patch`: MATCH [CURRENTLY_VERIFIED: CMD-FP]. Also an older copy `research/indicator-units/indicator-bluetooth-systemd-dev.patch` [HISTORICAL_FACT: ls].
- versions: source 0.0.6+17.10.20170605-0ubuntu7+unity1; binary indicator-bluetooth 0.0.6+17.10.20170605-0ubuntu7+unity1 amd64 [CURRENTLY_VERIFIED: CMD-APTLY]
- build_state: sbuild successful, `~/work/b/ind/out` (2026-09-24 22:35Z) [HISTORICAL_FACT: ~/AGENTS-LOG.md:148,152]; deb sha256 = pool [CURRENTLY_VERIFIED: CMD-DEB]; unit file present in pool deb [CURRENTLY_VERIFIED: `dpkg-deb -c` | grep systemd]
- test_state: no package tests. target2: unit `loaded active running`, service on bus; `bluetooth-supported: false` (no adapter). Not checked with a real adapter [HISTORICAL_FACT: research/indicator-units/README.md:44-58]
- target_state: installed on target2 by `dpkg -i` then; target2 later reset to Clean-2 [HISTORICAL_FACT: status/B.md:167-170, 46-48]; now [UNVERIFIED]
- aptly_state: ONLY binary `indicator-bluetooth_0.0.6+17.10.20170605-0ubuntu7+unity1_amd64`; NO source package in aptly [CURRENTLY_VERIFIED: CMD-APTLY; `find /srv/aptly/pool -name '*indicator-bluetooth*'` → only the .deb]
- source↔aptly match: NOT_CHECKED against aptly (no .dsc in aptly). Substitute: `~/work/b/ind/src/indicator-bluetooth_…+unity1.dsc` extracted = `git archive a373dcf` (0 diff lines) [CURRENTLY_VERIFIED: dpkg-source -x + diff -r]; that .dsc is the one built in ind/out [INFERENCE from build log name/time; UNVERIFIED that the .changes names this .dsc hash]
- records: research/indicator-units/README.md; PATCHES.md:58; status/B.md:167-170; STACK-HEALTH.md:86; AGENTS-LOG.md:146-155; no DECISIONS.md heading of its own [CURRENTLY_VERIFIED: grep '^#' DECISIONS.md]
- current_state: published binary, source only on builder + export
- gaps_unknowns: research README:41 says "in aptly" for the versions — true for binaries only; source package missing from aptly (anyone rebuilding from our archive cannot `apt-get source`). LP #2153375 not updated [UNVERIFIED].
- provenance_gap: no build manifest / release gate / aptly snapshot (§6); source not pushed to any remote of ours (export only); source .dsc not in aptly.
- unfinished: add source package to aptly or re-publish through §6 flow (new task ID).
- doubtful_fix: none on correctness — mechanical packaging, root cause (empty `pkg-config --variable=systemduserunitdir`) documented [HISTORICAL_FACT: indicator-units/README.md:30-38]; no regression test possible beyond file-list check.
- proposed migration_result: LEGACY_PARTIAL — binary verified to come from our build, but no source package in aptly and source is export-only.

### B-L09 — indicator-printers: restore systemd user unit (+unity1)
- legacy_id: B-L09 (collected as G2-02)
- package: indicator-printers
- goal: same as G2-01 [HISTORICAL_FACT: research/indicator-units/README.md]
- commits/branches: `97fa92092b93cf7d616b96a6a1099c49ce86e40a` on `unity/resolute`; base `origin/ubuntu/resolute` = `c5e42e6ad97f95861d59073ba8d7d63edf857bd2` (0ubuntu8). Not pushed [CURRENTLY_VERIFIED: CMD-REMOTE]. Export `package-patches-b/indicator-printers/0001-…patch`: MATCH [CURRENTLY_VERIFIED: CMD-FP].
- versions: source/binary 0.1.7+17.10.20171101-0ubuntu8+unity1 (indicator-printers amd64) [CURRENTLY_VERIFIED: CMD-APTLY]
- build_state: sbuild ok `~/work/b/ind/out` [HISTORICAL_FACT: AGENTS-LOG.md:152]; deb sha = pool; unit present [CURRENTLY_VERIFIED: CMD-DEB, dpkg-deb -c]
- test_state: target2 unit active, `/com/canonical/indicator/printers` exported; icon with a print job not checked [HISTORICAL_FACT: indicator-units/README.md:51-58]
- target_state: as G2-01 [UNVERIFIED now]
- aptly_state: ONLY binary `indicator-printers_0.1.7+17.10.20171101-0ubuntu8+unity1_amd64`; NO source [CURRENTLY_VERIFIED: CMD-APTLY, pool find]
- source↔aptly match: NOT_CHECKED (no aptly .dsc). Workdir `.dsc` in `~/work/b/ind/src` = `git archive 97fa920` (0 diff lines) [CURRENTLY_VERIFIED]
- records: research/indicator-units/; PATCHES.md:58; status/B.md:167-170; STACK-HEALTH.md:87; AGENTS-LOG.md:146-155
- current_state: published binary only
- gaps_unknowns: as G2-01
- provenance_gap: as G2-01 (no §6 manifest/gate/snapshot; export only; no source in aptly)
- unfinished: as G2-01
- doubtful_fix: none (mechanical)
- proposed migration_result: LEGACY_PARTIAL — same reasons as G2-01.

### B-L10 — indicator-session: FTBFS fix, CMake 4 (+unity1)
- legacy_id: B-L10 (collected as G2-03)
- package: indicator-session
- goal: build in resolute (cmake_minimum_required bump only) [HISTORICAL_FACT: research/indicator-ftbfs/README.md:17]
- commits/branches: `47aac89dcd5d82e42de29cfafc23dd3334fdc542`; base `origin/ubuntu/resolute` = `d34d4b2bd8d4e093f1157254090a5b47888db30e`. Not pushed. Export `package-patches-b/indicator-session/0001-Build-with-CMake-4.patch`: MATCH [CURRENTLY_VERIFIED: CMD-REMOTE, CMD-FP]
- versions: 17.3.20+21.10.20210613.1-0ubuntu5+unity1 source + indicator-session amd64 [CURRENTLY_VERIFIED: CMD-APTLY]
- build_state: sbuild successful `~/work/b/indf/out` [HISTORICAL_FACT: indicator-ftbfs/README.md:29; AGENTS-LOG.md:201]; deb sha = pool [CURRENTLY_VERIFIED: CMD-DEB]
- test_state: file list = archive except locale; target2 service active, menu exported [HISTORICAL_FACT: indicator-ftbfs/README.md:29-45]
- target_state: installed on target2 2026-09-25, later Clean-2 [HISTORICAL_FACT: AGENTS-LOG.md:198; status/B.md:46-48]; now [UNVERIFIED]
- aptly_state: `indicator-session_…0ubuntu5+unity1_{source,amd64}` [CURRENTLY_VERIFIED: CMD-APTLY]
- source↔aptly match: MATCH (0 diff lines) [CURRENTLY_VERIFIED: CMD-SRC]
- records: research/indicator-ftbfs/README.md; DECISIONS.md:944 "rebuild five dead indicators ourselves…"; PATCHES.md:61; status/B.md:155-157; STACK-HEALTH.md:80
- current_state: published, consistent
- gaps_unknowns: none material
- provenance_gap: no §6 manifest/gate/snapshot; source export-only, not pushed.
- unfinished: none
- doubtful_fix: none (mechanical build fix)
- proposed migration_result: LEGACY_VERIFIED — source↔aptly MATCH and export MATCH verified now; mechanical build fix with recorded target check. Export-only source is listed as a provenance gap, not as a downgrade (same rule as B-L for libunity). [B's review, overrides collector's LEGACY_PARTIAL]

### B-L11 — indicator-power: FTBFS fix, CMake 4 + GCC 15 (+unity1)
- legacy_id: B-L11 (collected as G2-04)
- package: indicator-power
- goal: CMake bumps; `G_DBUS_CONNECTION()` cast on `g_object_ref()` result in `src/service.c` [HISTORICAL_FACT: indicator-ftbfs/README.md:16]
- commits/branches: `bff6e5d7a49c94d1803851b6edf51a84902bbe4b`; base `origin/ubuntu/resolute` = `c41fadb30b5646cadd285d73bbd33aae35e24406`. Not pushed. Export `package-patches-b/indicator-power/0001-Build-with-CMake-4-and-GCC-15.patch`: MATCH [CURRENTLY_VERIFIED]
- versions: 12.10.6+17.10.20170829.1-0ubuntu9+unity1 source + indicator-power amd64 [CURRENTLY_VERIFIED: CMD-APTLY]
- build_state: sbuild ok indf/out; deb sha = pool [CURRENTLY_VERIFIED: CMD-DEB]
- test_state: target2 service active; hides itself (no battery) — no battery path tested [HISTORICAL_FACT: indicator-ftbfs/README.md:38-41]
- target_state: as G2-03 [UNVERIFIED now]
- aptly_state: `…0ubuntu9+unity1_{source,amd64}` [CURRENTLY_VERIFIED]
- source↔aptly match: MATCH [CURRENTLY_VERIFIED: CMD-SRC]
- records: indicator-ftbfs/README.md; DECISIONS.md:944; PATCHES.md:61; status/B.md:155; STACK-HEALTH.md:83
- current_state: published, consistent
- gaps_unknowns: runtime with a battery/upower device never exercised [HISTORICAL_FACT: STACK-HEALTH.md:83 "Runtime with upower 1.91" still listed]
- provenance_gap: as G2-03
- unfinished: none
- doubtful_fix: none (mechanical)
- proposed migration_result: LEGACY_VERIFIED — as indicator-session; battery path never exercised (gap listed). [B's review, overrides collector's LEGACY_PARTIAL]

### B-L12 — indicator-sound: FTBFS fix cherry-picked from 26.10 0ubuntu10 (+unity1)
- legacy_id: B-L12 (collected as G2-05)
- package: indicator-sound
- goal: CMake 3.10 + GCC 15 casts in `src/main.c`, taken from 26.10 0ubuntu10 (LP #2166355) [HISTORICAL_FACT: indicator-ftbfs/README.md:18]
- commits/branches: `338d8fdd2f69360203b9df6d7f4ba11ff53002ac`; base `origin/ubuntu/resolute` = `56cb8b8c82db0140170ba2c72ff88b44b6d3100d`. Not pushed. Export `package-patches-b/indicator-sound/0001-…patch`: MATCH [CURRENTLY_VERIFIED]. Tree equals `origin/ubuntu/stonking` except `debian/changelog` [CURRENTLY_VERIFIED: `git diff --stat origin/ubuntu/stonking 338d8fd -- . ':!debian/changelog'` empty].
- versions: 12.10.2+18.10.20180612-0ubuntu7+unity1 source + indicator-sound amd64 [CURRENTLY_VERIFIED]. 26.10 has 0ubuntu10 [CURRENTLY_VERIFIED: CMD-MADISON]
- build_state: sbuild ok indf/out; deb sha = pool [CURRENTLY_VERIFIED]
- test_state: target2 service active, sound menu on panel [HISTORICAL_FACT: indicator-ftbfs/README.md:34-40]
- target_state: [UNVERIFIED now]
- aptly_state: `…0ubuntu7+unity1_{source,amd64}` [CURRENTLY_VERIFIED]
- source↔aptly match: MATCH [CURRENTLY_VERIFIED: CMD-SRC]
- records: indicator-ftbfs/README.md; DECISIONS.md:944; PATCHES.md:61; status/B.md:155; STACK-HEALTH.md:82
- current_state: published, consistent
- gaps_unknowns: version string says "0ubuntu7+unity1" while content = 26.10's 0ubuntu10 (minus changelog history) — naming only [INFERENCE]
- provenance_gap: as G2-03
- unfinished: none
- doubtful_fix: none (upstream-distro fix taken verbatim)
- proposed migration_result: LEGACY_VERIFIED — as indicator-session; content is 26.10's 0ubuntu10 verbatim. [B's review, overrides collector's LEGACY_PARTIAL]

### B-L13 — indicator-datetime: FTBFS fix (+unity1)
- legacy_id: B-L13 (collected as G2-06)
- package: indicator-datetime
- goal: CMake bumps; tests read libnotify 0.8 `image-path` hint when `app_icon==""` (test-only) [HISTORICAL_FACT: indicator-ftbfs/README.md:15]
- commits/branches: `7676fbe0948908fdaba5dd54a4d55575bda23b8e`; base `origin/ubuntu/resolute` = `4fb6fd847c54941ea90a7e593eacb415fcf3ac4a`. Not pushed. Export `package-patches-b/indicator-datetime/0001-…patch`: MATCH [CURRENTLY_VERIFIED]
- versions: 15.10+21.04.20210304-0ubuntu6+unity1 source + indicator-datetime amd64 [CURRENTLY_VERIFIED]
- build_state: sbuild ok indf/out, 28/28 tests [HISTORICAL_FACT: indicator-ftbfs/README.md:29-30]; deb sha = pool [CURRENTLY_VERIFIED]
- test_state: 28/28 package tests (test modifications are in the tests themselves, justified as libnotify 0.8 behaviour) [HISTORICAL_FACT: same]
- target_state: superseded by +unity2 [UNVERIFIED now]
- aptly_state: `…0ubuntu6+unity1_{source,amd64}` still present alongside +unity2 [CURRENTLY_VERIFIED]
- source↔aptly match: MATCH (only diff: empty dir tree `tests/test-eds-ics-config-files/.local/…` present in orig tarball, not representable in git) [CURRENTLY_VERIFIED: CMD-SRC; `tar tzf` orig]
- records: indicator-ftbfs/README.md; DECISIONS.md:944; PATCHES.md:61; STACK-HEALTH.md:81
- current_state: superseded, still in repo
- gaps_unknowns: none
- provenance_gap: as G2-03
- unfinished: none
- doubtful_fix: test edits (not code) — acceptable per §4 "bug is in that test" [INFERENCE]
- proposed migration_result: SUPERSEDED — by +unity2 (contains this commit).

### B-L14 — indicator-datetime: VTODO without DTSTART placed at DUE (+unity2; LP #1848969, #2099742)
- legacy_id: B-L14 (collected as G2-07)
- package: indicator-datetime
- goal: stop service abort (`DateTime::get(): assertion failed: (m_dt)`) on a VTODO with only DUE [HISTORICAL_FACT: research/indicator-datetime-tasks/README.md:1,20-38]
- commits/branches: `846dfa0758df267e0404508bfafd67e44f819961` (parent 7676fbe) on `unity/resolute`; base `origin/ubuntu/resolute` 4fb6fd8…. Not pushed. Export `package-patches-b/indicator-datetime/0002-Place-tasks-with-only-a-due-date-release-unity2-LP-1.patch`: MATCH [CURRENTLY_VERIFIED]. Note: sbuild (idt-fix, log 12:23:45Z) ran before the commit (12:42:04Z) — built from working tree; tree now equals aptly source [CURRENTLY_VERIFIED: log name vs `git show -s --format=%ci`; CMD-SRC].
- versions: 15.10+21.04.20210304-0ubuntu6+unity2 source + indicator-datetime amd64 [CURRENTLY_VERIFIED]. Archive resolute/stonking both 0ubuntu6 [CURRENTLY_VERIFIED: CMD-MADISON]
- build_state: `~/work/b/idt-fix/out` Status successful, "100% tests passed, 0 tests failed out of 29" [CURRENTLY_VERIFIED: grep log]; deb sha = pool [CURRENTLY_VERIFIED]
- test_state: fails-before/passes-after SHOWN: control build `~/work/b/idt-neg` (new test, old engine-eds.cpp) → `assertion failed: (m_dt)`, "1 tests failed out of 29: test-eds-ics-tasks-without-start", Status: attempted [CURRENTLY_VERIFIED: grep idt-neg/out/*Z.build lines 11999-12051]. target2: +unity1 aborts with core dump stack DateTime::get←format←get_appointment; +unity2 alive 3/3, task shown in menu; TZ/date/suspend checks [HISTORICAL_FACT: indicator-datetime-tasks/README.md:29-38,70-75]. Verification by implementer only [HISTORICAL_FACT: no reviewer recorded].
- target_state: target2 reset to Clean-2 after B-2 [HISTORICAL_FACT: AGENTS-LOG.md:326-327]; now [UNVERIFIED]
- aptly_state: `…0ubuntu6+unity2_{source,amd64}` [CURRENTLY_VERIFIED]
- source↔aptly match: MATCH (same empty-dir note as G2-06) [CURRENTLY_VERIFIED: CMD-SRC]
- records: research/indicator-datetime-tasks/ (README, dt.sh, dt2.sh, eds.py, *.ics); DECISIONS.md:1353; PATCHES.md:69; status/B.md:79-84; AGENTS-LOG.md:321-327
- current_state: published, latest
- gaps_unknowns: Ayatana upstream handling beyond 47e005d (does Ayatana use DUE for tasks?) not recorded [UNVERIFIED]. Whether EDS query also returns VTODO with DTSTART+DURATION or undated VTODO in other backends (Nextcloud/CalDAV) — only local task list tested [HISTORICAL_FACT: README:40-45].
- provenance_gap: no §6 manifest/gate/snapshot; source export-only, not pushed.
- unfinished: upstream/LP report of fix not recorded as sent [UNVERIFIED]; LP #1515821 deliberately left [HISTORICAL_FACT: README:79-85].
- doubtful_fix: Root cause proven (mechanism: `get_appointment()` takes begin from DTSTART only; `g_debug` args evaluated unconditionally → `DateTime::get()` asserts) with core-dump stack [HISTORICAL_FACT: README:20-38]. Three changes in diff [CURRENTLY_VERIFIED: `git show 846dfa0 -- src`]: (a) VTODO without DTSTART uses DUE — semantic fix at the producer (get_appointment), correct layer; RFC 5545 allows VTODO with DUE and no DTSTART, so this is valid input, not corruption [UNVERIFIED: RFC text not re-read in this session]. (b) `add_event_to_subtask` drops appointments with unset begin — for VEVENT, DTSTART is required by RFC 5545 (without METHOD) so skipping invalid events is defensible; for an undated VTODO RFC 5545 semantics are "applies to each successive day until completed", so skipping deviates, but README:44 says such a VTODO is not returned by the range query anyway, so (b) is effectively an untested backstop (test's third task never reaches it) [INFERENCE]. (c) `g_debug` guarded by `begin.is_set()` — redundant after (a)+(b) for reachable cases; a convenient-site guard but harmless [INFERENCE]. No §2 correct_layer / defensive_workaround_rejected fields; but DECISIONS.md:1358-1364 does reject Ayatana's NULL-return guard as hiding the cause — the reasoning §2 asks for exists informally. Patch scope: one defect, plus test [CURRENTLY_VERIFIED: diffstat 5 files, 143+/5-].
- proposed migration_result: LEGACY_PARTIAL — root cause and fails-before/passes-after evidence present and source↔aptly MATCH, but export-only source, implementer-only verification, no §2 card; secondary skip guard (b) untested.

### B-L15 — indicator-keyboard: build fix lightdm-vala + systemd-dev (+unity1)
- legacy_id: B-L15 (collected as G2-08)
- package: indicator-keyboard
- goal: Build-Depends `lightdm-vala` (split from liblightdm-gobject-1-dev) and systemd→systemd-dev [HISTORICAL_FACT: indicator-ftbfs/README.md:19]
- commits/branches: `ad9d0bf3ab289e6ed829f97900be585b8fad5f4d`; base `origin/ubuntu/resolute` = `134e19512e147c13761fc269417cf542a2c396c9`. Not pushed. Export `package-patches-b/indicator-keyboard/0001-…patch`: MATCH [CURRENTLY_VERIFIED]
- versions: 0.0.0+19.10.20240924-0ubuntu1+unity1 source + amd64 [CURRENTLY_VERIFIED]
- build_state: indf/out ok; deb sha = pool [CURRENTLY_VERIFIED]
- test_state: tests still `|| true` at this version (LP #1968333) [HISTORICAL_FACT: indicator-ftbfs/README.md:47-70]
- target_state: superseded [UNVERIFIED now]
- aptly_state: `…+unity1_{source,amd64}` present [CURRENTLY_VERIFIED]
- source↔aptly match: MATCH [CURRENTLY_VERIFIED: CMD-SRC]
- records: indicator-ftbfs/README.md; DECISIONS.md:944; PATCHES.md:61; STACK-HEALTH.md:84
- current_state: superseded, still in repo
- gaps_unknowns: none
- provenance_gap: as G2-03
- unfinished: none
- doubtful_fix: none (mechanical)
- proposed migration_result: SUPERSEDED — by +unity2/+unity3 (contain this commit).

### B-L16 — indicator-keyboard: test mock notify fix, tests fatal (+unity2; LP #1968333)
- legacy_id: B-L16 (collected as G2-09)
- package: indicator-keyboard
- goal: mock `Service.execute()` uses `notify_property("command")` (Vala ≥0.55.1 drops the detail → `g_object_notify(self, pspec)`); `debian/rules` drops `|| true` [HISTORICAL_FACT: indicator-ftbfs/README.md:47-100; DECISIONS.md:974]
- commits/branches: `cb8cf9653e55d5096a62a7540f26a99fee330e8d`, `1a14712981770911755c977e5d6b9f28fc679c5b`; exports 0002, 0003: MATCH [CURRENTLY_VERIFIED]. Not pushed.
- versions: 0.0.0+19.10.20240924-0ubuntu1+unity2 source + amd64 [CURRENTLY_VERIFIED]
- build_state: `~/work/b/kbt/out` Status successful, tests 1-9 ok [CURRENTLY_VERIFIED: grep log]; deb sha = pool [CURRENTLY_VERIFIED]
- test_state: 9/9 with tests fatal; Vala codegen reproduced with a 20-line class [HISTORICAL_FACT: indicator-ftbfs/README.md:84-92]
- target_state: superseded [UNVERIFIED now]
- aptly_state: `…+unity2_{source,amd64}` present [CURRENTLY_VERIFIED]
- source↔aptly match: MATCH [CURRENTLY_VERIFIED: CMD-SRC at 1a14712]
- records: indicator-ftbfs/README.md:47-100; DECISIONS.md:974; PATCHES.md:62; status/B.md:151-153; AGENTS-LOG.md:202-208
- current_state: superseded by +unity3
- gaps_unknowns: Vala upstream bug + LP #1968333 fix not reported (waits for May) [HISTORICAL_FACT: indicator-ftbfs/README.md:99-100]
- provenance_gap: as G2-03
- unfinished: upstream reports (Vala codegen, LP #1968333) — needs task ID if pursued
- doubtful_fix: none (test-only; bug is in the test itself; root cause traced to Vala commit b9df26bcf)
- proposed migration_result: SUPERSEDED — by +unity3 (contains both commits).

### B-L17 — indicator-keyboard: NULL InputSources guard (+unity3; LP #2166139)
- legacy_id: B-L17 (collected as G2-10)
- package: indicator-keyboard
- goal: stop greeter-side service SIGSEGV in `g_variant_iter_new(NULL)` from `migrate_input_sources()` [HISTORICAL_FACT: research/indicator-keyboard-2166139/README.md:1-58]
- commits/branches: `10eb95c564c9a4bdf402a7ff0b4fbb0de62ac3fa` on `unity/resolute` (4 ahead of base 134e195…). Not pushed. Export 0004: MATCH [CURRENTLY_VERIFIED]. sbuild ik3 log 12:10:26Z precedes commit 12:16:13Z (built from working tree; changelog dated 09:17:15Z from a first build) [CURRENTLY_VERIFIED: log name, `git show -s`]
- versions: 0.0.0+19.10.20240924-0ubuntu1+unity3 source + amd64 [CURRENTLY_VERIFIED]; resolute archive 0ubuntu1, stonking 0ubuntu4 [CURRENTLY_VERIFIED: CMD-MADISON]
- build_state: `~/work/b/ik3/out` Status successful; `ok 10 /indicator-keyboard-service/xkb-input-sources` [CURRENTLY_VERIFIED: grep log]; deb sha = pool [CURRENTLY_VERIFIED]
- test_state: target2 reproduction: restart accounts-daemon under service run as `lightdm` on lightdm-gtk-greeter's bus (ik.sh): +unity2 SIGSEGV 3/3 with symbolised core; +unity3 alive 3/3 [HISTORICAL_FACT: README:36-63]. Unit test covers new helper `get_xkb_input_sources` (NULL/empty/mixed); "negative check" against helper without NULL check "built separately in the chroot" — no log of it found in `~/work/b` [CURRENTLY_VERIFIED: find ~/work/b -iname '*neg*' → only idt-neg]. No test for the LightDM NULL user-name change. Implementer-only verification.
- target_state: target2 reset to Clean-2 after B-1 [HISTORICAL_FACT: AGENTS-LOG.md:319-320]; now [UNVERIFIED]
- aptly_state: `…+unity3_{source,amd64}` (+unity1, +unity2 also present) [CURRENTLY_VERIFIED]
- source↔aptly match: MATCH [CURRENTLY_VERIFIED: CMD-SRC]
- records: research/indicator-keyboard-2166139/ (README, ik.sh); DECISIONS.md:1335; PATCHES.md:68; status/B.md:86-92; AGENTS-LOG.md:309-320
- current_state: published, latest
- gaps_unknowns: DECISIONS.md:1344-1345 asserts "accountsservice documents that NULL" — no quote/link to act-user API docs or source in the record [HISTORICAL_FACT: README:24-28 gives only "(transfer none)… returns NULL"]; could not check (no AccountsService gir/headers on builder) [UNVERIFIED]. Whether GDBusProxy cache is really emptied (vs property invalidated) on name-owner loss not shown by trace, only inferred from the crash [INFERENCE].
- provenance_gap: no §6 manifest/gate/snapshot; source export-only, not pushed.
- unfinished: decide correct layer (see below); report to LP #2166139 not recorded [UNVERIFIED].
- doubtful_fix: Per §2/§4. Crash reproduced and symbolised — the trigger is proven [HISTORICAL_FACT]. WHY NULL: record claims AccountsService proxy cache empty while accounts-daemon is off the bus, while ActUser stays `is-loaded` [README:24-28] — mechanism inferred, not traced; the "documented contract" claim is unsourced. Correct layer not proven: the service is invoked on `notify::is-loaded` [README:45,55], i.e. the state inconsistency (is_loaded=true with no properties) originates in libaccountsservice/ActUser; the consumer guard treats a transient "unknown" as "no layouts". Actual diff [CURRENTLY_VERIFIED: `git show 10eb95c -- lib`]: with NULL, `migrate_input_sources()` proceeds, skips that user, and still writes `source_settings.set_value("sources", …)` and `set_uint("current", …)` for the greeter from the remaining users + LightDM layout — i.e. during a daemon restart it persists a possibly incomplete layout list; the record does not show that the list is corrected when accounts-daemon returns (no second notify / re-run evidence) [INFERENCE from code at 10eb95c:lib/main.vala migrate_input_sources; UNVERIFIED at runtime]. The better-layer alternative (skip migration / defer until properties are present, or fix/confirm ActUser is-loaded semantics) was not considered in the record — no defensive_workaround_rejected. LightDM NULL user_name guard added after seeing a critical in a first build [README:65-68] — a second call-site guard for the same upstream state, untested. Patch also refactors both iteration sites into a new file (broader than a minimal guard, though it serves the test seam).
- proposed migration_result: REQUIRES_REVALIDATION — crash fixed and source matches, but WHY InputSources is NULL (contract) is unsourced, the guard sits at the consumer while the inconsistency is in ActUser's is-loaded state, and the NULL path now writes greeter layout settings without proof of recovery.

### B-L18 — indicator-messages: no-change backport of 26.10 0ubuntu8 as 0ubuntu8~26.04.1 (LP #2166912)
- legacy_id: B-L18 (collected as G2-11)
- package: indicator-messages (Canonical)
- goal: carry 26.10's systemd-dev fix so the source builds in resolute and keeps its user unit [HISTORICAL_FACT: research/rebuild-loss/README.md:58-66; DECISIONS.md:1464]
- commits/branches: `86fbc0de1cd35ac4806b2792353bdaf3a5400f32` on `unity/resolute`, tracking `origin/ubuntu/stonking` = `78d9113d9ab7362111876c31b636a852aaf94b09` (base; NOT origin/ubuntu/resolute = a83d6d95513a4a03016c2f1c6fa917e26beb8112) [CURRENTLY_VERIFIED: git rev-parse, branch -vv]. Delta vs stonking: `debian/changelog` only (+9) [CURRENTLY_VERIFIED: `git diff --stat origin/ubuntu/stonking 86fbc0d`]. Not pushed. Export `package-patches-b/indicator-messages/0001-Backport-0ubuntu8-…patch`: MATCH vs `git format-patch origin/ubuntu/stonking..unity/resolute` [CURRENTLY_VERIFIED]. Export README table does NOT list indicator-messages [CURRENTLY_VERIFIED: package-patches-b/README.md table].
- versions: 13.10.1+18.10.20180918-0ubuntu8~26.04.1 source + indicator-messages amd64 [CURRENTLY_VERIFIED]; archive resolute 0ubuntu7, stonking 0ubuntu8 [CURRENTLY_VERIFIED: CMD-MADISON] → sorts between them [INFERENCE: dpkg ordering of `~`; not run]
- build_state: `~/work/b/imsg/out` ok; deb sha = pool; unit + /usr/share/unity/indicators file present [CURRENTLY_VERIFIED: CMD-DEB, dpkg-deb -c]
- test_state: compare.py: no file lost vs 0ubuntu7; target2: service runs (double start, harmless), menu exported, visible after direct `RegisterApplication` [HISTORICAL_FACT: rebuild-loss/README.md:66-90]
- target_state: Clean-2 after B-9 [HISTORICAL_FACT: AGENTS-LOG.md:387-388]; now [UNVERIFIED]
- aptly_state: `…0ubuntu8~26.04.1_{source,amd64}` [CURRENTLY_VERIFIED]
- source↔aptly match: MATCH [CURRENTLY_VERIFIED: CMD-SRC]
- records: research/rebuild-loss/README.md:58-95; DECISIONS.md:1464; PATCHES.md:73; status/B.md:52-53; AGENTS-LOG.md:377-388
- current_state: published but functionally obsolete — no client library can reach it in 26.04; superseded as a user feature by G2-12/G2-14 [HISTORICAL_FACT: messaging-menu/README.md:117-127]
- gaps_unknowns: whether the git-ubuntu `origin/ubuntu/stonking` tip (commit subject "Update changelog for accountsservice transition", not an import commit) equals the archive's 0ubuntu8 source [UNVERIFIED]
- provenance_gap: no §6 manifest/gate/snapshot; export-only; base is a 26.10 branch.
- unfinished: decide whether to keep it in aptly at all (it has no clients; nothing should install it for Unity) — new task ID if removal wanted.
- doubtful_fix: none on code (verbatim 26.10). Value doubtful (no clients).
- proposed migration_result: LEGACY_PARTIAL — source↔aptly MATCH, but export-only, not in export README table, and package is functionally obsolete.

### B-L19 — ayatana-indicator-messages: link indicator into /usr/share/unity/indicators (+unity1)
- legacy_id: B-L19 (collected as G2-12)
- package: ayatana-indicator-messages
- goal: add `debian/ayatana-indicator-messages.links` so Unity's panel loads the Ayatana messages indicator (needs libindicator +unity2) [HISTORICAL_FACT: research/messaging-menu/README.md:65-74]
- commits/branches: no git tree (no `packages/ayatana-indicator-messages`) [CURRENTLY_VERIFIED: ls]. Export `docs/package-patches-b/debdiff/ayatana-indicator-messages_+unity1.debdiff` (23 lines: .links + changelog).
- versions: 24.5.1-1build1+unity1 source; binaries ayatana-indicator-messages, libmessaging-menu0, libmessaging-menu-dev, gir1.2-messagingmenu-1.0 (amd64) [CURRENTLY_VERIFIED: CMD-APTLY]. Base resolute 24.5.1-1build1; stonking 24.5.2-3 [CURRENTLY_VERIFIED: CMD-MADISON]
- build_state: `~/work/b/aim/out` (build log present; `~/work/b/aim/sbuild.log` is 0 bytes) [CURRENTLY_VERIFIED: ls -la]; all 4 debs sha = pool [CURRENTLY_VERIFIED: CMD-DEB]; symlink present in deb [CURRENTLY_VERIFIED: dpkg-deb -c]
- test_state: package's 3 tests pass [HISTORICAL_FACT: messaging-menu/README.md:74]; target2: envelope, counts, activate-source, Pidgin/Geary [HISTORICAL_FACT: README:80-100]; B-11 full-upgrade from Clean-2 installed it [HISTORICAL_FACT: README:170-176]
- target_state: Clean-2 after B-10/B-12 [HISTORICAL_FACT: AGENTS-LOG.md:399-400; status/B.md:46-48]; now [UNVERIFIED]
- aptly_state: as above, one version [CURRENTLY_VERIFIED]
- source↔aptly match: MATCH — aptly .dsc/.debian.tar.xz/.orig sha256 = `~/work/b/aim` files; `diff -Nru` of extracted base 24.5.1-1build1 (from `~/work/b/aim`) vs extracted aptly source equals the exported debdiff (ignoring headers) [CURRENTLY_VERIFIED: sha256sum; dpkg-source -x ×2; diff]. Base .dsc signature could not be checked (`gpgv`: no public key for 25E3FF2D…) [CURRENTLY_VERIFIED] → base authenticity [UNVERIFIED].
- records: research/messaging-menu/README.md; DECISIONS.md:1498; PATCHES.md:78; package-patches-b/README.md (debdiff list); status/B.md:33-39; AGENTS-LOG.md:396-400
- current_state: published; functionally depends on G2-14
- gaps_unknowns: base source provenance (signature) unverified; no git tree.
- provenance_gap: no §6 manifest/gate/snapshot; no git tree at all — debdiff only.
- unfinished: none of its own; tied to G2-14 revalidation.
- doubtful_fix: packaging-only; correctness hinges on libindicator +unity2 design (G2-14).
- proposed migration_result: LEGACY_PARTIAL — source↔aptly verified via debdiff, but no git tree, unsigned-checked base, and dependent on a REQUIRES_REVALIDATION item.
- note: the G3 collector independently regenerated the debdiff archive→aptly and got the committed debdiff body (MATCH) [CURRENTLY_VERIFIED: collected as G3-12].

### B-L20 — libindicator: build fix systemd-dev, keep indicators-pre.target (+unity1)
- legacy_id: B-L20 (collected as G2-13)
- package: libindicator
- goal: FTBFS fix (`dh_install --fail-missing` on missing `indicators-pre.target`) [HISTORICAL_FACT: research/rebuild-trial/README.md:19-50]
- commits/branches: `f75a61760288cde9878f86c68f963f09a9808fc7`; base `origin/ubuntu/resolute` = `56a2331dde7aba1a4ada9a634cd3d1d7ff57032e`. Not pushed. Export 0001: MATCH [CURRENTLY_VERIFIED]
- versions: 16.10.0+18.04.20180321.1-0ubuntu8+unity1; binaries indicator-common (all), libindicator-dev, libindicator3-7, libindicator3-dev, libindicator3-tools, libindicator7 (amd64) [CURRENTLY_VERIFIED: CMD-APTLY]
- build_state: `~/work/b/rebuild/fix-libindicator`; all 6 debs sha = pool [CURRENTLY_VERIFIED: CMD-DEB]
- test_state: file lists/exported symbols (34 and 40)/shlibs equal archive [HISTORICAL_FACT: rebuild-loss/README.md:40-51]; confirmed symbol counts 34 (libindicator7) and 40 (libindicator3-7) [CURRENTLY_VERIFIED: CMD-SYM]
- target_state: [UNVERIFIED]
- aptly_state: `…+unity1` source + 6 binaries, alongside +unity2 [CURRENTLY_VERIFIED]
- source↔aptly match: MATCH [CURRENTLY_VERIFIED: CMD-SRC]
- records: research/rebuild-trial/README.md:19-50; research/rebuild-loss/README.md:38-54; DECISIONS.md:1198, 1430; PATCHES.md:64; status/B.md:54-55, 124-128; AGENTS-LOG.md:245-251, 353-355
- current_state: superseded by +unity2
- gaps_unknowns: stale records — PATCHES.md:64 and status/B.md:125 still say "not in aptly" though it was published 2026-09-26 14:34Z [HISTORICAL_FACT: AGENTS-LOG.md:354-355; CURRENTLY_VERIFIED: CMD-APTLY]
- provenance_gap: as G2-03
- unfinished: fix stale PATCHES.md:64 row (doc task)
- doubtful_fix: none (mechanical)
- proposed migration_result: SUPERSEDED — by +unity2 (contains f75a617).

### B-L21 — libindicator: accept Ayatana indicators on Unity's panel, GMenuModel wrapper (+unity2)
- legacy_id: B-L21 (collected as G2-14)
- package: libindicator (shared library libindicator3-7)
- goal: `indicator-ng.c` accepts `x-ayatana-type org.ayatana.indicator.root`, `x-ayatana-{scroll,secondary}-action`, wraps Ayatana popups in a GMenuModel adding `x-canonical-type` from a 12-entry table [HISTORICAL_FACT: messaging-menu/README.md:48-66]
- commits/branches: `67bfe16332f1394e5ce5c9e137ec345c0e7e0a40` (parent f75a617). Not pushed. Export 0002: MATCH [CURRENTLY_VERIFIED]. sbuild li2 log 17:31:02Z precedes commit 17:53:03Z (built from working tree) [CURRENTLY_VERIFIED]
- versions: 16.10.0+18.04.20180321.1-0ubuntu8+unity2; same 6 binaries [CURRENTLY_VERIFIED: CMD-APTLY]
- build_state: `~/work/b/li2/out`; all 6 debs sha = pool [CURRENTLY_VERIFIED: CMD-DEB]
- test_state: libindicator has no test covering indicator-ng; target2 manual: envelope/menu/counts/click, Pidgin, Unity sound menu unchanged (one screenshot) [HISTORICAL_FACT: messaging-menu/README.md:80-100]; implementer only. No ABI/symbol check recorded for +unity2 [CURRENTLY_VERIFIED: grep 'symbol|ABI' messaging-menu/README.md → none]
- target_state: installed via B-11 full-upgrade, then Clean-2 [HISTORICAL_FACT: messaging-menu/README.md:170-176; status/B.md:46-48]; now [UNVERIFIED]
- aptly_state: `…+unity2` source + 6 binaries [CURRENTLY_VERIFIED]
- source↔aptly match: MATCH [CURRENTLY_VERIFIED: CMD-SRC]
- records: research/messaging-menu/README.md; DECISIONS.md:1498; PATCHES.md:77; status/B.md:33-39; AGENTS-LOG.md:389-400
- current_state: published, latest; ayatana-indicator-messages +unity1 and ubuntu-unity-meta 0.29+unity1 Recommends depend on it functionally
- gaps_unknowns: NEW EXPORTED SYMBOL: libindicator3.so.7 +unity2 exports `indicator_ng_ayatana_menu_get_type` (G_DEFINE_TYPE, not static), 40→41 dynamic symbols vs +unity1; libindicator7 (GTK2) unchanged at 34 [CURRENTLY_VERIFIED: CMD-SYM]. Package has no .symbols file (only shlibs), so the addition went unflagged [CURRENTLY_VERIFIED: `git ls-tree 67bfe16 debian/`]. Also registers global GType name "IndicatorNgAyatanaMenu" in every process loading libindicator3 [INFERENCE from code]. Only messages indicator exercised; other Ayatana indicators possibly dropped into /usr/share/unity/indicators later untested [INFERENCE].
- provenance_gap: no §6 manifest/gate/snapshot; export-only, not pushed.
- unfinished: under §2 a shared-library/component-boundary change needs Design Challenger APPROVE (none exists); ABI/API check; decide on symbol visibility (make type private / version script) — new task ID.
- doubtful_fix: Not a crash guard; a feature/compat layer in a shared library consumed by unity-panel-service and all indicators. Options analysis exists (3 options, cost/risk) [HISTORICAL_FACT: messaging-menu/README.md:37-56; DECISIONS.md:1498] but no Design Challenger, no ABI review, and the recorded claim "only Ayatana indicators take the new code path" [README:41] is incomplete: `indicator_ng_menu_item_is_of_type` now also accepts `x-ayatana-type` for any `com.canonical.*` expected type, and scroll/secondary action lookup falls back to `x-ayatana-*` for all indicators [CURRENTLY_VERIFIED: `git show 67bfe16 -- libindicator`] (benign for Canonical indicators that lack those attributes [INFERENCE]). Wrapper lifetime: holds ref on base, disconnects on finalize; new wrapper per `get_item_links` call [CURRENTLY_VERIFIED: code] — ownership looks right, not reviewed by a second party. Type-mapping table first attempt (prefix mapping) broke rows and was corrected by observation [HISTORICAL_FACT: README:60-63].
- proposed migration_result: REQUIRES_REVALIDATION — shared-library behaviour/ABI change (unrecorded new exported symbol) without Design Challenger or ABI check; implementer-only manual verification.

### B-L22 — libunity: Python scope runner without `imp` (Python 3.12+)
- legacy_id: B-L22 (collected as G3-01)
- package: libunity (binaries gir1.2-unity-7.0, libunity-dev, libunity-protocol-private0, libunity-scopes-json-def-desktop, libunity-scopes-json-def-phone, libunity-tools, libunity9, unity-scopes-runner) [CURRENTLY_VERIFIED: C-APTLY]
- goal: `/usr/share/unity-scopes/scope-runner-dbus.py` did `import imp` (removed in 3.12) → every Python scope failed with ModuleNotFoundError; replace `imp.load_source()` with importlib + explicit SourceFileLoader [HISTORICAL_FACT: docs/research/libunity-python314/README.md:14-35]
- commits/branches:
  - packages/libunity (git-ubuntu clone, only remote `origin` = git.launchpad.net/ubuntu/+source/libunity), branch `unity/resolute` = `78c98ec79f189ac748e69bb4872723c0f194866c` (2026-09-26 12:58:31Z, "Load source scopes with importlib; release +unity1"), base `origin/ubuntu/resolute` = `fc47c881337392636c90cb1e8eb6088a1e316bfe`, ahead 1 [CURRENTLY_VERIFIED: git log / git branch -vv / git rev-parse origin/ubuntu/resolute]
  - NOT pushed anywhere: `git branch -r --contains 78c98ec` empty; `git ls-remote origin` has only Launchpad refs (ubuntu/resolute = fc47c88) [CURRENTLY_VERIFIED]
  - export: docs/package-patches-b/libunity/0001-Load-source-scopes-with-importlib-release-unity1.patch, committed in unity-distro `f9167f2b6b6a1ac1ad981b94bb55de4d24d0173f`, on origin/main [CURRENTLY_VERIFIED: C-DOCGIT]
  - `git format-patch fc47c88..unity/resolute --stdout` is byte-identical to the export [CURRENTLY_VERIFIED: diff → no output, "LU_IDENTICAL"]
- versions: source 7.1.4+19.04.20190319-6.1ubuntu1+unity1; all 8 binaries same version [CURRENTLY_VERIFIED: C-APTLY]
- build_state: sbuild -d resolute successful, Build-Time 157, `~/work/b/lu1/out/libunity_*+unity1_amd64.build`: "Status: successful"; libunity testsuite TOTAL 4 / PASS 4 / FAIL 0 (lines 3815-3821) [CURRENTLY_VERIFIED: grep on build log]. Tests do not cover the runner [HISTORICAL_FACT: research/libunity-python314/README.md:37-38]
- test_state: target2 (Clean-2 + +unity1): runner owns com.canonical.Unity.Scope.Info.Calculator, Dash `calc: 12*7` → 84 (dash-unity1.png); stock: no results (dash-stock.png) [HISTORICAL_FACT: research/libunity-python314/README.md:40-46, 25-26]. No automated regression test for the runner [HISTORICAL_FACT: same:37-38]
- target_state: target2 rolled back to Clean-2 after B-3 [HISTORICAL_FACT: ~/AGENTS-LOG.md:334 (13:01Z)]. Current target contents [UNVERIFIED: no VM access]
- aptly_state: source + 8 binaries at 7.1.4+19.04.20190319-6.1ubuntu1+unity1, one version each; published index shows libunity9/unity-scopes-runner at +unity1 [CURRENTLY_VERIFIED: C-APTLY, C-PUB, 04-aptly-latest-by-source.txt:17]. `.dsc` source in aptly: YES
- source↔aptly match: MATCH — `dpkg-source --no-check --skip-patches -x <aptly .dsc>` tree == `git archive 78c98ec` tree (`diff -r` empty, "LU_TREE_MATCH"); aptly .dsc sha256 c2351387… == ~/work/b/lu1 .dsc; all 8 aptly .debs == ~/work/b/lu1/out/* (C-BIN); orig == archive orig (C-ORIG) [CURRENTLY_VERIFIED]
- records: research/libunity-python314/README.md (whole); DECISIONS.md:1371 "## 2026-09-26 - libunity +unity1: scope runner without imp (agent B)"; PATCHES.md:70; status/B.md:72-77; package-patches-b/README.md row libunity; AGENTS-LOG.md:328,329,331,332,334; 07-PENDING-MAY.md:49 [HISTORICAL_FACT]
- current_state: published in aptly, consistent with git+export [CURRENTLY_VERIFIED]
- gaps_unknowns: commit only on builder + export (no remote git) [CURRENTLY_VERIFIED]; stonking has -8 (still imports imp per research:8-11), version-ordered above ours, so a 26.10 upgrade would drop the fix — not a resolute issue [CURRENTLY_VERIFIED: C-RMADISON shows stonking 7.1.4+19.04.20190319-8; HISTORICAL_FACT research:8-11]; PyGI deprecation warnings remain [HISTORICAL_FACT: research:44-46]
- provenance_gap: common gap; source_provenance not PUSHED (local commit, export only)
- unfinished: none for this fix. Side findings recorded, not B's task: light-locker SIGABRT on Clean-2 boot "Not investigated" [HISTORICAL_FACT: research/libunity-python314/README.md:56-58]
- doubtful_fix: root cause is exact (import of removed module) and the change is in the file that owns it; minimal (one quilt patch); keeps any-extension loading via explicit SourceFileLoader. No regression test in the package's suite (runner untested) — §4 wants one where a seam exists; the Dash check is the strongest reproduction given [HISTORICAL_FACT: research:37-43]. No other doubt.
- proposed migration_result: **LEGACY_VERIFIED** — git tree, export, aptly source and binaries currently match; provenance gap (local-only commit, no gate/manifest/snapshot) listed.

### B-L23 — appmenu-gtk-module: make the GTK3 module resident (upstream a783b01c, LP #2166410)
- legacy_id: B-L23 (collected as G3-02)
- package: appmenu-gtk-module (binaries appmenu-gtk-module-common, appmenu-gtk3-module, libappmenu-gtk-parser-dev-common, libappmenu-gtk3-parser-dev, libappmenu-gtk3-parser0) [CURRENTLY_VERIFIED: C-APTLY]
- goal: GTK3 `g_module_close()`s modules loaded via the `gtk-modules` XSETTING when it changes; appmenu module hijacks GtkMenuBar → segfault; backport a783b01c (`g_module_check_init` → `g_module_make_resident`) [HISTORICAL_FACT: research/appmenu-resident/README.md:1-24, 37-44]
- commits/branches:
  - packages/appmenu-gtk-module (git-ubuntu clone, only remote Launchpad), `unity/resolute` = `548f9b4d8e16e71f00b212e6ab384223786c32fa` (2026-09-25 00:05:07Z), base `origin/ubuntu/resolute` = `025b498fd25ff0adce3b022ad6ddb33babc95f05`, ahead 1; not in any remote ref [CURRENTLY_VERIFIED: git log / branch -vv / rev-parse]
  - export docs/package-patches-b/appmenu-gtk-module/0001-Make-the-GTK-module-resident-upstream-a783b01c-LP-21.patch, unity-distro commit `f9167f2b6b6a1ac1ad981b94bb55de4d24d0173f`, on origin/main [CURRENTLY_VERIFIED: C-DOCGIT]
  - `git format-patch 025b498..unity/resolute --stdout` identical to export ("AM_IDENTICAL") [CURRENTLY_VERIFIED]
- versions: source 25.04-1build1+unity1; 5 binaries 25.04-1build1+unity1 (no -dbgsym in aptly) [CURRENTLY_VERIFIED: C-APTLY]
- build_state: sbuild in ~/work/b/amenu, build log `appmenu-gtk-module_25.04-1build1+unity1_amd64-2026-09-25T00:05:18Z.build` "Status: successful" [CURRENTLY_VERIFIED: grep]; started 00:05Z [HISTORICAL_FACT: AGENTS-LOG.md:176]
- test_state: repro with Xvfb/xsettingsd `unload.sh`/`readd.sh`: archive SIGSEGV 2/2 on drop; +unity1 exit 0 kept/dropped/re-added 4/4 [HISTORICAL_FACT: research/appmenu-resident/README.md:26-35, 84-97]; live under Unity (Clean-2 + aptly): GIMP 3.2.2 archive SIGSEGV 2/2 vs +unity1 survives 2/2; LibreOffice survives both; Chromium snap does not map host module [HISTORICAL_FACT: same:107-133]. Not checked: panel-click menu opening, Chrome [HISTORICAL_FACT: same:53-54]. No in-package regression test (package has no test seam for this) [UNVERIFIED whether a seam exists]
- target_state: target2 rolled back to Clean-2 after B-8 [HISTORICAL_FACT: AGENTS-LOG.md:374]; status/B.md:160-161 "target2 has it (dpkg -i)" is stale [HISTORICAL_FACT vs AGENTS-LOG.md:374]
- aptly_state: 5 binaries at 25.04-1build1+unity1; **source NOT in aptly** (C-APTLY lists no `_source`; no appmenu-gtk-module_*.dsc under /srv/aptly/pool) [CURRENTLY_VERIFIED]; published index appmenu-gtk3-module 25.04-1build1+unity1 [CURRENTLY_VERIFIED: C-PUB]; published 2026-09-25 00:11Z [HISTORICAL_FACT: AGENTS-LOG.md:178-179]
- source↔aptly match: MATCH (indirect) — all 5 aptly .debs sha256 == ~/work/b/amenu/*.deb; `dpkg-source --skip-patches -x ~/work/b/amenu/…+unity1.dsc` tree == `git archive 548f9b4` ("AM_TREE_MATCH") [CURRENTLY_VERIFIED]. The chain aptly-binary → build-dir .dsc rests on the local build dir, not on a source in aptly.
- records: research/appmenu-resident/README.md; PATCHES.md:60; DECISIONS.md:1061-1063 (inside "## 2026-09-25 - Re-check of agent B's fixes…", heading at 1047) — no dedicated DECISIONS heading; status/B.md:44-46, 159-161; STACK-HEALTH row (research:3); 05-STATUS.md:39-43; AGENTS-LOG.md:174-180, 351, 367, 374; 07-PENDING-MAY.md:56, 68 [HISTORICAL_FACT]
- current_state: binaries published, consistent with local git commit and build dir [CURRENTLY_VERIFIED]
- gaps_unknowns: source package absent from aptly; git commit local-only; no dedicated DECISIONS entry; stale status/B.md:160-161 [CURRENTLY_VERIFIED / HISTORICAL_FACT as above]
- provenance_gap: common gap + source not in aptly + source_provenance not PUSHED (export only)
- unfinished: panel-click activation of the exported menu not verified [HISTORICAL_FACT: research:53-54]; GTK2 apps have no global menu (appmenu-gtk2-module gone) — "Not planned" [HISTORICAL_FACT: research/hud/README.md:151-157]
- doubtful_fix: upstream's own fix, exact mechanism shown (LP gdb stack dlclose←g_module_close; GTK 3.24.52 gtkmodules.c), correct layer (the module declares itself resident), re-init/watcher/unload neighbours reviewed (research:56-100). Not reachable in the default Unity session (module comes from GTK_MODULES) — a protective carry [HISTORICAL_FACT: research:19-24]. No doubt on correctness.
- proposed migration_result: **LEGACY_PARTIAL** — fix sound and binaries currently trace to commit 548f9b4, but the source package is not in aptly and the commit exists only on builder (export).

### B-L24 — hud: FTBFS fixes (CMake 4, systemd-dev, C++17)
- legacy_id: B-L24 (collected as G3-03)
- package: hud (binaries gir1.2-hud-2, gir1.2-hud-client-2, hud, hud-doc, hud-tools, libhud-client2, libhud-client2-dev, libhud-client2-doc, libhud-gtk1, libhud-gtk1-dev, libhud-gtk1-doc, libhud2, libhud2-dev, libhud2-doc + 4 -dbgsym) [CURRENTLY_VERIFIED: C-APTLY]
- goal: rebuild the never-rebuilt noble upload in resolute: cmake_minimum_required 3.10 (CMakeLists.txt + 5 cmake/*.cmake), Build-Depends systemd → systemd-dev, `-std=c++14` → `-std=c++17` [HISTORICAL_FACT: research/hud/README.md:19-29; debdiff]
- commits/branches: no git tree. Debdiff docs/package-patches-b/debdiff/hud_+unity1.debdiff, last commit `06bcc6b951e69b18e98cea8bc2f80ce5b210ec17` (2026-09-26 19:34Z), on origin/main [CURRENTLY_VERIFIED: C-DOCGIT]
- versions: source 14.10+17.10.20170619-0ubuntu6+unity1; all binaries same [CURRENTLY_VERIFIED: C-APTLY]; archive resolute/stonking 0ubuntu6 [CURRENTLY_VERIFIED: C-RMADISON]
- build_state: ~/work/b/hud/out/hud_*+unity1_amd64.build: "100% tests passed, 0 tests failed out of 6", "Status: successful" [CURRENTLY_VERIFIED: grep]. Earlier B-7 attempt `~/work/b/b7fix/hud_…+unity1.dsc` (sha 0ac7718c…, differs from aptly) = pre-C++17 WIP, not published [CURRENTLY_VERIFIED: sha256sum; HISTORICAL_FACT: status/B.md:57]
- test_state: file lists of 14 binaries = archive's, exported symbols equal [HISTORICAL_FACT: research/hud/README.md:37-41]; live on target2: GTK4 (gnome-text-editor via unity-gtk4-menu) and GTK3 (GIMP via appmenu) found in HUD; no hud-service crash [HISTORICAL_FACT: same:45-66]; LibreOffice intermittent 11/24 vs archive 10/15 [HISTORICAL_FACT: same:68-80]
- target_state: target2 back on Clean-2 after B-12 [HISTORICAL_FACT: AGENTS-LOG.md:413-414; status/B.md:47-48]
- aptly_state: source + 18 binaries (incl. dbgsym) at 0ubuntu6+unity1, one version [CURRENTLY_VERIFIED: C-APTLY; 04-aptly-latest-by-source.txt:7]; `.dsc` in aptly YES; published hud 0ubuntu6+unity1 [CURRENTLY_VERIFIED: C-PUB]
- source↔aptly match: MATCH — C-DD hud "MATCH"; orig identical (C-ORIG); aptly .dsc sha 458c3a9d… == ~/work/b/hud .dsc; all 14 aptly .debs == ~/work/b/hud/out (C-BIN) [CURRENTLY_VERIFIED]
- records: research/hud/README.md; DECISIONS.md:1567 "## 2026-09-26 - hud: rebuild in resolute; the LibreOffice HUD gap is recorded, not fixed (agent B)"; PATCHES.md:82; status/B.md:8-20 (current), 52-57 (stale "WIP" line 57); research/rebuild-loss/README.md:32; package-patches-b/README.md; AGENTS-LOG.md:413-414 (DONE only — no "START build hud" / "START aptly publish hud" lines exist for B-12) [CURRENTLY_VERIFIED: grep AGENTS-LOG]; 07-PENDING-MAY.md:77
- current_state: published, consistent with committed debdiff [CURRENTLY_VERIFIED]
- gaps_unknowns: publish moment not logged (protocol gap) [CURRENTLY_VERIFIED]; stale status/B.md:57 [HISTORICAL_FACT]
- provenance_gap: common gap + no-git source (debdiff only)
- unfinished (records show open): (a) LibreOffice HUD empty in ~half of Writer starts — "recorded, not fixed", one mechanism not traced [HISTORICAL_FACT: DECISIONS.md:1580-1584; research/hud/README.md:68-100]; (b) window-stack-bridge drops a window when bamf's DesktopFile() call fails, no retry; suggested fallback not implemented [HISTORICAL_FACT: research/hud/README.md:84-93]; (c) window-stack-bridge app id from `QFileInfo::baseName()` → reverse-DNS ids collapse to `org` ("harmless", not fixed) [HISTORICAL_FACT: same:102-104]; (d) GTK2 global menu "Not planned" [HISTORICAL_FACT: same:151-157]. Each would need a new task ID.
- doubtful_fix: layers 1-2 are exact build-system causes at the correct layer. Layer 3: `-std=c++17` is set in the project-wide `CMAKE_CXX_FLAGS` (CMakeLists.txt:138), so it also changes the dialect of shipped C++ code (hud-service, window-stack-bridge, libhud-client/qtgmenu), while the stated cause is only googletest in the tests [HISTORICAL_FACT: debdiff; research:27]. Narrower option (C++17 only for the test targets) was not evaluated [UNVERIFIED]. Mitigation: file lists and exported symbols equal archive, tests 6/6, live check ok [HISTORICAL_FACT: research:31-41]. Three defects in one upload — acceptable for an FTBFS chain (each is a prerequisite of the next) but not "one defect per patch" (§4).
- proposed migration_result: **LEGACY_VERIFIED** — debdiff ⇄ aptly source ⇄ binaries currently verified, tests recorded; C++17 breadth noted for review, open HUD findings need new tasks.

### B-L25 — overlay-scrollbar: stub package, remove 81overlay-scrollbar
- legacy_id: B-L25 (collected as G3-04)
- package: overlay-scrollbar (binaries overlay-scrollbar [all], overlay-scrollbar-gtk2 [amd64, empty transitional]) [CURRENTLY_VERIFIED: C-APTLY]
- goal: session script `/etc/X11/Xsession.d/81overlay-scrollbar` set GTK2_MODULES=overlay-scrollbar; module needs a dropped GTK2 patch → "undefined symbol: ubuntu_gtk_set_use_overlay_scrollbar" (second Pidgin dies). Build nothing, keep GSettings schemas, rm_conffile the script, empty -gtk2 [HISTORICAL_FACT: research/messaging-menu/README.md:102-116, 131-153; debdiff changelog]
- commits/branches: no git tree. docs/package-patches-b/debdiff/overlay-scrollbar_+unity1.debdiff, commit `f752fb672eb781ea04e6a936c54d32bf75695668` (2026-09-26 18:13Z), on origin/main [CURRENTLY_VERIFIED: C-DOCGIT]
- versions: source/binaries 0.2.17.1+16.04.20151117-0ubuntu5+unity1 [CURRENTLY_VERIFIED: C-APTLY]; archive resolute + stonking 0ubuntu5 [CURRENTLY_VERIFIED: C-RMADISON]
- build_state: ~/work/b/osb/out build "Status: successful" [CURRENTLY_VERIFIED: grep]
- test_state: target2 from Clean-2 + aptly full-upgrade: "Removing obsolete conffile …81overlay-scrollbar", liboverlay-scrollbar.so gone, no GTK2_MODULES after reboot, Pidgin starts and raises from envelope [HISTORICAL_FACT: research/messaging-menu/README.md:170-186; DECISIONS.md:1553-1555]
- target_state: target2 back on Clean-2 after B-11 [HISTORICAL_FACT: AGENTS-LOG.md:406]
- aptly_state: source + 2 binaries, one version [CURRENTLY_VERIFIED: C-APTLY; 04-…:21]; .dsc in aptly YES; published both binaries +unity1 [CURRENTLY_VERIFIED: C-PUB]
- source↔aptly match: MATCH — C-DD "MATCH"; orig identical; aptly .dsc sha 3ffe644a… == ~/work/b/osb .dsc; both .debs == ~/work/b/osb/out (C-BIN) [CURRENTLY_VERIFIED]
- records: research/messaging-menu/README.md:102-116, 131-194; DECISIONS.md:1528 "## 2026-09-26 - overlay-scrollbar: a stub package, not Breaks in the metapackage (agent B)"; PATCHES.md:79; status/B.md:22-31, 58; package-patches-b/README.md; AGENTS-LOG.md:401-406; 07-PENDING-MAY.md:72-73 [HISTORICAL_FACT]
- current_state: published, consistent [CURRENTLY_VERIFIED]
- gaps_unknowns: research/rebuild-loss/README.md:35 still says overlay-scrollbar is "dead … deleted from resolute. List only" — contradicted by C-RMADISON (0ubuntu5 in resolute/universe) and by B-11 [CURRENTLY_VERIFIED / HISTORICAL_FACT]
- provenance_gap: common gap + no-git source (debdiff only)
- unfinished: none recorded as open.
- doubtful_fix: the package that ships the conffile is the correct layer to remove it; Breaks-in-meta alternative rejected with a concrete reason (reaches only meta users; apt upgrade holds back removals) [HISTORICAL_FACT: DECISIONS.md:1545-1550]. The change removes an entire feature (GTK2 overlay scrollbars) rather than a line — justified by FTBFS against 26.04 GTK2 and dead module [HISTORICAL_FACT: debdiff changelog; rebuild-loss:35]. Adds a pre-generated `debian/com.canonical.desktop.interface.enums.xml` (glib-mkenums output checked in) — mechanical. No doubt beyond noting it is a package redesign, not a patch.
- proposed migration_result: **LEGACY_VERIFIED** — debdiff/aptly/binaries currently match; upgrade path verified on target2; stale rebuild-loss row to be corrected.

### B-L26 — ubuntu-unity-meta: 0.29+unity1 (Recommends ayatana-indicator-messages, drop overlay-scrollbar-gtk2)
- legacy_id: B-L26 (collected as G3-05)
- package: ubuntu-unity-meta (binary ubuntu-unity-desktop amd64) [CURRENTLY_VERIFIED: C-APTLY]
- goal: in desktop-recommends-{amd64,arm64,armhf,ppc64el} replace overlay-scrollbar-gtk2 with ayatana-indicator-messages [HISTORICAL_FACT: debdiff; research/messaging-menu/README.md:155-165]
- commits/branches: no git tree. docs/package-patches-b/debdiff/ubuntu-unity-meta_0.29+unity1.debdiff, commit `f752fb672eb781ea04e6a936c54d32bf75695668`, on origin/main [CURRENTLY_VERIFIED: C-DOCGIT]
- versions: source 0.29+unity1 (native), binary ubuntu-unity-desktop 0.29+unity1 [CURRENTLY_VERIFIED: C-APTLY]; archive resolute 0.29, stonking 0.30 [CURRENTLY_VERIFIED: C-RMADISON]
- build_state: ~/work/b/meta/out "Status: successful" [CURRENTLY_VERIFIED]
- test_state: built deb differs from archive's by exactly the two Recommends [HISTORICAL_FACT: research/messaging-menu/README.md:158-159]; `dpkg-deb -f …ubuntu-unity-desktop_0.29+unity1_amd64.deb Recommends` contains ayatana-indicator-messages and no overlay entry (count 1) [CURRENTLY_VERIFIED]; full-upgrade on target2 installed it [HISTORICAL_FACT: research:170-176]
- target_state: target2 Clean-2 after B-11 [HISTORICAL_FACT: AGENTS-LOG.md:406]
- aptly_state: source + ubuntu-unity-desktop 0.29+unity1 [CURRENTLY_VERIFIED: C-APTLY; 04-…:23]; .dsc in aptly YES; published [CURRENTLY_VERIFIED: C-PUB]
- source↔aptly match: MATCH — C-DD "MATCH" (native: full tar vs tar); aptly .dsc sha db3c9710… == ~/work/b/meta .dsc; deb == ~/work/b/meta/out (C-BIN) [CURRENTLY_VERIFIED]
- records: research/messaging-menu/README.md:155-168; DECISIONS.md:1540-1541 (within overlay-scrollbar heading 1528) and 1522 (Messaging menu heading 1498); PATCHES.md:80; status/B.md:22-31; AGENTS-LOG.md:403-406 [HISTORICAL_FACT]
- current_state: published, consistent [CURRENTLY_VERIFIED]
- gaps_unknowns: ~/work/b/meta also holds ubuntu-unity-meta_0.30 source (stonking) — only used for Rule-0 comparison [CURRENTLY_VERIFIED: ls; HISTORICAL_FACT: research:136-137]
- provenance_gap: common gap + no-git source (debdiff only)
- unfinished: none recorded.
- doubtful_fix: two independent changes in one upload (drop dead module = B-11; add messaging menu = B-10 follow-up), contrary to §4 "one defect per patch"; both are one-line list edits, low risk. The added Recommends only works with libindicator +unity2 (B-10) — a cross-package dependency not expressed in metadata (Recommends by name, no version) [HISTORICAL_FACT: debdiff changelog; research:163-165]. Not doubtful in correctness.
- proposed migration_result: **LEGACY_VERIFIED** — currently verified debdiff/aptly/binary; bundling noted.

### B-L27 — unity-lens-files: 7.1.0+17.10.20170605-0ubuntu6+unity1 (plocate / no-locate)
- legacy_id: B-L27 (collected as G3-06)
- package: unity-lens-files (binary unity-lens-files amd64) [CURRENTLY_VERIFIED: C-APTLY]
- goal: global search spawns `locate`, not installed on 26.04 → error per search. debian/control `Recommends: plocate`; src/locate.vala returns no locate results when `locate` not in PATH [HISTORICAL_FACT: debdiff changelog]
- commits/branches: no git tree. docs/package-patches-b/debdiff/unity-lens-files_+unity1.debdiff, commit `f9167f2b6b6a1ac1ad981b94bb55de4d24d0173f`, on origin/main [CURRENTLY_VERIFIED: C-DOCGIT]
- versions: source/binary 7.1.0+17.10.20170605-0ubuntu6+unity1 [CURRENTLY_VERIFIED: C-APTLY]; archive 0ubuntu6 resolute/stonking [CURRENTLY_VERIFIED: C-RMADISON]
- build_state: built 2026-09-26 14:03-14:07Z (B-5) in ~/work/b/lensfiles/out, "Status: successful"; the .changes is binary-only [CURRENTLY_VERIFIED: ls/grep]. The source used for that build was in the scratchpad and wiped by the builder reboot; the source now in aptly was **regenerated from the debdiff at 16:26Z** (~/work/b/lensfiles/src, mtime 16:26:19-20) [HISTORICAL_FACT: research/unity-scopes/README.md:120-122; CURRENTLY_VERIFIED: stat]
- test_state: target2: archive → 1 locate error per search; +unity1 without locate → 0 errors, recent files only; +unity1 + plocate 1.1.23 after updatedb → file found (lf-unity1-plocate.png) [HISTORICAL_FACT: research/unity-scopes/README.md:108-119]
- target_state: Clean-2 after B-8 [HISTORICAL_FACT: AGENTS-LOG.md:374]
- aptly_state: source + binary 0ubuntu6+unity1 [CURRENTLY_VERIFIED: C-APTLY; 04-…:28]; .dsc in aptly YES (regenerated copy); published [CURRENTLY_VERIFIED: C-PUB]; published 16:26Z [HISTORICAL_FACT: AGENTS-LOG.md:369-370]
- source↔aptly match: MATCH for content — C-DD "MATCH"; orig identical; aptly .dsc/.diff.gz sha == ~/work/b/lensfiles/src (8f20fbe0…, 3386f235…); aptly .deb == ~/work/b/lensfiles/out (14:07 build) [CURRENTLY_VERIFIED]. Byte identity of the aptly source with the source the binary was built from: NOT_CHECKABLE (original source deleted) [CURRENTLY_VERIFIED: no other copy found]
- records: research/unity-scopes/README.md:108-122 (live check); research/unity-scopes/README.md:49, 91-92 (stale: "Found, not ours … locate not installed"); status/B.md:43; AGENTS-LOG.md:345-346, 367-370, 374; 07-PENDING-MAY.md:55, 64, 68; package-patches-b/README.md. **No PATCHES.md row, no DECISIONS.md heading** [CURRENTLY_VERIFIED: grep -nE "lens|plocate" PATCHES.md / DECISIONS.md → none]
- current_state: published; content consistent with debdiff [CURRENTLY_VERIFIED]
- gaps_unknowns: missing PATCHES/DECISIONS entries; source regenerated after the binary build; stale research line 91-92 [as above]
- provenance_gap: common gap + no-git source + published source is a post-hoc regeneration, not the build input
- unfinished: none open (the `locate` finding is closed by this upload).
- doubtful_fix: two changes bundled (Recommends + code guard) (§4). The `find_program_in_path("locate") == null → return` is a guard at the call site; it is the component that spawns locate and "locate is optional" is a real invariant once it is only Recommended, so the layer is defensible; but it silently disables a configured feature (use-locate on by default) with no log hint [HISTORICAL_FACT: debdiff]. Minor.
- proposed migration_result: **LEGACY_PARTIAL** — content verified, but no PATCHES/DECISIONS record and the published source is a regeneration, not the source that produced the binary.

### B-L28 — unity-scope-{calculator,devhelp,tomboy,virtualbox,zotero}: drop shared dist-packages/__init__.py
- legacy_id: B-L28 (collected as G3-07)
- package: unity-scope-calculator 0.1+14.04.20140328-0ubuntu6+unity1; unity-scope-devhelp 0.1+14.04.20140328-0ubuntu5+unity1; unity-scope-tomboy, unity-scope-virtualbox, unity-scope-zotero 0.1+13.10.20130723-0ubuntu4+unity1 (each one `_all` binary of same name) [CURRENTLY_VERIFIED: C-APTLY]
- goal: ten Python scopes each shipped /usr/lib/python3/dist-packages/__init__.py → dpkg refuses a second; `rm -f` it in override_dh_auto_install [HISTORICAL_FACT: research/unity-scopes/README.md:19-36; debdiffs]
- commits/branches: no git tree. docs/research/unity-scopes/debdiff/unity-scope-<name>.debdiff, commit `32c4c9643202de09c0ece33c58d44921e5e1d425` (2026-09-26 13:50Z), on origin/main [CURRENTLY_VERIFIED: C-DOCGIT]
- versions: as above; archive resolute/stonking = the un-suffixed versions [CURRENTLY_VERIFIED: C-RMADISON]
- build_state: ~/work/b/scopes/results.txt EXIT 0 for all five; build logs 13:10-13:19Z [CURRENTLY_VERIFIED: cat results.txt, ls]. Build input: `scratchpad/scs/*.dsc` (buildall.sh) — no longer exists [CURRENTLY_VERIFIED: find → only aptly copies]
- test_state: all 8 Python scopes + 5 lenses + video-remote + home installed together; calculator `calc: 2*21` → 42; virtualbox answers with stub binaries; devhelp nothing to show (no books); tomboy/zotero cannot work (apps gone) [HISTORICAL_FACT: research/unity-scopes/README.md:38-39, 46-64]
- target_state: Clean-2 after B-4 [HISTORICAL_FACT: AGENTS-LOG.md:344; 07-PENDING-MAY.md:51]
- aptly_state: source + binary for each of the five, one version each [CURRENTLY_VERIFIED: C-APTLY; 04-…:29-35]; .dsc in aptly YES; published [CURRENTLY_VERIFIED: C-PUB]
- source↔aptly match: MATCH ×5 — C-DD "MATCH" for calculator, devhelp, tomboy, virtualbox, zotero; origs identical; aptly .debs == ~/work/b/scopes/out (C-BIN) [CURRENTLY_VERIFIED]. aptly .dsc vs original build input: NOT_CHECKABLE (input wiped)
- records: research/unity-scopes/README.md; DECISIONS.md:1390 "## 2026-09-26 - Unity scopes: seven +unity1, online scopes left alone (agent B)"; PATCHES.md:71; status/B.md:64-70; package-patches-b/README.md (last para); AGENTS-LOG.md:335-336, 342-343 [HISTORICAL_FACT]
- current_state: published, consistent [CURRENTLY_VERIFIED]
- gaps_unknowns: tomboy and zotero are published although they "cannot work" on 26.04 [HISTORICAL_FACT: research:61-62] — carried only to be co-installable
- provenance_gap: common gap + no-git source; build input not preserved
- unfinished (decided, not open): launchpad scope not rebuilt (tests need network; Exec=/usr/bin/python) — "left alone" per coordinator; facebook/flickr Soup 2.4/3.0 ImportError — "online, left alone"; soundcloud/yahoostock conflict with scope-home "on purpose" [HISTORICAL_FACT: research:34-36, 53-54, 63-64; DECISIONS.md:1403-1407]. Not open per records; a new task only if the decision is revisited.
- doubtful_fix: correct layer (each package ships the clashing file), mechanical packaging-only; `rm -f` tolerates absence silently (minor). No doubt.
- proposed migration_result: **LEGACY_VERIFIED** — debdiffs, aptly sources and binaries currently match; mechanical change.

### B-L29 — unity-scope-manpages: __init__.py + `gi.require_version('Gtk', '3.0')`
- legacy_id: B-L29 (collected as G3-08)
- package: unity-scope-manpages 3.0+14.04.20140324-0ubuntu5+unity1 (source + `_all` binary) [CURRENTLY_VERIFIED: C-APTLY]
- goal: (1) drop dist-packages/__init__.py; (2) PyGObject loaded GTK 4 → `IconTheme.lookup_icon(name,128,0)` TypeError on every search; require GTK 3 (package depends on gir1.2-gtk-3.0) [HISTORICAL_FACT: research/unity-scopes/README.md:72-77; debdiff]
- commits/branches: docs/research/unity-scopes/debdiff/unity-scope-manpages.debdiff, commit `32c4c9643202de09c0ece33c58d44921e5e1d425`, origin/main [CURRENTLY_VERIFIED]
- versions: as above; archive 0ubuntu5 [CURRENTLY_VERIFIED: C-RMADISON]
- build_state: rebuilt 13:40Z (manpages-2.log; build log T13:40:07Z "Status: successful"), results.txt EXIT 0 [CURRENTLY_VERIFIED]
- test_state: `man: printf` → 25 results in Dash, with and without DISPLAY; before: none, TypeError [HISTORICAL_FACT: research:57, 77]
- target_state: Clean-2 after B-4 [HISTORICAL_FACT: AGENTS-LOG.md:344]
- aptly_state: source + binary, one version [CURRENTLY_VERIFIED: C-APTLY]; published [C-PUB]
- source↔aptly match: MATCH — C-DD; orig identical; .deb == ~/work/b/scopes/out [CURRENTLY_VERIFIED]
- records: research/unity-scopes/README.md:57, 70-77; DECISIONS.md:1397-1398; PATCHES.md:71; status/B.md:67 [HISTORICAL_FACT]
- current_state: published, consistent [CURRENTLY_VERIFIED]
- gaps_unknowns: none beyond common.
- provenance_gap: common gap + no-git source; build input wiped
- unfinished: none.
- doubtful_fix: exact mechanism (unversioned `gi` import picks GTK4; API arity), fixed in the importing module = correct layer, 2 lines. Bundled with the __init__.py change in one upload (§4), no automated regression test. No correctness doubt.
- proposed migration_result: **LEGACY_VERIFIED** — currently verified; bundling noted.

### B-L30 — unity-scope-gnote: __init__.py + 3 s retry while Gnote activates
- legacy_id: B-L30 (collected as G3-09)
- package: unity-scope-gnote 0.1+13.10.20130723-0ubuntu4+unity1 (source + `_all` binary) [CURRENTLY_VERIFIED: C-APTLY]
- goal: (1) drop dist-packages/__init__.py; (2) search while Gnote not running: D-Bus activation starts `gnote --shell-search`, but `/org/gnome/Gnote/RemoteControl` is not yet registered → UnknownMethod; wrap SearchNotes/ListAllNotes in 15 × 0.2 s retry [HISTORICAL_FACT: research/unity-scopes/README.md:79-87; debdiff]
- commits/branches: docs/research/unity-scopes/debdiff/unity-scope-gnote.debdiff, commit `32c4c9643202de09c0ece33c58d44921e5e1d425`, origin/main; helper research/unity-scopes/gnote_fix.py [CURRENTLY_VERIFIED]
- versions: as above; archive 0ubuntu4 [CURRENTLY_VERIFIED: C-RMADISON]
- build_state: rebuilt 13:43Z (gnote-2.log; T13:43:07Z build "Status: successful"; "Ran 2 tests … OK") [CURRENTLY_VERIFIED]
- test_state: `gnote: B4probe` → note found with Gnote not running (gnote-note.png) [HISTORICAL_FACT: research:58, 86-87]. No automated regression test; the package's 2 tests do not cover this [UNVERIFIED that they don't; test names not inspected]
- target_state: Clean-2 after B-4 [HISTORICAL_FACT: AGENTS-LOG.md:344]
- aptly_state: source + binary, one version [CURRENTLY_VERIFIED]; published [C-PUB]
- source↔aptly match: MATCH — C-DD; orig identical; .deb == ~/work/b/scopes/out [CURRENTLY_VERIFIED]
- records: research/unity-scopes/README.md:58, 79-87; DECISIONS.md:1399-1400; PATCHES.md:71; status/B.md:68 ("gnote starts Gnote correctly"); AGENTS-LOG.md:343 ("gnote activation retry"); 07-PENDING-MAY.md:51 ("gnote activation race") [HISTORICAL_FACT]
- current_state: published, consistent [CURRENTLY_VERIFIED]
- gaps_unknowns: the mechanism "Gnote 49 registers RemoteControl only once it is up" is asserted, not traced in Gnote source (no code reference, no bus trace in the research) [HISTORICAL_FACT: research:83-85; UNVERIFIED]. research:84-85 also says the `--shell-search` instance "quits when idle, so every later search failed the same way" — implies every cold search pays the activation delay again [HISTORICAL_FACT].
- provenance_gap: common gap + no-git source; build input wiped
- unfinished: none recorded open.
- doubtful_fix: **yes.** D-Bus activation completes when the service owns its bus name; if Gnote owns `org.gnome.Gnote` before exporting `/org/gnome/Gnote/RemoteControl`, that is a registration-ordering defect in Gnote (the owner of the invariant "name owned ⇒ object callable"), and a consumer-side retry is the "defensive workaround at a convenient call site" §2/§4 reject unless evidence shows the consumer owns the failure. No correct_layer / defensive_workaround_rejected record; Gnote upstream/Debian not searched for this (no Rule-0 entry for gnote itself) [HISTORICAL_FACT: research:79-87]. Implementation: blocking `time.sleep` inside the search path (up to 3 s), catches every `GLib.Error` (not only UnknownMethod), magic 3 s bound; bundled with the __init__ change.
- proposed migration_result: **REQUIRES_REVALIDATION** — works as measured, but root-cause mechanism unproven and fix is at the consumer instead of Gnote's registration order.

### B-L31 — session-migration: B's debdiff (published by agent A)
- legacy_id: B-L31 (collected as G3-10)
- package: session-migration 0.3.9build2+unity1 [CURRENTLY_VERIFIED: C-APTLY]
- goal (B's part): CMake 4 (`cmake_minimum_required` 3.10) + test regex `re.escape` for build paths containing `+` [HISTORICAL_FACT: debdiff; research/rebuild-loss/README.md:33]
- commits/branches: B: docs/package-patches-b/debdiff/session-migration_+unity1.debdiff, commit `f9167f2b6b6a1ac1ad981b94bb55de4d24d0173f`, origin/main [CURRENTLY_VERIFIED: C-DOCGIT]. A: packages/session-migration `unity/resolute` = `35f62a312de8262b043cd2fe2d04ed25ff892fe9` on base `d8d054d34cde9c20314e79e8432b77c640a4fd4c`, pushed: `git ls-remote lifesupport` → refs/heads/unity/resolute 35f62a3 (github Ubuntu-Unity-LifeSupport/session-migration) [CURRENTLY_VERIFIED]; commit time 17:31:40Z matches A-6 "repos pushed" [HISTORICAL_FACT: AGENTS-LOG.md:394]. `git diff d8d054d 35f62a3` +/- lines == debdiff +/- lines ("SM_BODY_MATCH") [CURRENTLY_VERIFIED]
- versions: binary session-migration_0.3.9build2+unity1_amd64 only in aptly [CURRENTLY_VERIFIED: C-APTLY]; archive 0.3.9build2 resolute/stonking [CURRENTLY_VERIFIED: C-RMADISON]
- build_state: B trial build ~/work/b/b7fix: results.txt rc=2, results2.txt rc=0 (after regex fix) [CURRENTLY_VERIFIED: grep]; A's build ~/work/a/sm [HISTORICAL_FACT: AGENTS-LOG.md:381]. A's and B's `.dsc`/tar.xz differ in bytes (native repack), but the published .deb sha256 d9988186… equals BOTH ~/work/a/sm and ~/work/b/b7fix/out-session-migration_0.3.9build2+unity1 debs [CURRENTLY_VERIFIED: sha256sum]
- test_state: 9/9 tests; migration ran at first login, skipped at second (A) [HISTORICAL_FACT: DECISIONS.md:1482-1486; PATCHES.md:74]
- target_state: A's target "= aptly" [HISTORICAL_FACT: AGENTS-LOG.md:394] — A's scope
- aptly_state: binary only; **source not in aptly**; `dh-migrations` binary built by A (~/work/a/sm) not in aptly [CURRENTLY_VERIFIED: C-APTLY; ls ~/work/a/sm]
- source↔aptly match: B's debdiff == pushed git diff (MATCH) and published .deb == B's own build (MATCH) [CURRENTLY_VERIFIED]; source-in-aptly: NOT_APPLICABLE (absent)
- records: package-patches-b/README.md ("published by agent A"); PATCHES.md:74 ("Prepared by agent B … built and verified by agent A"); DECISIONS.md:1480 (A-6, agent A); research/rebuild-loss/README.md:33 (stale: "not in aptly; nobody owns it"); status/B.md:56 (stale: "built, not published"); AGENTS-LOG.md:380-394 (A) [HISTORICAL_FACT]
- current_state: published by A; B's contribution consistent with it [CURRENTLY_VERIFIED]
- gaps_unknowns: two stale B records (rebuild-loss:33, status/B.md:56) [HISTORICAL_FACT]
- provenance_gap: common gap (A's publication) + source not in aptly — belongs to A's reconciliation
- unfinished: none for B.
- doubtful_fix: CMake bump is mechanical; `re.escape` fixes the test (the bug is in the test regex) — correct layer, test-only change. No doubt.
- proposed migration_result: **LEGACY_VERIFIED (B's part only)** — B's debdiff equals A's pushed commit and the published binary; publication gaps to be reconciled under agent A.

### B-L32 — gtk-nocsd: 4.8-1+unity2, /etc/X11/Xsession.d/51gtk-nocsd for Xsession-started desktops (B)
- legacy_id: B-L32 (collected as G4-03)
- package: gtk-nocsd
- goal: Xfce/MATE/LXQt/WMs started via Xsession without systemd user manager did not load gtk-nocsd (4.8-1 uses environment.d only, dropped gtk3-nocsd Xsession scripts) [HF: D/research/nocsd-gaps/README.md:253-266; changelog a492994]
- commits/branches: a4929940dc51f19cf2e8c56c242df843d5b29436 on unity/resolute; on lifesupport [CV: `git branch -r --contains a492994` -> lifesupport/unity/resolute]; commit 23:27:30Z, push 23:27:58Z [CV: reflog] — build started 23:19Z from uncommitted tree [HF: AGENTS-LOG.md:284; changelog trailer 23:19:37]
- versions: 4.8-1+unity2 / libgtk-nocsd0, gtk3-nocsd, libgtk3-nocsd0 4.8-1+unity2 [CV-aptly]
- build_state: sbuild resolute, Status: successful 2026-09-25T23:22:46Z [CV: `grep Status ~/work/b/nocsd-u2/out/*.build`]
- test_state: Xfce 4.20 + Unity on target2 via /proc environ/maps (tests/xs.sh) [HF: nocsd-gaps/README.md:282-289]. Unity measurement had only `libgtk-nocsd.so.0` in LD_PRELOAD even with +unity1 (row 287) => unity-gtk4-menu was not installed, so the regression below could not show [HF: nocsd-gaps/README.md:287-289; INFERENCE]
- target_state: target2 rolled back to Clean-2 afterwards [HF: AGENTS-LOG.md:290]; now UV
- aptly_state: source + 3 binaries present; **dbgsym 4.8-1+unity2 not in aptly** though built (~/work/b/nocsd-u2/out/libgtk-nocsd0-dbgsym_4.8-1+unity2_amd64.ddeb) [CV-aptly; `find /srv/aptly/pool -name '*dbgsym_4.8-1+unity2*'` -> none]
- source↔aptly match: MATCH — aptly .dsc sha256 249dc1b0…, debian.tar.xz 00f5d056… == ~/work/b/nocsd-u2 files; debian/ == git a492994 [CV-cmp; `sha256sum`]. Binaries: 3 .deb in aptly byte-identical to ~/work/b/nocsd-u2/out [CV: sha256 compare]
- records: DECISIONS.md:1263 (bullet 1286-1291); PATCHES.md:65; nocsd-gaps/README.md:253-305; status/B.md:113-115; AGENTS-LOG.md:284-286
- current_state: superseded by +unity3; still in aptly (not candidate)
- gaps_unknowns: Debian not informed (nothing filed) [HF: nocsd-gaps/README.md:304-305]
- provenance_gap: no build manifest / release gate / version_safety record / aptly snapshot (§6); published before commit was pushed (publish DONE 23:27Z, push 23:27:58Z) [HF: AGENTS-LOG.md:286; CV reflog]; target check was on dpkg/aptly setup mixture, not normal upgrade path — UV exactly
- unfinished: none separate (see G4-04)
- doubtful_fix: introduced regression: exported `LD_PRELOAD=libgtk-nocsd.so.0` in every Xsession, which `95dbus_update-activation-env --all` pushed to the systemd user manager, overwriting the environment.d list and dropping libunity-gtk4-menu.so.0 in Unity sessions [HF: D/research/hud/README.md:106-119]. §2: invariant "environment.d is the single preload list" not stated; no root_cause/correct_layer card. §4: verification too narrow (Unity check lacked unity-gtk4-menu). Shipped a behaviour regression to the default desktop.
- proposed migration_result: SUPERSEDED — replaced by +unity3; regression recorded

### B-L33 — gtk-nocsd: 4.8-1+unity3, 51gtk-nocsd seeds LD_PRELOAD from the systemd user manager (B, current)
- legacy_id: B-L33 (collected as G4-04)
- package: gtk-nocsd
- goal: fix +unity2 regression (GTK4 global menu/HUD lost in Unity) while keeping Xfce coverage [HF: hud/README.md:106-128; changelog a2a0747]
- commits/branches: a2a074786f6139a82d08f88f4aa42f35fb0a8e7a on unity/resolute == lifesupport/unity/resolute [CV-lsr]; commit 19:37:09Z, pushed 20:53:46Z [CV: reflog]; docs 1d8a88d70ded086b29ebb2f0178473e2243be741 (on origin/main of meta-repo) [CV: `git branch -r --contains 1d8a88d`]
- versions: 4.8-1+unity3 / libgtk-nocsd0, libgtk-nocsd0-dbgsym, gtk3-nocsd, libgtk3-nocsd0 4.8-1+unity3 [CV-aptly]
- build_state: sbuild resolute, Status: successful 2026-09-26T19:39:31Z [CV: grep ~/work/b/nocsd-u3/out/*.build]
- test_state: 4-case simulation with stand-in systemctl (script not committed) [HF: hud/README.md:131-134; CV: `grep -rl show-environment D/research` finds no sim script]; Unity on target2: user manager, compiz, u-p-s, hud-service carry `libunity-gtk4-menu.so.0:libgtk-nocsd.so.0`, panel menu + HUD [HF: hud/README.md:135-141]; Xfce: **minimal** xfce4-session/xfwm4/panel install [HF: hud/README.md:142-149]. Install method on target2: Clean-2 → our aptly (then holding +unity2) → full-upgrade, then `dpkg -i libgtk-nocsd0_4.8-1+unity3_amd64.deb` from the build dir, reboot, checks; published to aptly only afterwards; no check through the normal apt upgrade path after publication [HISTORICAL_FACT: agent B's own session 2026-09-26 ~19:40-19:56Z, stated by the implementer; not separately recorded in research/hud]
- target_state: target2 back on Clean-2 [HF: AGENTS-LOG.md:414]; now UV
- aptly_state: source + 4 binaries present; current candidate in repo [CV-aptly; D/../migration 04-aptly-latest-by-source.txt:6 "latest=4.8-1+unity3 versions=4"]
- source↔aptly match: MATCH — aptly .dsc sha256 29913efa…, debian.tar.xz 02a38aa1… == ~/work/b/nocsd-u3; debian/ == git a2a0747; all 4 binaries byte-identical to ~/work/b/nocsd-u3/out [CV-cmp; sha256]. `debian/51gtk-nocsd` == D/research/nocsd-gaps/tests/51gtk-nocsd [CV: `diff -q`]. debian/patches/series empty [CV]
- records: DECISIONS.md:1567 (bullets 1586-1593); PATCHES.md:83; hud/README.md:106-149; nocsd-gaps/README.md:350-358; status/B.md:17-19; STATUS.md:314-316; PENDING-MAY.md:76 (May approval 19:35Z); AGENTS-LOG.md:413-414
- current_state: live in aptly; version vs archive: > resolute 0~20260321+0b77e1b-1 and > stonking 4.8-1 [CV-madison + dpkg ordering INFERENCE] — note it will also outrank 26.10's 4.8-1 on release upgrade
- gaps_unknowns: (1) path "session already has LD_PRELOAD" still exports a list without environment.d's other libraries and overwrites the user manager's list — only simulated, not measured [INFERENCE from script, a2a0747:debian/51gtk-nocsd]; (2) Xfce now also inherits unity-gtk4-menu from environment.d when installed — checked only on minimal Xfce; MATE/LXQt/WMs untested UV; (3) relies on user manager having applied environment.d before Xsession (pam_systemd) — assumed, not documented; (4) which package ships 95dbus_update-activation-env on resolute UV (not on builder: `dpkg -S` no match)
- provenance_gap: no build manifest / release gate / version_safety / aptly snapshot (§6); no AGENTS-LOG START/DONE publish line for +unity3 (only line 414 summary) [CV: `grep -n unity3 ~/AGENTS-LOG.md`]; pushed after publish (push 20:53:46Z; publish time UV); target check via dpkg -i before publication, not the normal upgrade path -> does not meet the §6 target gate [HISTORICAL_FACT: implementer]
- unfinished: NEW TASK — re-verify +unity3 on a clean target via apt full-upgrade (Unity with unity-gtk4-menu; full Xfce; one more Xsession desktop); commit the systemctl stand-in simulation as a test; decide whether to offer the Xsession script to Debian (salsa ubports-team)
- doubtful_fix: root_cause_mechanism is proven (script-moved-aside reboot proof, hud/README.md:117-119). correct_layer: the clobber is caused by our own script feeding 95dbus; fixing in our script is the right package — changing the `--all` import in 95dbus (dbus's file, working as designed) would be the wrong layer. But the chosen mechanism (read `systemctl --user show-environment` inside Xsession) is a merge-by-readback that only runs when session LD_PRELOAD is empty; the more direct invariant ("Xsession must not export a preload list narrower than environment.d's") is not enforced in the non-empty case. Not a defensive null-guard; acceptable but incomplete. No §2 evidence card, no Design Challenger, no committed regression test (§4). +unity2 had shipped a regression; +unity3's verification (dpkg -i, minimal Xfce) is again narrower than §5/§6 require.
- proposed migration_result: REQUIRES_REVALIDATION — source/aptly match, mechanism sound, but target gate (apt upgrade path) and non-Unity desktops never verified

### B-L34 — gtk-nocsd: unity-gtk4-menu merged into gtk-nocsd 4.8 (experiment, nocsd-merge)
- legacy_id: B-L34 (collected as G4-05)
- package: gtk-nocsd
- goal: one preload instead of two (May asked) [HF: DECISIONS.md:1122-1139]
- commits/branches: b/global-menu cafe5a2842f702d48f89937989792c419f8a4236 in ~/work/b/nocsd-merge/pkg — local only [CV: `git branch -r --contains` empty]
- versions: 4.8-1+unity2~menu1 (source + binaries in ~/work/b/nocsd-merge/build) [CV: ls]
- build_state: sbuild [HF: AGENTS-LOG.md:224]
- test_state: target2 dpkg -i, 18/18 apps [HF: DECISIONS.md:1128-1133; AGENTS-LOG.md:225-226]
- target_state: target2 later rolled back to Clean-2 [HF: AGENTS-LOG.md:242]
- aptly_state: absent [CV: `aptly repo search unity-resolute '$Version (% *menu*)'` -> no results]
- source↔aptly match: n/a. Research copy: D/research/nocsd-merge/packaging.diff == `git diff origin/unity/resolute b/global-menu` minus global-menu.patch; global-menu.patch identical [CV: diff -q]
- records: DECISIONS.md:1122; research/nocsd-merge/; status/B.md:138
- current_state: experiment, deliberately not taken [HF: DECISIONS.md:1135-1139]
- gaps_unknowns: none
- provenance_gap: branch local only
- unfinished: none (superseded by G4-06 upstream route)
- doubtful_fix: n/a (not shipped); decision to not carry a 1250-line patch is consistent with §4
- proposed migration_result: SUPERSEDED — replaced by upstream-main port (G4-06)

### B-L35 — gtk-nocsd: global menu as upstream patch on main 6b1f70a (nocsd-upstream / nocsd-desktops)
- legacy_id: B-L35 (collected as G4-06)
- package: gtk-nocsd (upstream codeberg MorsMortium/gtk-nocsd)
- goal: desktop-neutral global menu export (gtk-shell-shows-menubar switch, GTK_NOCSD_NO_GLOBAL_MENU) in upstream style [HF: DECISIONS.md:1141-1156]
- commits/branches: global-menu d335007dea33dbdb54267d9ae601fe85755b8cd0 (~/work/b/nocsd-up/src), base main 6b1f70ab9f25a57be071262aee76091f4b4cc1a4; menu b4af04065c59687360af70427fb97014957112ab (checkpoint); packaging b/global-menu-up 88bdc15a95610a203d041eb64557877b62f71cbd (~/work/b/nocsd-merge/pkg) — all local only [CV: `git branch -r --contains` empty]
- versions: 4.8+git20260924.6b1f70a-1+unity2~menu2..~menu5 (local builds ~/work/b/nocsd-up/build) [CV: ls]
- build_state: built; 0 warnings under upstream flags [HF: DECISIONS.md:1148-1149]
- test_state: target2 dpkg -i, 18/18; Xfce 4.20 + Plasma 6.6.4 X11 work only with flag set [HF: DECISIONS.md:1150-1153,1158-1170; AGENTS-LOG.md:229-242]
- target_state: rolled back to Clean-2 [HF: AGENTS-LOG.md:242]
- aptly_state: absent [CV: aptly search *menu* -> none]
- source↔aptly match: n/a. D/research/nocsd-upstream/0001-…patch == `git format-patch -1 d335007` (diff body) [CV]; research packaging.diff == branch diff except it omits the debian/patches/series hunk [CV: diff]
- records: DECISIONS.md:1141, 1158; research/nocsd-upstream/, research/nocsd-desktops/; status/B.md:130-138
- current_state: not sent; superseded in content by split series (G4-08)
- gaps_unknowns: codeberg main moved to e817d809… [CV-upstream]; applicability UV; experimental versions 4.8+git… sort above 4.8-1+unity3 (any host still holding them would not take +unity3) [INFERENCE]
- provenance_gap: local only, not pushed anywhere
- unfinished: covered by G4-08
- doubtful_fix: n/a (not shipped)
- proposed migration_result: SUPERSEDED — replaced by split-parts-2

### B-L36 — gtk-nocsd: split-parts (4-commit split for maintainer reply #2, nocsd-reply2)
- legacy_id: B-L36 (collected as G4-07)
- package: gtk-nocsd upstream
- goal: split patch into base/(a)/(b)/(c); measurements for reply #2 [HF: DECISIONS.md:1241-1261]
- commits/branches: split-parts in ~/work/b/nocsd-up/split: cec5dbc07f1ccad7b998e526e6fbd7f504fcbadc, 65368e4e8c130c362d055e370d615373d24289c7, c6ebae0213a31064606865dbcd4b090a12a78e4d, cbb5ca84e19d7cd7a0604d3acd70972441bf0d48 — local only [CV]
- versions: none packaged (exp. ~menu5flat1 is G4-09)
- build_state: all combinations build [HF: DECISIONS.md:1253-1254]
- test_state: 44-app audit on target2 [HF: nocsd-reply2/README.md:37-57]
- target_state: rolled back to Clean-2 [HF: status/B.md:122]
- aptly_state: absent
- source↔aptly match: n/a; D/research/nocsd-reply2/patches/0001-0004 == the 4 commits [CV: format-patch diff]
- records: DECISIONS.md:1241; research/nocsd-reply2/; status/B.md:117-122
- current_state: superseded by split-parts-2
- gaps_unknowns: none
- provenance_gap: local only
- unfinished: none
- doubtful_fix: n/a
- proposed migration_result: SUPERSEDED — by split-parts-2

### B-L37 — gtk-nocsd: split-parts-2 (5-commit series incl. inserted groups + part (d), nocsd-gaps)
- legacy_id: B-L37 (collected as G4-08)
- package: gtk-nocsd upstream
- goal: close reply2 gaps: inserted action groups (a), late/live menus (d) [HF: DECISIONS.md:1263-1285; nocsd-gaps/README.md:9-28]
- commits/branches: split-parts-2 in ~/work/b/nocsd-up/split: 23e91cb9a7e34e432ead039a8fa8812bb818189f, d694107dac2e73d323f6d8e29ddbae778cd00cac, 5597fb90244da689fe6060dbec2ba0c7f54c255f, 2cfbec6b35fb294ec6ffa6885b2bb0a49ccbd0ea, a45085383e2e8724ab96c697d49a4b0d2dcf313d — local only [CV]
- versions: none in aptly
- build_state: 16 combinations 0 warnings [HF: nocsd-gaps/README.md:20-22]
- test_state: 44 apps, 10 dead items -> 0 [HF: DECISIONS.md:1275]
- target_state: rolled back to Clean-2 [HF: AGENTS-LOG.md:290]
- aptly_state: absent
- source↔aptly match: n/a; D/research/nocsd-gaps/split/patches/0001-0005 == the 5 commits [CV]
- records: DECISIONS.md:1263; research/nocsd-gaps/; status/B.md:94-102
- current_state: ready, not sent; base 6b1f70a is stale vs codeberg main e817d809… [CV-upstream]
- gaps_unknowns: rebase conflicts vs new main UV; GTK3/button hiding/per-window only estimated [HF: DECISIONS.md:1283]
- provenance_gap: local only (not pushed to lifesupport or any fork); only patch copies in meta-repo
- unfinished: NEW TASK — rebase on current main and (if May approves) submit; blocked on May / C-L01
- doubtful_fix: n/a (not shipped)
- proposed migration_result: LEGACY_PARTIAL — measured work, unsubmitted, stale base

### B-L38 — gtk-nocsd: exp-flat (holder vs flat menubar experiment)
- legacy_id: B-L38 (collected as G4-09)
- package: gtk-nocsd upstream
- goal: measure flat menubar vs holder menu [HF: DECISIONS.md:1245-1247]
- commits/branches: exp-flat b0424de42ddf26f33b73e3bee981ac271b518580 (~/work/b/nocsd-up/flat); b/exp-flat 619cda8bb7f23ad48b67dab7f4d698d4cd6bb30e, 071b69e0c087b1d145c74558eec46caa43b0e9dd (~/work/b/nocsd-merge/pkg) — local only [CV]
- versions: 4.8+git20260924.6b1f70a-1+unity2~menu5flat1 (local) [CV: ls]
- build_state/test_state: target2 [HF: AGENTS-LOG.md:258]
- target_state: Clean-2 afterwards UV
- aptly_state: absent
- source↔aptly match: n/a
- records: research/nocsd-reply2/ §1
- current_state: rejected variant (holder chosen)
- gaps_unknowns/provenance_gap: local only
- unfinished: none
- doubtful_fix: n/a
- proposed migration_result: SUPERSEDED — experiment concluded

### B-L39 — gtk-nocsd upstream: Epiphany Passwords abort on main (first bad 8f076dd) + fix
- legacy_id: B-L39 (collected as G4-10)
- package: gtk-nocsd upstream (not in our 4.8) [HF: nocsd-epiphany-crash/README.md:7-8]
- goal: bisect + minimal fix
- commits/branches: fix-dialog-title 2cfc8f1d1f65a738dc7092edc1d9201fc318819b on main 6b1f70a, in repo ~/work/b/nocsd-up/src; its worktree (scratchpad/fix) no longer exists, listed "prunable" [CV: `git worktree list`]; local only [CV]
- versions: none
- build_state: 0 warnings, upstream Uncrustify [HF: README.md:117-120]
- test_state: bisect 21 commits; reproducer tests/dialogtitle.c; with fix 3/3 alive, clock mode kept [HF: README.md:14-27,98-133]; Mahjongg itself not tested [HF: README.md:133-134]
- target_state: Clean-2 after [HF: AGENTS-LOG.md:297]
- aptly_state: n/a (our 4.8 unaffected)
- source↔aptly match: n/a; research 0001-Keep-the-header-title-of-LibAdwaita-dialogs.patch == `git format-patch -1 2cfc8f1` [CV]
- records: research/nocsd-epiphany-crash/ (commit 6f5577d06fea82ea84b0005ae876c04f932e6b54); nocsd-gaps/README.md:308-313; status/B.md:100,108-110; PENDING-MAY.md:22-26
- current_state: not reported, not sent; whether main e817d809… still has it UV
- gaps_unknowns: upstream may have fixed it since 6b1f70a UV
- provenance_gap: fix branch local only; worktree lost (commit survives in repo)
- unfinished: NEW TASK — recheck on current main; report/offer fix per May decision
- doubtful_fix: fix targets the mechanism (restricts 8f076dd's rule to header labels, guards size request on Parent), not a bare null guard; second hunk (size only when Parent) is partly defensive but justified by bd1c1bc path [HF: README.md:84-96] — acceptable
- proposed migration_result: LEGACY_PARTIAL — finding solid, unsent, base stale

### B-L40 — gtk-nocsd upstream: other findings (types-never-fetched; gnome-sound-recorder)
- legacy_id: B-L40 (collected as G4-11)
- package: gtk-nocsd upstream
- goal: record upstream bugs
- commits/branches: none (tests in research/nocsd-reply2/tests)
- versions: types bug reproduced on main 6b1f70a; sound-recorder crash fixed by 4.8 [HF: nocsd-reply2/README.md:137-154]
- build_state/test_state: reproducer typesorder.c + trace.gdb [HF: same]
- target_state/aptly_state: n/a
- source↔aptly match: NOT_CHECKED (n/a)
- records: DECISIONS.md:766-772, 1258-1259; nocsd-reply2/README.md:137-159
- current_state: not reported [HF: PENDING-MAY.md:24-26]
- gaps_unknowns: state on current main UV
- provenance_gap: none beyond not reported
- unfinished: NEW TASK (with G4-10) — recheck + report types bug if May lifts hold
- doubtful_fix: n/a
- proposed migration_result: LEGACY_PARTIAL — sound-recorder item closed by 4.8; types item open

### B-L41 — gtk-nocsd (Debian packaging): environment.d does not reach Xfce
- legacy_id: B-L41 (collected as G4-12)
- package: gtk-nocsd (Debian 4.8-1)
- goal: record Debian packaging gap [HF: nocsd-desktops/README.md; nocsd-gaps/README.md:253-305]
- commits/branches: fix carried as G4-03/G4-04
- versions/build/test/target/aptly: see G4-04
- source↔aptly match: see G4-04
- records: DECISIONS.md:1169-1170, 1286-1291; PATCHES.md:65
- current_state: fixed locally only; nothing filed to Debian/LP [HF: nocsd-gaps/README.md:268-271,302-305]
- gaps_unknowns: 26.10 same (4.8-1) [CV-madison]
- provenance_gap: n/a
- unfinished: include in G4-04 follow-up (offer to salsa) — May's call
- doubtful_fix: see G4-04
- proposed migration_result: LEGACY_PARTIAL — local fix only, depends on G4-04 revalidation

### B-L42 — gtk-nocsd: issue #1 (MorsMortium) reply #2 — facts only (C owns draft, C-L01)
- legacy_id: B-L42 (collected as G4-13)
- package: gtk-nocsd / unity-gtk4-menu
- goal: B supplied facts; C owns draft v4 ~/coordinator/gtk-nocsd-reply2-draft.md [HF: PENDING-MAY.md:22-26; MIGRATION-20260927.md:37]
- commits/branches: facts rest on G4-06..G4-11 (base 6b1f70a)
- aptly_state: n/a
- source↔aptly match: n/a
- records: DECISIONS.md:1241-1261; research/nocsd-reply2/, nocsd-gaps/, nocsd-epiphany-crash/
- current_state: not sent, waits for May [HF]
- gaps_unknowns: upstream main moved (6b1f70a -> e817d809…) [CV-upstream]; B's facts need recheck before sending
- provenance_gap: n/a
- unfinished: under C-L01 (no new B ID; B recheck step when C schedules)
- doubtful_fix: n/a
- proposed migration_result: LEGACY_PARTIAL — as C-L01; B facts dated 2026-09-26

### B-L43 — vala-panel: FTBFS in resolute, left alone
- legacy_id: B-L43 (collected as G5-01)
- package: src:vala-panel 24.05-3 (libvalapanel0)
- goal/finding: trial rebuild of never-built section-B sources; vala-panel FTBFS (`launchbar-button.vala:143/146: The name 'launch' does not exist`), cause GioUnix-2.0 GIR move drops `vala_panel_launch` from vapi; Debian #1118323; fixed upstream master 5e821ba2/82005703, unreleased; Unity does not use libvalapanel0 → not patched [HISTORICAL_FACT: research/rebuild-trial/README.md:20,52-70; DECISIONS.md:1214-1216; status/B.md:126; STACK-HEALTH.md:92]
- where recorded: research/rebuild-trial/README.md:52-70; DECISIONS.md:1198-1216; build log dir ~/work/b/rebuild/out-vala-panel
- evidence type: reproduced (sbuild, 191 s attempt) [HISTORICAL_FACT: research/rebuild-trial/results.txt:9]; "Unity does not use it" = read in code/deps
- current_state: open upstream / closed for us (decided out of scope). Archive still 24.05-3 in resolute and stonking [CURRENTLY_VERIFIED: `rmadison -s resolute,stonking vala-panel libvalapanel0`]; nothing of ours in aptly [CURRENTLY_VERIFIED: `aptly repo search unity-resolute 'Name (% vala-panel*)'` → no results]
- gaps_unknowns: whether any Unity-flavour seed pulls libvalapanel0 (only asserted via appmenu plugins for Xfce/MATE/Budgie) [UNVERIFIED]
- unfinished: no new task — not a Unity defect.
- doubtful: none material.
- proposed migration_result: LEGACY_VERIFIED — FTBFS was reproduced in sbuild; archive state unchanged today.

### B-L44 — overlay-scrollbar: "dead" (FTBFS, dead GTK2 module)
- legacy_id: B-L44 (collected as G5-02)
- package: src:overlay-scrollbar 0.2.17.1+16.04.20151117-0ubuntu5
- goal/finding: rebuild-loss survey listed it as FTBFS (needs Ubuntu's old GTK patch `ubuntu_gtk_*_use_overlay_scrollbar`), "dead", "list only", no owner [HISTORICAL_FACT: research/rebuild-loss/README.md:105; DECISIONS.md:1450-1452]. Then found it kills GTK2 clients via session-wide `GTK2_MODULES` (undefined `ubuntu_gtk_set_use_overlay_scrollbar`) [HISTORICAL_FACT: research/messaging-menu/README.md:102-116]
- where recorded: research/rebuild-loss/README.md:105; research/messaging-menu/README.md:102-116,131-186; DECISIONS.md:1528-1555
- evidence type: reproduced (sbuild FTBFS; Pidgin module error on target2)
- current_state: SUPERSEDED by B-11 — `overlay-scrollbar 0ubuntu5+unity1` stub (no module, `rm_conffile 81overlay-scrollbar`) + ubuntu-unity-meta 0.29+unity1; measured by full-upgrade from Clean-2 [HISTORICAL_FACT: DECISIONS.md:1528-1555; status/B.md:22-30]. Stub in aptly [CURRENTLY_VERIFIED: `aptly repo search unity-resolute 'Name (% overlay-scrollbar*)'` → 0ubuntu5+unity1 source/all/amd64]
- gaps_unknowns: none for the stub; unity-tweak-tool still reads the kept schemas (asserted) [HISTORICAL_FACT: research/messaging-menu/README.md:~150]
- unfinished: no.
- doubtful: rebuild-loss/README.md:105 says "deleted from resolute" — overlay-scrollbar and overlay-scrollbar-gtk2 0ubuntu5 are still published in resolute and stonking [CURRENTLY_VERIFIED: `rmadison -s resolute,stonking overlay-scrollbar overlay-scrollbar-gtk2`]. Wording likely meant the no-change rebuild in -proposed; as written it is wrong/ambiguous.
- proposed migration_result: SUPERSEDED — replaced by the B-11 stub (itself measured).

### B-L45 — hud / LibreOffice: intermittent empty HUD
- legacy_id: B-L45 (collected as G5-03)
- package: hud 14.10+17.10.20170619-0ubuntu6(+unity1); LibreOffice 26.2 Writer
- goal/finding: HUD empty for ~half of Writer starts: archive 10/15 OK, ours 11/24 OK → not introduced by rebuild. Two mechanisms: (1) window-stack-bridge drops the window when bamf has not exported the app yet (`DesktopFile()` UnknownMethod → `m_error`, never added, no retry; 1 run each build); (2) window known, full properties seen via dbus-monitor, but GMenu collection yields nothing — not traced. Side: app id from `QFileInfo::baseName()` → reverse-DNS desktop files become `org` (called harmless) [HISTORICAL_FACT: research/hud/README.md:68-104]
- where recorded: research/hud/README.md:68-104 (scripts lo3.sh, ht.sh); DECISIONS.md:1567-1584; STATUS.md:318-319; status/B.md:14
- evidence type: measured (counts) for the gap; mechanism 1 read in code + journal; mechanism 2 partially traced; `org` id read in code
- current_state: open (recorded, not fixed; automatic mode stopped during B-12) [HISTORICAL_FACT: DECISIONS.md:1580-1584]. hud +unity1 in aptly [CURRENTLY_VERIFIED: `aptly repo search unity-resolute 'Name (% hud*)'`]; archive unchanged 0ubuntu6 [CURRENTLY_VERIFIED: `rmadison hud`]
- gaps_unknowns: mechanism 2 root cause; ratio split between mechanisms (1 run each vs "the other failures"); `org` id impact on HUD ranking/matching not measured [UNVERIFIED]
- unfinished: candidate for a UNITY-* task (real open user-visible defect listed in STATUS known limitations; mechanism 1 has a proposed fallback in the record).
- doubtful: "harmless" for the `org` app id is asserted, not measured; samples small (15/24) — "within noise" claim is reasonable but not statistically tested.
- proposed migration_result: LEGACY_PARTIAL — gap measured on both builds; cause only half traced.

### B-L46 — appmenu: GTK2 applications have no global menu
- legacy_id: B-L46 (collected as G5-04)
- package: appmenu-gtk-module (GTK2 build `appmenu-gtk2-module` absent)
- goal/finding: GTK2 apps (Pidgin) log `Failed to load module "appmenu-gtk-module"`; `appmenu-gtk2-module` last shipped in noble / Debian bookworm; menus stay in window; "Not planned (coordinator, B-12)" [HISTORICAL_FACT: research/hud/README.md:151-157; research/messaging-menu/README.md:188-194; STATUS.md:310-313]
- where recorded: STATUS.md:310-313 (Known limitations); research/hud/README.md:151-157
- evidence type: reproduced (Pidgin log on target2) + read (archive history)
- current_state: open, accepted limitation (not planned). No appmenu-gtk2 anywhere in resolute/stonking or our aptly [CURRENTLY_VERIFIED: `rmadison -s resolute,stonking appmenu-gtk2-module` → no output; `aptly repo search unity-resolute 'Name (% appmenu-gtk2*)'` → no results]
- gaps_unknowns: how many GTK2 apps remain in 26.04 default/popular set [UNVERIFIED]
- unfinished: no — decision already taken (not planned); only a task if May reverses it.
- doubtful: "harmless" log line — fine.
- proposed migration_result: LEGACY_VERIFIED — reproduced; archive absence re-confirmed today.

### B-L47 — unity-scope-home: new scope unused until next login
- legacy_id: B-L47 (collected as G5-05)
- package: unity-scope-home (archive, 6.8.2+19.04.20190412-0ubuntu8)
- goal/finding: a scope installed while the home scope runs is not used until home scope restarts (next login); "how the home scope reads its registry, not a bug" [HISTORICAL_FACT: research/unity-scopes/README.md:66-68]
- where recorded: research/unity-scopes/README.md:66-68
- evidence type: observed during B-4 (implied) + mechanism assumed; no code line or run log cited
- current_state: open-by-design (no action).
- gaps_unknowns: no pointer to the registry-reading code; no test log in record [UNVERIFIED]
- unfinished: no.
- doubtful: "not a bug" is an assertion without a code citation.
- proposed migration_result: REQUIRES_REVALIDATION — mechanism inferred, not evidenced in the record.

### B-L48 — nux: upstream ICU conversions broken, unreached on Linux
- legacy_id: B-L48 (collected as G5-06)
- package: nux 4.0.8+18.10.20180623-0ubuntu14/15 (`remove_unicode_licensed.patch`, LP #2147049)
- goal/finding: `icu_conversions.cpp` (replacing ConvertUTF*) is broken: source length `end - start + 1`, capacity counted in 4-byte units passed as bytes, `*sourceStart/*targetStart` never advanced, `"utf16"/"utf32"` = BE+BOM vs host-endian wchar_t; measured with `utfconv.cpp` (e.g. "Hi" 8→32 consumed 0, BOM first; 32→8 garbage). No effect on Unity: on Linux `TCHARToUTF8(s)` is identity, remaining callers Windows-only [HISTORICAL_FACT: research/nux-vidmode/README.md:120-141; status/B.md:196,205]
- where recorded: research/nux-vidmode/README.md:120-141 (+ utfconv.cpp)
- evidence type: measured (test program) for the defect; read in code for "unreached"
- current_state: open upstream, on hold (upstream report waits for May) [HISTORICAL_FACT: status/B.md:204-205]. Defect still present in our carried patch [CURRENTLY_VERIFIED: `git -C packages/nux show b/fbo:debian/patches/remove_unicode_licensed.patch | grep 'source_end - \*source_start + 1'` hit at patch line 947]. Upstream devel head unchanged at 2c1878a [CURRENTLY_VERIFIED: `git -C packages/nux ls-remote origin refs/heads/ubuntu/devel`]
- gaps_unknowns: third-party nux consumers on Linux calling conversions [UNVERIFIED]
- unfinished: no UNITY-* task (no Unity-visible defect); upstream report item only.
- doubtful: none.
- proposed migration_result: LEGACY_VERIFIED — measured; code still unchanged today.

### B-L49 — unity-scope-launchpad: not rebuilt, broken `Exec=/usr/bin/python`
- legacy_id: B-L49 (collected as G5-08)
- package: unity-scope-launchpad 0.1daily13.06.05-0ubuntu6
- goal/finding: not rebuilt (tests need api.launchpad.net; online scope); does not load: `Exec=/usr/bin/python`, absent in 26.04; left alone. It remains the only owner of `dist-packages/__init__.py` [HISTORICAL_FACT: research/unity-scopes/README.md:34-36,63]
- where recorded: research/unity-scopes/README.md:34-36,63
- evidence type: reproduced (D-Bus activation load test)
- current_state: open (left alone, online scope). Not in our aptly [CURRENTLY_VERIFIED: `aptly repo search unity-resolute 'Name (% unity-scope-launchpad)'` → no results]; archive unchanged in resolute/stonking [CURRENTLY_VERIFIED: `rmadison unity-scope-launchpad`]
- gaps_unknowns: whether it is installed by default (record implies not) [UNVERIFIED]
- unfinished: no (deliberate); candidate only if May wants online scopes.
- doubtful: none.
- proposed migration_result: LEGACY_VERIFIED — reproduced; archive state same.

### B-L50 — unity-lens-photos: facebook/flickr Soup 2.4 vs 3.0 ImportError
- legacy_id: B-L50 (collected as G5-09)
- package: unity-lens-photos 1.0+17.10.20170605-0ubuntu10
- goal/finding: facebook/flickr scopes fail to load (`Requiring namespace 'Soup' version '2.4', but '3.0' is already loaded`), apport files a crash on activation; from the Dash no crash because `RemoteContent=true` and remote search off (0 new crash files) [HISTORICAL_FACT: research/unity-scopes/README.md:54]
- where recorded: research/unity-scopes/README.md:54
- evidence type: reproduced (load.sh) + measured (0 crash files after photos search)
- current_state: open, left alone (online). Not in aptly; archive unchanged [CURRENTLY_VERIFIED: `aptly repo search ... 'Name (% unity-lens-photos)'` no results; `rmadison unity-lens-photos`]
- gaps_unknowns: crash if user enables remote search [UNVERIFIED]
- unfinished: no (online, deliberate).
- doubtful: none.
- proposed migration_result: LEGACY_VERIFIED.

### B-L51 — misc scope findings: files-lens locate, SyntaxWarnings, yahoostock feedparser
- legacy_id: B-L51 (collected as G5-10)
- package: unity-lens-files; Python unity-scope-*; unity-scope-yahoostock
- goal/finding: (a) files lens global search runs `locate`, none installed [HISTORICAL_FACT: research/unity-scopes/README.md:49,91-92]; (b) Python scopes print invalid-escape `SyntaxWarning`s, yahoostock `"is" with 'int' literal` [HISTORICAL_FACT: :93-94]; (c) yahoostock imports feedparser without depending on it [HISTORICAL_FACT: :95-96]
- where recorded: research/unity-scopes/README.md:49,91-96,108-121
- evidence type: reproduced (journal/log)
- current_state: (a) CLOSED by unity-lens-files +unity1 (Recommends plocate; 0 locate errors; file found with plocate) [HISTORICAL_FACT: research/unity-scopes/README.md:108-121], in aptly [CURRENTLY_VERIFIED: `aptly repo search unity-resolute 'Name (% unity-lens-files)'`]; (b) open — the seven scope debdiffs do not touch escapes [CURRENTLY_VERIFIED: `grep -l -E 'SyntaxWarning|escape|r"' docs/research/unity-scopes/debdiff/*` → none]; A-6 fixed such warnings only in unity/u-s-d/u-c-c [HISTORICAL_FACT: DECISIONS.md:1488-1490]; (c) open, package removed by Conflicts anyway.
- gaps_unknowns: whether SyntaxWarnings become errors in a future Python [UNVERIFIED]
- unfinished: (b) cosmetic; not a UNITY-* candidate unless the rule "python3 -W error py_compile clean" (A-6) is extended to scopes.
- doubtful: none.
- proposed migration_result: LEGACY_VERIFIED — (b) SyntaxWarnings and (c) yahoostock feedparser were reproduced (recorded) and remain open (the scope debdiffs do not touch them); (a) files-lens locate is SUPERSEDED by lens-files +unity1 (collected as G3-06). [B's review: one result for the entry]

### B-L52 — Canonical indicator-messages: double start
- legacy_id: B-L52 (collected as G5-11)
- package: indicator-messages 0ubuntu8~26.04.1 (B-9)
- goal/finding: started twice (systemd via `unity-panel-service.service.wants` and XDG autostart); systemd instance loses the bus name and exits 0; archive behaviour (same file list); harmless [HISTORICAL_FACT: research/rebuild-loss/README.md:142-147; research/messaging-menu/README.md:118-128; DECISIONS.md:1526]
- where recorded: research/rebuild-loss/README.md:142-147; research/messaging-menu/README.md:118-128
- evidence type: reproduced on target2
- current_state: superseded — Unity now uses ayatana-indicator-messages (single starter); Canonical one kept in aptly but "nothing should install it" [HISTORICAL_FACT: research/messaging-menu/README.md:124-128]
- gaps_unknowns: no mechanism prevents installing it alongside Ayatana's [UNVERIFIED]
- unfinished: no.
- doubtful: none.
- proposed migration_result: SUPERSEDED — B-10 chose Ayatana's indicator.

### B-L53 — Vala codegen bug (detailed notify emission) and LP #1968333 fix: not reported
- legacy_id: B-L53 (collected as G5-12)
- package: valac ≥0.55.1 (GNOME/vala); indicator-keyboard
- goal/finding: since Vala 0.55.1 (b9df26bcf) a signal with emitter drops `detail_expr`: `notify["command"](pspec)` → `g_object_notify(self, pspec)` (critical, no notify); reproduced with a 20-line class on valac 0.56.18; unchanged in 0.56.19 and main; our indicator-keyboard +unity2 changes the test mock to `notify_property()` and makes tests fatal (9/9) [HISTORICAL_FACT: research/indicator-ftbfs/README.md:45-95; DECISIONS.md:974-987]. Not reported: Vala bug and LP #1968333 fix "wait for May" [HISTORICAL_FACT: research/indicator-ftbfs/README.md:94-95; STATUS.md:253-256]
- where recorded: research/indicator-ftbfs/README.md:45-95
- evidence type: reproduced (reproducer) + read in code (valagsignalmodule.vala)
- current_state: fix closed locally (in aptly per status/B.md:150-152; exported patch identical to git, see table 9); upstream reporting open/on hold.
- gaps_unknowns: current Vala main state not re-checked today [UNVERIFIED]
- unfinished: upstream-queue item, not a UNITY-* defect.
- doubtful: none.
- proposed migration_result: LEGACY_VERIFIED — reproduced; local fix measured by tests.

### B-L54 — indicator-keyboard 0ubuntu4 in 26.10 lost its user unit (B's re-check 2026-09-25)
- legacy_id: B-L54 (collected as G5-13)
- package: indicator-keyboard (26.10 0ubuntu4)
- goal/finding: B's re-check found no newer release carrying B's fixes (all patches stay); on the way: 26.10 0ubuntu4 ships no systemd user unit (build-depends on `systemd`, not `systemd-dev`); not reported per May [HISTORICAL_FACT: DECISIONS.md:1047-1084; status/B.md:140-143]
- where recorded: DECISIONS.md:1047-1084
- evidence type: read (rmadison, git-ubuntu diffs); "no user unit" apparently from inspecting 26.10 binaries — method not stated
- current_state: open upstream (not reported); our +unity3 unaffected.
- gaps_unknowns: re-check is stale (2026-09-25); 26.10 may have moved [UNVERIFIED]
- unfinished: no UNITY-* task (affects 26.10 archive, not us); upstream-report candidate on hold.
- doubtful: method for "ships no user unit" not cited.
- proposed migration_result: REQUIRES_REVALIDATION — point-in-time archive comparison, now 2 days old.

### B-L55 — appmenu-gtk-module: GIMP segfault on module drop (archive) vs survives (+unity1)
- legacy_id: B-L55 (collected as G5-14)
- package: appmenu-gtk-module 25.04-1build1(+unity1, a783b01c, LP #2166410)
- goal/finding: with archive module GIMP 3.2.2 SIGSEGV after module drop 2/2; with +unity1 survives 2/2 (also after re-add); LibreOffice survives both; Chromium snap does not map host module. GIMP exports whole menu via module; LO exports native menu. `enabled-gtk-modules` does not work (u-s-d publishes only known modules) [HISTORICAL_FACT: research/appmenu-resident/README.md:107-135; status/B.md:47-50]
- where recorded: research/appmenu-resident/README.md:107-135
- evidence type: reproduced/measured (n=2 each)
- current_state: closed by +unity1 (in aptly per status/B.md:159-161).
- gaps_unknowns: n=2 per arm is small.
- unfinished: no.
- doubtful: 2/2 samples — "survives" is suggestive, not strong.
- proposed migration_result: LEGACY_VERIFIED (small-n) — measured before/after.

### B-L56 — rebuild-trial / rebuild-loss survey results
- legacy_id: B-L56 (collected as G5-15)
- package: 9 (trial) + 21 (loss) Unity-stack sources
- goal/finding: trial: 7/9 build; libindicator FTBFS (systemd.pc) fixed +unity1; vala-panel FTBFS (G5-01) [HISTORICAL_FACT: research/rebuild-trial/README.md:10-20]. Loss survey: no successful rebuild lost a file; systemd.pc trap in indicator-messages (26.10 0ubuntu8) and hud; session-migration CMake4+test regex; unity-greeter unsatisfiable; overlay-scrollbar dead [HISTORICAL_FACT: research/rebuild-loss/README.md:97-108]
- where recorded: research/rebuild-trial/README.md; research/rebuild-loss/README.md; logs ~/work/b/rebuild, ~/work/b/b7, ~/work/b/b7fix
- evidence type: reproduced (sbuild) + measured (compare.py file lists)
- current_state: all follow-ups closed/superseded: libindicator +unity1/+unity2 published; indicator-messages 0ubuntu8~26.04.1 (B-9); hud +unity1 (B-12); session-migration +unity1 published by A (A-6) [HISTORICAL_FACT: DECISIONS.md:1480-1485]; unity-greeter +unity1 by A (A-5) [HISTORICAL_FACT: research/rebuild-loss/README.md:126]; overlay-scrollbar stub (B-11). Table rows in rebuild-loss:103-105 ("nobody owns", "not in aptly") are stale.
- gaps_unknowns: 35→21 candidate filtering (only sources with risky files) excludes other regressions by design.
- unfinished: no.
- doubtful: rebuild-loss:105 "deleted from resolute" (see G5-02); rows 103-104 stale.
- proposed migration_result: LEGACY_VERIFIED for the survey measurement; stale rows SUPERSEDED by B-9/B-11/B-12/A-5/A-6.

### B-L57 — gtk-nocsd global menu under Xfce/Plasma (research/nocsd-desktops, B's)
- legacy_id: B-L57 (collected as G5-16)
- package: gtk-nocsd (menu patch ~menu5 on upstream 6b1f70a)
- goal/finding: patch works on Xfce 4.20 and Plasma 6.6.4 X11 (18/18 apps, identical to Unity) only when `gtk-shell-shows-menubar` is set, which neither desktop does; under Xfce, Debian's gtk-nocsd is not loaded at all from environment.d (Xsession-started session) — "recorded, not reported" [HISTORICAL_FACT: research/nocsd-desktops/README.md:15-61]
- where recorded: research/nocsd-desktops/README.md
- evidence type: measured in real sessions on target2
- current_state: Xfce LD_PRELOAD part superseded by our gtk-nocsd +unity2/+unity3 `51gtk-nocsd` [HISTORICAL_FACT: status/B.md:17-18,113-116; research/hud/README.md:121-149]; design question (flag vs Registrar detection) open, patch not sent (gtk-nocsd group covers) [HISTORICAL_FACT: research/nocsd-desktops/README.md:47-54]
- gaps_unknowns: MATE, Budgie, Wayland, full Xubuntu/Kubuntu not tested [HISTORICAL_FACT: :63-66]
- unfinished: no UNITY-* task (upstream-design / May decision).
- doubtful: none.
- proposed migration_result: LEGACY_PARTIAL — measured; Xfce preload part SUPERSEDED by +unity3; remainder belongs to gtk-nocsd group.

---


## Appendix A: observations (not ledger items)

### G1-09 — other B work found in these areas (not in the brief)
- gtk-nocsd global-menu experiments (B): branches `b/global-menu` (cafe5a2, "~menu1"), `b/global-menu-up` (88bdc15, "~menu5"), `b/exp-flat` in ~/work/b/nocsd-merge/pkg (origin = local UD/packages/gtk-nocsd); `global-menu` d335007, `menu` b4af040, `exp-flat` b0424de, `fix-dialog-title` 2cfc8f1 in ~/work/b/nocsd-up/src (origin codeberg MorsMortium/gtk-nocsd, not ours). Local only; patches exported in research/nocsd-merge/ and research/nocsd-upstream/. Not in aptly. `fix-dialog-title` is registered as a worktree at `scratchpad/fix`, which no longer exists (stale worktree; the commit remains in the repo). [CURRENTLY_VERIFIED: `git branch -vv` in both dirs; `ls` of worktree path -> missing; HISTORICAL_FACT: SB:130-139; DEC:1122,1141,1241,1263]
- gtk-nocsd package +unity2/+unity3 (B, LD_PRELOAD fix) — published, likely in another group; not examined here. [HISTORICAL_FACT: 07-PENDING-MAY.md:77; PAT:83]
- STACK-HEALTH section B (nux row etc.). [HISTORICAL_FACT: LOG:142; STACK-HEALTH.md:74]
- unity-gtk4-menu "late-menu placeholder" diff — written, deliberately not shipped. [HISTORICAL_FACT: DEC:800-810]
- Qt global menu: measured working, nothing built. [HISTORICAL_FACT: SB:201; research/layer-b/README.md:1550]
- proposed migration_result: gtk-nocsd experiments — REQUIRES_REVALIDATION only if revived (unpublished, builder-only branches, one stale worktree); others informational.

### G2-15 — Other B work found in these areas (not in the item list)
- indicator-keyboard 26.10 0ubuntu4 lost its systemd user unit too — found, not reported [HISTORICAL_FACT: status/B.md:142-143; STACK-HEALTH.md:84]. Not our package version; informational.
- Vala codegen bug (detailed notify via emitter drops detail) and our LP #1968333 fix — not reported upstream, waits for May [HISTORICAL_FACT: research/indicator-ftbfs/README.md:99-100; PATCHES.md:62].
- Negative-control build for indicator-datetime kept in `~/work/b/idt-neg` (useful evidence, not referenced by path in README) [CURRENTLY_VERIFIED: ls].
- Adjacent B items in the same research dirs, belonging to other groups: overlay-scrollbar +unity1 and ubuntu-unity-meta 0.29+unity1 (B-11, research/messaging-menu/), hud +unity1 (B-12), session-migration debdiff (now A's) [HISTORICAL_FACT: messaging-menu/README.md:130-190; rebuild-loss/README.md; DECISIONS.md A-6 entry].
- Stale docs: PATCHES.md:64 and status/B.md:125 (libindicator +unity1 "not in aptly"); research/indicator-units/README.md:41 ("in aptly" — binaries only); package-patches-b/README.md table omits indicator-messages [CURRENTLY_VERIFIED: reading files vs CMD-APTLY].
- Build-before-commit pattern: datetime +unity2, keyboard +unity3, libindicator +unity2 were sbuilt before the git commit existed; trees match now, but there was no commit-pinned build [CURRENTLY_VERIFIED: log timestamps vs commit dates].

### G3-12 — ayatana-indicator-messages 24.5.1-1build1+unity1 (extra: no-git B package listed in package-patches-b)
- package: ayatana-indicator-messages (binaries ayatana-indicator-messages, gir1.2-messagingmenu-1.0, libmessaging-menu-dev, libmessaging-menu0) [CURRENTLY_VERIFIED: C-APTLY]
- goal: link `/usr/share/ayatana/indicators/org.ayatana.indicator.messages` into `/usr/share/unity/indicators` so Unity's panel (with libindicator +unity2) shows the Ayatana messaging menu [HISTORICAL_FACT: debdiff; DECISIONS.md:1498-1512]
- commits/branches: docs/package-patches-b/debdiff/ayatana-indicator-messages_+unity1.debdiff, commit `ecf7619b1c177dcc7dd81fcf1c6572eb914f8fdf`, on origin/main [CURRENTLY_VERIFIED]
- versions: 24.5.1-1build1+unity1; archive resolute 24.5.1-1build1, stonking 24.5.2-3 [CURRENTLY_VERIFIED: C-RMADISON]
- build/test/target: built 17:39Z, published 17:53Z, target2 Clean-2 at 17:56Z [HISTORICAL_FACT: AGENTS-LOG.md:396, 397-398, 400]
- aptly_state: source + 4 binaries +unity1 [CURRENTLY_VERIFIED: C-APTLY]
- source↔aptly match: MATCH — `debdiff arch/ayatana-indicator-messages_24.5.1-1build1.dsc aptly/…+unity1.dsc` vs committed debdiff ("AYATANA_MATCH"); orig identical [CURRENTLY_VERIFIED]. Binaries vs build dir: NOT_CHECKED
- records: PATCHES.md:78; DECISIONS.md:1498; research/messaging-menu/; status/B.md:33-40 [HISTORICAL_FACT]
- provenance_gap: common gap + no-git source
- doubtful_fix: belongs to B-10 (probably another group's scope); not judged here.
- proposed migration_result: source↔aptly **currently MATCH**; classification deferred to the group owning B-10 (libindicator +unity2 coupling).

### G3-13 — other B work found in these areas (not in the G3 list)
- gtk-nocsd 4.8-1+unity3 (51gtk-nocsd keeps environment.d LD_PRELOAD), found during B-12, commit `a2a0747` on unity/resolute, github Ubuntu-Unity-LifeSupport/gtk-nocsd, in aptly [HISTORICAL_FACT: research/hud/README.md:106-149; PATCHES.md:83; AGENTS-LOG.md:414] — not verified here (belongs to gtk-nocsd group) [UNVERIFIED]
- unity-scope-launchpad +unity1: B attempted a build (~/work/b/scopes/results.txt "EXIT 2", log unity-scope-launchpad_0.1daily13.06.05-0ubuntu6+unity1.log); no debdiff committed, not in aptly; research says "launchpad is not rebuilt" [CURRENTLY_VERIFIED: cat results.txt; HISTORICAL_FACT: research/unity-scopes/README.md:34-36] — abandoned attempt, no artefact to migrate
- hud WIP source in ~/work/b/b7fix (pre-C++17, sha 0ac7718c…), superseded by the published +unity1 [CURRENTLY_VERIFIED]
- rebuild-trial of libunity/lenses/scope-home/indicator-* (2026-09-25) and rebuild-loss survey (2026-09-26, B-7) — research only, docs commits `b411b7756cf58c78dd02fd74c1276a1f2ab8d837` and `06bcc6b951e69b18e98cea8bc2f80ce5b210ec17` on origin/main [CURRENTLY_VERIFIED: C-DOCGIT]
- Stale records to fix in any follow-up: status/B.md:56-57, status/B.md:160-161, research/rebuild-loss/README.md:33 and :35, research/unity-scopes/README.md:91-92 [HISTORICAL_FACT; see entries above]

### G4-14 — gtk-nocsd: aptly hygiene observations
- package: gtk-nocsd
- aptly_state: 4 source versions counted by coordinator (0b77e1b+unity2 binaries without source record; 4.8-1+unity1/2/3 with source) [CV-aptly; migration 04-aptly-latest-by-source.txt:6]; +unity2 dbgsym missing; repo published amd64 only, no source index [CV-pub]; no snapshots [CV-pub]
- source↔aptly match: +unity1/+unity2/+unity3 MATCH (G4-02..04); 0b77e1b NOT_CHECKED
- provenance_gap: entire history published by direct `aptly publish` without snapshot (§6)
- unfinished: NEW TASK (C/A) — decide on removing superseded versions and the source-less 0b77e1b binaries under the new publish process (not B's to do unilaterally)
- proposed migration_result: REQUIRES_REVALIDATION — repo state needs a first gated snapshot


## Appendix B: exports and work directories

## 9. package clones in ~/unity-distro/packages without our GitHub remote

Method [CURRENTLY_VERIFIED]: `git -C packages/<d> remote -v`; `git log --oneline --branches --not --remotes`; `git rev-list --count <base>..<tip>`; `git format-patch <base>..<tip> --stdout` vs `cat <export>/*.patch`, both filtered by dropping `^From <40hex> Mon Sep 17` and the `-- `+version line pair, then `diff`. Only differences found anywhere were blank separator lines that `--stdout` inserts between concatenated patches (datetime 1, keyboard 3, libindicator 1, nux 1) — content identical.
gtk-nocsd is excluded (has `lifesupport` GitHub remote plus salsa). `ll-build`, `ll-src` are not git trees.

| clone | remote(s) | owner | base (tip) | local commits ahead | export location | #patches live/export | content |
|---|---|---|---|---|---|---|---|
| appmenu-gtk-module | launchpad | B | origin/ubuntu/resolute 025b498 (unity/resolute 548f9b4) | 1 | package-patches-b/appmenu-gtk-module | 1/1 | identical |
| calamares-settings-ubuntu | launchpad ~ubuntu-qt-code | B | origin/ubuntu/resolute c699701 (unity/resolute b6b546b) | 1 | **research/calamares-oem/** (not package-patches-b; README table omits it) | 1/1 | identical |
| indicator-bluetooth | launchpad | B | 3540ba2 (a373dcf) | 1 | package-patches-b/indicator-bluetooth | 1/1 | identical |
| indicator-datetime | launchpad | B | 4fb6fd8 (846dfa0) | 2 | package-patches-b/indicator-datetime | 2/2 | identical |
| indicator-keyboard | launchpad | B | 134e195 (10eb95c) | 4 | package-patches-b/indicator-keyboard | 4/4 | identical |
| indicator-messages | launchpad | B | **origin/ubuntu/stonking** 78d9113 (86fbc0d) | 1 | package-patches-b/indicator-messages (**missing from README table**) | 1/1 | identical |
| indicator-power | launchpad | B | c41fadb (bff6e5d) | 1 | package-patches-b/indicator-power | 1/1 | identical |
| indicator-printers | launchpad | B | c5e42e6 (97fa920) | 1 | package-patches-b/indicator-printers | 1/1 | identical |
| indicator-session | launchpad | B | d34d4b2 (47aac89) | 1 | package-patches-b/indicator-session | 1/1 | identical |
| indicator-sound | launchpad | B | 56cb8b8 (338d8fd) | 1 | package-patches-b/indicator-sound | 1/1 | identical |
| libindicator | launchpad | B | 56a2331 (67bfe16) | 2 | package-patches-b/libindicator | 2/2 | identical |
| libunity | launchpad | B | fc47c88 (78c98ec) | 1 | package-patches-b/libunity | 1/1 | identical |
| nux | gitlab ubuntu-unity/nux | B | origin/ubuntu/devel 2c1878a (b/fbo 9793c23; b/ubuntu15 9d26778 is its parent) | 2 on b/fbo; +1 on **b/vidmode be561f9** (0ubuntu13-based, not ancestor of b/fbo) | package-patches-b/nux | 2/2 | identical; be561f9 not exported as a commit, but its only content `fix-missing-vidmode.patch` is byte-identical to research/nux-vidmode/fix-missing-vidmode.patch and to the copy inside b/fbo [CURRENTLY_VERIFIED: `git show b/vidmode:… \| diff -q -` and same for b/fbo] |
| unity-indicators | gitlab ubuntu-unity | nobody / A (reference clone) | main 32abb95 = origin/main | 0 | — | — | no local commits, clean |
| unity-scope-home | gitlab ubuntu-unity | nobody / A (reference clone) | ubuntu/devel ebf80fe = origin/ubuntu/devel | 0 | — | — | no local commits, clean |

Notes:
- package-patches-b/README.md table lists base "`origin/ubuntu/resolute`" for all indicator rows; indicator-messages actually sits on `origin/ubuntu/stonking` [CURRENTLY_VERIFIED: `git branch -vv` → `[origin/ubuntu/stonking: ahead 1]`]; README text omits indicator-messages and calamares rows but both are exported [CURRENTLY_VERIFIED: `ls docs/package-patches-b docs/research/calamares-oem`].
- nux `unity/resolute` local branch = 3c56e89 (upstream 0ubuntu13 commit, not ours); `b/vidmode` is historical (0ubuntu13+unity1 era).
- Nothing of B's in these clones is unexported.

### 10. ~/work/b directories

Sizes/contents [CURRENTLY_VERIFIED: `du -sh`, `ls`, `find -maxdepth 4 -name .git` in ~/work/b]; purpose [HISTORICAL_FACT: status/B.md and research READMEs as cited]. Loose top-level files (breadth-*.txt, *.png, classtest*, probe*, libunity-gtk4-menu.so.0, lp2160298.patch) are unity-gtk4-menu 0.4–0.8 breadth/probe artefacts (2026-09-23/24).

| dir | what | holds anything not recorded elsewhere? |
|---|---|---|
| aim | ayatana-indicator-messages +unity1 build | no (debdiff exported, in aptly) |
| amenu | appmenu-gtk-module +unity1 build | no |
| b7 | B-7 rebuild-loss sbuilds (21 sources) | build logs only (cited in rebuild-loss:123-124) |
| b7fix | hud / indicator-messages fix builds | logs only |
| cal | calamares-settings-ubuntu-unity build | no (patch in research/calamares-oem) |
| deb03 | unpacked unity-gtk4-menu 0.3 deb (env.d conf) | no |
| devroot | empty (uid 100000) | no |
| gtk3src | gtk+3.0 3.24.52 source (reference) | no |
| hud | hud +unity1 build | no (debdiff exported) |
| idt-fix / idt-neg | indicator-datetime +unity2 build / negative-test build | no |
| ik3 | indicator-keyboard +unity3 build | no |
| imsg | indicator-messages 0ubuntu8~26.04.1 build | no |
| ind / indb / indf | indicator-bluetooth/printers, datetime early builds, FTBFS-fix builds | logs only |
| iso | ISO manifest, calamares src, www bootstrap for oem-test | partly (www bootstrap; vm-bootstrap.sh copy in research/calamares-oem) [UNVERIFIED equality] |
| kbt | indicator-keyboard +unity2 build | no |
| lensfiles | unity-lens-files +unity1 build | no (debdiff exported) |
| li2 | libindicator +unity2 build | no |
| live | nocsd breadth result txts (Unity/KDE/Xfce) | possibly raw breadth files beyond those committed [UNVERIFIED] |
| lu1 | libunity +unity1 build | no |
| meta | ubuntu-unity-meta 0.29+unity1 build | no |
| nocsd-head | gtk-nocsd upstream main clone (codeberg), 0 unpushed | no |
| nocsd-merge | gtk-nocsd experiments; `pkg` git: 4 local-only commits (b/exp-flat, b/global-menu, b/global-menu-up) | **yes — local branches, gtk-nocsd group** |
| nocsd-u2 / nocsd-u3 | gtk-nocsd 4.8-1+unity2/+unity3 builds | no (pushed branch unity/resolute) |
| nocsd-up | gtk-nocsd upstream clone + worktrees `flat`, `split`; 13 local-only commits on global-menu, menu, exp-flat, split-parts, split-parts-2, fix-dialog-title (worktree in scratchpad, marked prunable) | **yes — local branches, gtk-nocsd group** (fix-dialog-title patch also in research/nocsd-epiphany-crash/) |
| nux | nux builds (out, out15, outu2), ABI dumps, test programs, screenshots | test programs copied to research/nux-vidmode; logs only otherwise |
| osb | overlay-scrollbar +unity1 build | no |
| out / out09 | unity-gtk4-menu 0.4–0.8 / 0.9 builds | no (repo on GitHub) |
| probe | probe library source (unity-gtk4-menu era) | possibly [UNVERIFIED] |
| rebuild | rebuild-trial sbuilds incl. out-vala-panel | logs only |
| reply2 | nocsd-reply2 measurements, split tests, shots | possibly raw data beyond research/nocsd-reply2 [UNVERIFIED] |
| scopes | 7 unity-scope-* +unity1 builds, results.txt | no (debdiffs exported) |
| src | yelp, gtk4, gnome-console, gnome-contacts sources (reference) | no |
| vpa | vala-panel-appmenu upstream clone (gitlab), 0 unpushed | no |
| xfwm4src | xfwm4 4.20.0 source (reference) | no |


## Appendix C: entries attributed to others (full collector text)

### G1-05 — belongs to A (unity-gtk4-menu 0.1-0.3 predate B)
- package: unity-gtk4-menu
- facts: 0.1 (9ad39071b7426cf794de4655e2e97e697e495322, 2026-09-23 07:27Z), 0.2 (0d6157308be1ff072d9a4b12941620d0e416638b, 07:52Z), 0.3 (d7d89e2f1ac7e81ca055baef1470f3e5f0370cd6, 09:50Z) were committed before agent B came online (22:39Z) and B took over at 0.3 ("A agreed to hand it over"). [CURRENTLY_VERIFIED: `git log --format='%H %ad'`; HISTORICAL_FACT: LOG:18,21-22]
- aptly_state: 0.3 in repo; 0.1 and 0.2 .debs remain in /srv/aptly/pool but are not in `unity-resolute` (orphaned pool files). [CURRENTLY_VERIFIED: `find /srv/aptly/pool -name '*gtk4-menu*'` vs `aptly repo search`]
- source↔aptly: NOT_CHECKED (outside B's scope; 0.3 deb built in ~/work/b/deb03 has no .dsc).
- proposed migration_result: out of G1/B scope — assign to A's reconciliation; if forced: SUPERSEDED by 0.9.

### G3-11 — belongs to nobody's / reference clone (unity-scope-home)
- package: unity-scope-home
- goal: n/a
- commits/branches: packages/unity-scope-home, branch `ubuntu/devel` = `ebf80fee24f1d20756fc14223cfccd7bff0c4857` (Tomasz Jeruzalski, 2026-02-16, "Update changelog", changelog top 6.8.2+19.04.20190412-0ubuntu7), remote origin = gitlab.com/ubuntu-unity/unity/unity-scope-home; no local commits; reflog: "clone" at 2026-09-22 18:21:22Z [CURRENTLY_VERIFIED: git log/reflog/head debian/changelog]. The clone predates agent B's first registration (2026-09-23 22:39Z) [HISTORICAL_FACT: ~/AGENTS.md line for B e6cb5b]
- versions: none of ours; not in aptly ("ERROR: no results") [CURRENTLY_VERIFIED: C-APTLY]
- build_state: B's rebuild-trial built the **archive** 6.8.2+19.04.20190412-0ubuntu8 .dsc from ~/work/b/rebuild (not this clone): successful 256 s; nothing published [HISTORICAL_FACT: research/rebuild-trial/README.md:7-8, 15; results.txt "16:39Z unity-scope-home successful 256s"; CURRENTLY_VERIFIED: ls ~/work/b/rebuild]
- test_state / target_state / aptly_state: n/a
- source↔aptly match: NOT_APPLICABLE
- records: research/rebuild-trial/README.md:15; research/rebuild-loss/README.md:30; STACK-HEALTH.md:78; DECISIONS.md:1201 [HISTORICAL_FACT]
- current_state: idle upstream clone
- gaps_unknowns: who cloned it on 2026-09-22 [UNVERIFIED; pre-two-agent era]
- provenance_gap: n/a
- unfinished: none
- doubtful_fix: n/a
- proposed migration_result: none — not a B deliverable (B only trial-built the archive source; no change produced).

### G4-01 — belongs to A (gtk-nocsd 0~20260321+0b77e1b-1+unity2)
- package: gtk-nocsd
- goal: backport upstream d851645 + 664d8c6 (crash handler segfault on glibc 2.43) [HF: P commits ddc0822, 23900a7 changelog]
- commits/branches: ddc0822212da927224446f5e15ef76e0997a089c (+unity1, never published), 23900a7a468e53a1bf48614b73b4416f82067c38 (+unity2); contained in lifesupport/unity/resolute [CV: `git branch -r --contains 23900a7`]; pushed 2026-09-24 17:25:10Z [CV: `git reflog show lifesupport/unity/resolute`]
- versions: source 0~20260321+0b77e1b-1+unity2 / binaries libgtk-nocsd0, gtk3-nocsd, libgtk3-nocsd0 3+0~20260321+0b77e1b-1+unity2 [CV-aptly]
- build_state: built by A in ~/work/a [HF: AGENTS-LOG.md:116-117]
- test_state: compiz restart + logout cycles by A [HF: DECISIONS.md:880-917]
- target_state: UV
- aptly_state: 3 binaries present, **source record absent** from repo (pool has no 0b77e1b .dsc) [CV-aptly; `find /srv/aptly/pool -name '*gtk-nocsd_0*'` -> none]
- source↔aptly match: NOT_CHECKED (no source in aptly)
- records: PATCHES.md:33; DECISIONS.md:880 "compiz restart: four fixes"; research/compiz-restart/
- current_state: superseded by 4.8-1+unity1 (patches part of 4.0) [HF: PATCHES.md:33]; obsolete binaries still in repo
- gaps_unknowns: why source is missing from repo (removed or never added) UV
- provenance_gap: old process; no manifest/gate/snapshot; source not in aptly
- unfinished: none for B; stale binaries in repo — A/C hygiene decision
- doubtful_fix: n/a (A's)
- proposed migration_result: SUPERSEDED — replaced by 4.8 rebase; owner A (listed here only because 4 aptly versions were asked)

### G4-02 — belongs to A (gtk-nocsd 4.8-1+unity1, handed to B)
- package: gtk-nocsd
- goal: fix LP #2158965 (Chromium without window buttons, upstream ecd66fe) by taking 4.8 whole [HF: DECISIONS.md:957-972]
- commits/branches: 92ed59e7b622fe2f76490e3ea04e43131a08f06d (merge of salsa 5e3e223348575f74938cb31ec76e4d68332e399f); on lifesupport/unity/resolute, pushed 2026-09-25 02:36:43Z [CV: reflog]
- versions: 4.8-1+unity1 / libgtk-nocsd0 (+dbgsym), gtk3-nocsd, libgtk3-nocsd0 4.8-1+unity1 [CV-aptly]
- build_state: sbuild by A [HF: AGENTS-LOG.md:199]
- test_state: 13 apps, crash handler, logout [HF: DECISIONS.md:963-967]
- target_state: UV
- aptly_state: present [CV-aptly]
- source↔aptly match: MATCH — debian/ of aptly .dsc (sha256 ad5da668…) == git tree 92ed59e [CV-cmp]; P holds debian/ only, upstream via orig.tar.gz sha256 2be0214c… [CV: `sha256sum`]
- records: PATCHES.md:34; research/gtk-nocsd-4.8/
- current_state: superseded by +unity2/+unity3
- gaps_unknowns: none in B scope
- provenance_gap: old process (no manifest/gate/snapshot)
- unfinished: none for B
- doubtful_fix: n/a (A's)
- proposed migration_result: SUPERSEDED — base of B's +unity2/+unity3; A to reconcile

### G5-07 — belongs to A (nux Validator finding)
- package: nux (Nux/Validator.cpp, Windows branch)
- goal/finding: on the Windows branch `Validate` returns `Acceptable` from both sides of its `if` [HISTORICAL_FACT: DECISIONS.md:177-179; PATCHES.md:40; STATUS.md:253; CONTRIBUTING-UPSTREAM.md:194]
- where recorded: DECISIONS.md:177-179 (2026-09-22, commit 3e206c1 — agent A's era, before B existed); PATCHES.md:40 status "draft"
- evidence type: read in code
- current_state: open, draft, not sent; Windows-only path.
- gaps_unknowns: none relevant to Linux.
- unfinished: no (Windows-only, no Linux effect); belongs to A's/upstream queue, not B's reconciliation.
- doubtful: none.
- proposed migration_result: LEGACY_VERIFIED (read-in-code finding, nothing contradicts) — attribute to A, exclude from B's ledger.


## Appendix D: collector preambles and command legends

#### Collector preamble G1

Collected 2026-09-27, read-only. Scratch extraction under `scratchpad/mig/tmp-G1/`.
Abbreviations: UD = ~/unity-distro, DEC = UD/docs/DECISIONS.md, PAT = UD/docs/PATCHES.md,
SB = UD/docs/status/B.md, LOG = ~/AGENTS-LOG.md, EP = UD/docs/ENGINEERING-PROCESS.md.

Common facts used below:
- aptly holds NO source packages for nux, unity-gtk4-menu or calamares-settings-ubuntu; only .debs. [CURRENTLY_VERIFIED: `find /srv/aptly/pool -name '*.dsc' | grep -E 'nux|gtk4|calamares'` -> empty; `aptly repo search unity-resolute 'Name (nux) | ...'` -> no `_source` rows for these three]
- Therefore "source↔aptly" below = (a) local .dsc that sbuild consumed, unpacked with `dpkg-source -x --no-check`, `diff -rq` against `git archive <commit>`; plus (b) sha256 of each local built .deb vs the aptly pool .deb of the same name. Both must hold to say MATCH. [method]
- Meta-repo records (docs/research/*, package-patches-b/*) are pushed: `git diff --stat origin/main -- <path>` empty for every path cited; origin = github.com/Ubuntu-Unity-LifeSupport/unity-distro. [CURRENTLY_VERIFIED: `git -C UD diff --stat origin/main -- docs/research/{nux-fbo,nux-vidmode,layer-b,nocsd-order,calamares-oem} docs/package-patches-b/nux`]
- No item below has a build manifest, release gate JSON, version-safety record or aptly snapshot (EP §6). [CURRENTLY_VERIFIED: aptly has no snapshots per task brief; no RELEASE-*/gate files in the cited research dirs: `ls UD/docs/research/{nux-fbo,nux-vidmode,layer-b,nocsd-order,calamares-oem}`]
- Archive context: `rmadison` -> nux 0ubuntu12 resolute, 0ubuntu13 stonking, 0ubuntu15 stonking-proposed; calamares-settings-ubuntu 1:26.04.12 resolute, 1:26.10.5 stonking. All our versions sort above resolute's. [CURRENTLY_VERIFIED: `rmadison -s resolute,...,stonking-proposed nux calamares-settings-ubuntu`]

---


#### Collector preamble G2

Commands referenced below (run 2026-09-27 on builder, read-only; temp output in scratchpad/mig/tmp-G2/):
- CMD-REMOTE: `git -C ~/unity-distro/packages/<p> remote -v; git -C … branch -vv -a`
- CMD-FP: `git format-patch <base>..unity/resolute --stdout` vs `cat docs/package-patches-b/<p>/*.patch`, both filtered of `^From <40hex> ` and the `2.x` version trailer; then per commit `git format-patch -1 <h> --stdout` vs the single exported file. "MATCH" = only diffs are the mbox blank separator between patches and `[PATCH n/m]` subject numbering (checked with `diff`).
- CMD-APTLY: `aptly repo search unity-resolute '$Source (<p>) | Name (<p>)'`; publish: `aptly publish list` → `./resolute [amd64] publishes {main: [unity-resolute]}` (no snapshot).
- CMD-SRC: `tmp-G2/cmp.sh <p> <ver> <commit>`: copy `/srv/aptly/pool/**/<hash>_<p>_<ver>.dsc` + files, `dpkg-source --no-check --skip-patches -x`, vs `git archive <commit> | tar -x`; `diff -r -x .pc -x .git -x .gitignore`. All sources here are Format 1.0.
- CMD-DEB: `sha256sum` of every pool .deb vs `find ~/work/b -name <same name> -exec sha256sum`.
- CMD-SYM: `dpkg-deb -x` of pool libindicator3-7/libindicator7 +unity1 and +unity2; `nm -D --defined-only … | sort | diff`.
- CMD-MADISON: `rmadison -u ubuntu <p>` (resolute / stonking=26.10).

General facts for every entry:
- All 9 clones have only `origin https://git.launchpad.net/ubuntu/+source/<p>`; branch `unity/resolute` is local, tracking an origin ref, "ahead N"; no remote of ours [CURRENTLY_VERIFIED: CMD-REMOTE]. Source provenance = builder-local git + export in `docs/package-patches-b/` only [HISTORICAL_FACT: docs/package-patches-b/README.md:1-10].
- aptly: local repo `unity-resolute` published directly as `resolute`, no snapshot [CURRENTLY_VERIFIED: CMD-APTLY publish list].
- No item has a build manifest (scripts/build_sbuild.py), release gate, version-safety record, publish record or aptly snapshot as required by docs/ENGINEERING-PROCESS.md §6 [HISTORICAL_FACT: ENGINEERING-PROCESS.md §6; no such files found under docs/research/<dirs below> — CURRENTLY_VERIFIED: `ls` of each research dir].
- No evidence card in §2 format (task_id, correct_layer, defensive_workaround_rejected, design_challenger_required) exists for any item; research READMEs are free-form [CURRENTLY_VERIFIED: reading the READMEs listed].
- target2 was restored to Clean-2 after each task and finally 2026-09-26 20:56Z [HISTORICAL_FACT: docs/status/B.md:46-48]; current installed state on any VM: [UNVERIFIED] (no VM access in this task).
- Sbuild outputs exist and every published .deb in G2 is byte-identical (sha256) to a file in `~/work/b/<dir>/out` (or `rebuild/fix-libindicator`) [CURRENTLY_VERIFIED: CMD-DEB]; build logs `*Z.build` present there [CURRENTLY_VERIFIED: ls].

---


#### Collector preamble G3

Collected 2026-09-27, read-only. Temp dir: `scratchpad/mig/tmp-G3/` (arch/ = archive sources from `apt-get source --download-only`, aptly/ = copies of /srv/aptly/pool source files, dd/ = regenerated debdiffs, x/ = extracted trees).

Shared commands referenced below:
- **C-APTLY**: `aptly repo search unity-resolute '$Source (<pkg>) | Name (<pkg>)'` (run 2026-09-27).
- **C-PUB**: awk over `/srv/aptly/public/dists/resolute/main/binary-amd64/Packages` for Package/Version. Published `./resolute [amd64] publishes {main: [unity-resolute]}` (`aptly publish list`); `aptly snapshot list` → "No snapshots found"; published dist has no source index (binary-amd64 only).
- **C-DD**: `debdiff arch/<p>_<archive-v>.dsc aptly/<p>_<v>+unity1.dsc > dd/<p>.debdiff`, then `diff <(strip dd/<p>.debdiff) <(strip <committed debdiff>)` where `strip` normalises only `---/+++/diff` header lines (paths/timestamps). Result "MATCH" = identical bodies.
- **C-ORIG**: `sha256sum aptly/<p>_*.orig.tar.* arch/<p>_*.orig.tar.*` → all 12 origs identical (hud, libunity, overlay-scrollbar, lens-files, 7 scopes, ayatana).
- **C-BIN**: for every aptly pool `.deb` of these sources, `sha256sum` vs a same-named file under `~/work/b` / `~/work` → all matched a local build output (list per entry).
- **C-RMADISON**: `rmadison -u ubuntu -a source -s resolute,resolute-updates,resolute-security,resolute-proposed,stonking <pkgs>`.
- **C-DOCGIT**: in ~/unity-distro `git log -1 --format=%H -- <path>` + `git branch -r --contains <hash>` → all doc commits below are on `origin/main` [CURRENTLY_VERIFIED]. unity-distro local `main` is ahead of origin/main by 2 (30499ff, not B's) [CURRENTLY_VERIFIED: git branch -vv].

Common provenance gap (applies to EVERY published item below, not repeated in full): published under the pre-2026-09-27 process; no task ID (UNITY-YYYYMMDD-NNN), no evidence card with the §2 fields (root_cause_mechanism / correct_layer / defensive_workaround_rejected / existing_fix_result), no `scripts/build_sbuild.py` build manifest (source tree hash, log hash), no `package-version-safety` record, no generated release gate, no verifier PASS (§5), no aptly snapshot (published straight from local repo `unity-resolute`; `aptly snapshot list` empty), no publish record in `~/coordinator/publish-records/` [CURRENTLY_VERIFIED: aptly snapshot list; docs/ENGINEERING-PROCESS.md §6]. Also: none of the `.changes` files in the build dirs contains a `.dsc` (binary-only sbuild), so no build artefact ties the aptly source bytes to the binaries [CURRENTLY_VERIFIED: awk over Checksums-Sha256 of ~/work/b/{lu1,hud,osb,meta,scopes,amenu,lensfiles}/**/*.changes].

---


#### Collector preamble G4

Conventions: HF = [HISTORICAL_FACT: ...], CV = [CURRENTLY_VERIFIED: ...], UV = [UNVERIFIED].
Paths: D = ~/unity-distro/docs, P = ~/unity-distro/packages/gtk-nocsd, T = scratchpad/mig/tmp-G4.
Common CV commands used below:
- CV-aptly: `aptly repo search unity-resolute '$Source (gtk-nocsd) | Name (gtk-nocsd)'` -> sources 4.8-1+unity1/2/3; binaries of 3+0~20260321+0b77e1b-1+unity2 (no source record); dbgsym only for +unity1, +unity3.
- CV-pub: `aptly publish list` -> `./resolute [amd64] publishes {main: [unity-resolute]}` (no source arch published); `aptly snapshot list` -> none.
- CV-cmp: `dpkg-source --no-check -x` of each aptly pool .dsc into T/uN, `git archive <commit>` into T/git-uN, `diff -r debian/`.
- CV-lsr: `git -C P ls-remote lifesupport` -> master 5e3e223348575f74938cb31ec76e4d68332e399f, unity/resolute a2a074786f6139a82d08f88f4aa42f35fb0a8e7a, tag debian/0_20260321+0b77e1b-1.
- CV-madison: `rmadison -u ubuntu gtk-nocsd` -> resolute 0~20260321+0b77e1b-1, stonking 4.8-1; `rmadison -u debian` -> 4.8-1 testing/unstable.
- CV-upstream: `git -C ~/work/b/nocsd-up/src ls-remote origin refs/heads/main` -> e817d809bd976185099477b74383984b29e8cc65 (codeberg main has moved past 6b1f70ab9f25a57be071262aee76091f4b4cc1a4, the base of every B upstream branch).

Ownership summary: 0~20260321+0b77e1b-1+unity2 and 4.8-1+unity1 are A's [HF: ~/AGENTS-LOG.md:116-117,130-131,197-206; D/DECISIONS.md:957]. Package handed to B 2026-09-26 [HF: D/status/A.md:42; D/status/B.md:104-105; D/DECISIONS.md:1289-1290]. 4.8-1+unity2 and +unity3 are B's [HF: AGENTS-LOG.md:284-286,414].

---


#### Collector preamble G5

Scope: read-only reconciliation, 2026-09-27. Meta-repo HEAD `30499ff` [CURRENTLY_VERIFIED: `git -C ~/unity-distro log -1`], worktree clean [CURRENTLY_VERIFIED: `git status --short` empty].
Paths relative to `~/unity-distro/docs/` unless absolute. Coordinator snapshot `05-status-B.md` is byte-identical to `status/B.md` [CURRENTLY_VERIFIED: `diff -q ~/coordinator/migration-20260927/05-status-B.md docs/status/B.md`].

Ownership notes:
- `research/recheck-2026-09-26/` is **agent A's** (A-1/A-2), not B's [HISTORICAL_FACT: research/recheck-2026-09-26/README.md:1; commits 43ce18a, 0a22fb5, d7ab656]. B's re-check is DECISIONS 2026-09-25 "Re-check of agent B's fixes" [HISTORICAL_FACT: DECISIONS.md:1047-1084] — covered as G5-13.
- `research/nocsd-desktops/` is B's [HISTORICAL_FACT: research/nocsd-desktops/README.md:3].
- The nux `Validator` finding is **agent A's** (2026-09-22, before B registered 2026-09-23 22:39Z) [HISTORICAL_FACT: commit 3e206c1 2026-09-22T18:28Z; ~/AGENTS.md B registration line].

---
