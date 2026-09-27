# Legacy state reconciliation - agent A (2026-09-27)

One-off PROCESS BOOTSTRAP / HISTORICAL STATE RECONCILIATION requested by May
through the coordinator. **Read-only**: nothing was built, published, rolled
back, fixed or resumed while writing this file. Author: agent A.

## Labels

- `HISTORICAL_FACT` - recorded at the time in git, aptly, a build log or a
  research/DECISIONS/PATCHES entry; not re-run today.
- `CURRENTLY_VERIFIED` - checked on 2026-09-27 between 16:24Z and 16:33Z (builder clock, UTC) with
  the command named in "How this was checked".
- `UNVERIFIED` - neither recorded with evidence nor checked today.

`migration_result`: `LEGACY_VERIFIED` (reproduced or measured before, measured
after, published version is what target runs today), `LEGACY_PARTIAL` (fix
published and target runs it, but part of the evidence is missing or was never
re-checked), `REQUIRES_REVALIDATION` (root cause or test not proven enough to
rely on), `SUPERSEDED` (replaced, withdrawn or never shipped).
No item had an independent Verifier review, a design review, a build manifest
or a release gate; those gaps are listed once below, not repeated per item.

## How this was checked (CURRENTLY_VERIFIED commands)

- aptly: `aptly repo search unity-resolute '$Source (<pkg>)'` and
  `'Name (<pkg>)'`; `aptly publish list` -> `./resolute publishes {main:
  [unity-resolute]}` (a local repo, **no snapshot exists**: `aptly snapshot
  list` -> "No snapshots found").
- Published binary identity: `sha256sum` of every main binary of A's sources
  under `/srv/aptly/public/pool/main` compared with the local build output -
  **26 of 26 match** a file in `~/work/a/...`, `~/unity-distro/packages/` or
  `~/unity-distro/packages/ll-build/` (list in "Artifact identity").
- git: `git for-each-ref refs/heads` per package repo, `git ls-remote
  <remote> refs/heads/<branch>` for push state, `git merge-base --is-ancestor`
  for local-only branches.
- target: `ssh target dpkg-query -W ...` (boot 2026-09-26 20:26:39, `~/.dirty`
  present), `apt list --upgradable | grep -c +unity` -> 0 **with the apt cache
  of 2026-09-26** (apt was not updated today: read-only rule).
- archive: `rmadison -u ubuntu -s resolute,resolute-proposed,resolute-updates,resolute-security xorg-server` -> 1ubuntu1 (release), 1ubuntu1.2 (-updates), 1ubuntu1.3 (-proposed).
- builder: `systemctl --user is-active xorg-watch.timer` -> active.

## Provenance gap - every published item of A

Published before the current contract. For **every** `+unityN` in the table
below: no `build_sbuild.py` manifest, no recorded source commit or tree hash,
no `version_safety.py` record, no release gate, no Verifier review, no aptly
snapshot (published with `aptly publish update` of the local repo
`unity-resolute`), no publish record in `~/coordinator/publish-records/`,
no task ID. What does exist: the sbuild `.build` log next to each binary, a
matching sha256 between the pool and that local build (CURRENTLY_VERIFIED),
and the branch commit that carries the changelog of that version
(HISTORICAL_FACT - the build was made with `dpkg-source -b` from a working tree,
so the exact commit the tree matched is UNVERIFIED; for native packages it can
be checked by comparing the `.dsc` tarball with the commit, not done today).

Packages without our own git history: **xorg-server** (built from the Ubuntu
`.dsc` plus `docs/research/xorg-versioning/patches/`; no package repository).

## Items

### A-L01 unity: known issue #2 - menu dead after cancel (`+unity1`, `+unity2`)
- package: unity. goal: only the session manager confirms Unity's pending end-session action.
- commits: `31bf416e102b2f8205edfca504ae4a6d2fa4680e` (+unity1 attempt), `aea75d239059c6f650d8e502bdfba22f79af790e`, `e2effde95f853ada73cda1b559bb6dfd8a85c653`, `dd954ff0ffa5df6a0eb24dc4f2471949a28b468f` on `unity/resolute`, pushed to `lifesupport` (github.com/Ubuntu-Unity-LifeSupport/unity) - CURRENTLY_VERIFIED. Upstream-prep branch `mr/stale-pending-action` `280719d1f5fa51820b3ff1b4df96356b7306e1ae`, pushed to lifesupport, never sent upstream - CURRENTLY_VERIFIED / HISTORICAL_FACT.
- versions: source+binary `7.7.1+26.04.20260306-0ubuntu3+unity1`, `+unity2` in aptly - CURRENTLY_VERIFIED.
- build_state: built, logs `~/unity-distro/packages/unity_*+unity{1,2}_amd64*.build` - HISTORICAL_FACT. test_state: reproduced on target, fixed, two unit tests (DECISIONS 2026-09-23 "#2 fixed in Unity"; `research/shutdown-path/`) - HISTORICAL_FACT; re-checked 2026-09-26 on a clean snapshot, 73 cancel cycles clean (`research/recheck-2026-09-26/`) - HISTORICAL_FACT.
- target_state: `+unity11` (contains this) - CURRENTLY_VERIFIED. aptly: latest unity `+unity11`; all: +unity1, 2, 4, 5, 8, 9, 10, 11 - CURRENTLY_VERIFIED.
- refs: PATCHES rows "unity GnomeSessionManager: only the session manager…", `docs/upstream/unity-stale-pending-action/`.
- migration_result: **LEGACY_VERIFIED** - reproduced, fixed, re-checked from a clean snapshot on 2026-09-26.

### A-L02 unity: #6 double dialog path - inhibitors, fading view, no logind bypass (`+unity3` unpublished, `+unity4`, `+unity5`)
- commits: `5521ac19b0e195335b71da66972d01c10ee24287`, `73ff04c939620b7492f64a5e053007836e856e1d` (+unity3, built, never published), `965f2f868f025c38f30247fb13e0d33a883238e6`, `672057a7fbb4c68fa94ea941a6e41a2f2c09b1b1` (+unity4), `1c7677f0274a6ddda0268323e5c087dec755f59e`, `d8a743a0570cee30bce5fae9db1d92d4c265bd8a` (+unity5); pushed (lifesupport) - CURRENTLY_VERIFIED. Branch `wip/confirm-inhibitors` `f0343140136c06208981ff38fe92063103adce73` pushed; its content is in `unity/resolute` - CURRENTLY_VERIFIED.
- versions in aptly: +unity4, +unity5 (no +unity3) - CURRENTLY_VERIFIED. build: logs in `~/work/a/out/` - HISTORICAL_FACT.
- test_state: DECISIONS 2026-09-24 "#6: option A over option B, by measurement", "#6 shipped to our archive as three packages at once" (verified from a clean snapshot via apt) - HISTORICAL_FACT; re-check 2026-09-26: restart 4/4, logout 3/3 one dialog - HISTORICAL_FACT.
- migration_result: **LEGACY_VERIFIED** - measured option A vs B, re-checked 2026-09-26.

### A-L03 unity: unit tests build with googletest 1.17 / GCC 15
- commit `f0343140136c06208981ff38fe92063103adce73`, in `unity/resolute`, pushed - CURRENTLY_VERIFIED. Shipped in every build from +unity6 on (tests stay off in the package build).
- test_state: 51/51 and 20/20 from a clean tree (DECISIONS 2026-09-23) - HISTORICAL_FACT.
- migration_result: **LEGACY_PARTIAL** - test-only change, never re-run since 2026-09-24; package build does not run the tests.

### A-L04 unity: compiz teardown and decorations after a compiz restart (`+unity6`, `+unity7` unpublished, `+unity8`)
- commits: `b49fc7160531f232ccdbad87f12fbf909eed5d4b`, `705e4d3a646271bc2be4cc1d6b65e2520fb2ad34`, `fe02aa6d86697424efe4e2c3b8fbbd1294811ef5` (+unity6), `4fd0e9324432da511feab3c7542c97d39c35cb55`, `ecbba638aef63423956de91435fe25693c797204` (+unity7), `8ba95e5f71c8ea32894320e20b5d1d74ca5864fe`, `659357e3b957939ffdcf26c331566257dc2cd077` (+unity8); pushed; local branch `fix/compiz-teardown` (not pushed, fully contained in `unity/resolute`) - CURRENTLY_VERIFIED.
- aptly: +unity8 (no +unity6/7) - CURRENTLY_VERIFIED. test_state: `research/compiz-restart/` (before/after runs) - HISTORICAL_FACT; not part of the 2026-09-26 re-check - UNVERIFIED since.
- migration_result: **LEGACY_PARTIAL** - measured once on 2026-09-24, not re-checked on the clean snapshot.

### A-L05 unity: LP #2160299 (file manager fallback) and LP #2165662 (shaped shadow) (`+unity9`)
- commits: `53d94899143472573a98f316e1f8cbe311b076c9`, `1d618edeac60ac0502e961f25bbc4de30a900162`, `8bb626d58fc11a08af70e13ef20bb6a190e32be5`; pushed; local `fix/lp-crashes` contained in `unity/resolute` - CURRENTLY_VERIFIED.
- test_state: reproduced before, verified after (`research/unity-lp-crashes/`) - HISTORICAL_FACT. Third-party patches (reporters' MPs).
- migration_result: **LEGACY_PARTIAL** - never re-checked; the shaped-shadow change rebuilds on a missing pixmap (guard-like, see "Doubtful fixes").

### A-L06 unity: known issue #3 - pointer moves, clicks nothing (`+unity10`)
- commits: `f2268bef33bb98b503f98dc1aab550d0a635c271`, `fde810ec73a72f06ff24d323b75b2fe92a43244a`; pushed; local `fix/resize-grab-leak` contained - CURRENTLY_VERIFIED.
- test_state: reproduced with real evdev input, leaked "resize" grab shown in compiz with gdb, 16/50 stuck before, 0/50 after; 0/50 again on the clean snapshot 2026-09-26; title-bar variants identical on +unity9/+unity10 (`research/cursor-stops/`, `research/recheck-2026-09-26/`) - HISTORICAL_FACT.
- migration_result: **LEGACY_VERIFIED** - root cause instrumented, before/after numbers, re-checked; the fix is an early return (see "Doubtful fixes" for the design question).

### A-L07 unity: Python escapes in /usr/bin/unity, unity-uwidgets depends on python3-requests (`+unity11`)
- commits: `d7b3401867d43263079149ec76e9208c44e1c386`, `ee9831e7d163eb672829cad61eca777ca20ae823`, `2040279dadc253e76daad4ac2e1ffacc7a2d1e74`; pushed; local `fix/python-warnings` contained - CURRENTLY_VERIFIED.
- test_state: `python3 -W error` clean, `unity --help` clean, wallpaper import works with requests 2.32.5 on target (DECISIONS 2026-09-26 A-6) - HISTORICAL_FACT.
- target: `unity`, `unity-uwidgets` `+unity11` - CURRENTLY_VERIFIED.
- migration_result: **LEGACY_VERIFIED** - mechanical change, checked live.

### A-L08 unity: experiment "option B" (RequestShutdown/RequestReboot)
- branch `exp/option-b-request-shutdown` `3cd92e249e4285f3e54e2256e2f095a7feb22d34`, pushed to lifesupport - CURRENTLY_VERIFIED. Built as `+unity2+optb1` (`~/unity-distro/packages/unity_*+unity2+optb1.dsc`), never published - HISTORICAL_FACT.
- migration_result: **SUPERSEDED** - rejected by measurement in favour of option A (DECISIONS 2026-09-24).

### A-L09 compiz: XSMP die callback `exit(0)` -> `_exit(0)` (`+unity1`)
- commits `07c0ebe21d9a478f2fcedfa54d24752a2a38e49e`, `740a586bd44df9ea75edcfe636565ade2f8c06c5` on `unity/resolute`, pushed to `origin` = github.com/Ubuntu-Unity-LifeSupport/compiz - CURRENTLY_VERIFIED. Also a local build `+exp1` (`~/work/a/out/compiz_*+exp1*`), never published - HISTORICAL_FACT.
- test_state: 3/7 crashes before, 0/13 after (PATCHES) - HISTORICAL_FACT.
- aptly compiz: +unity1, +unity2; target `compiz-core +unity2` - CURRENTLY_VERIFIED.
- migration_result: **LEGACY_PARTIAL** - measured, not re-checked on the clean snapshot (the 2026-09-26 restart/logout runs had no compiz crash, which is supporting evidence only).

### A-L10 compiz: frame-extents clamp on the window's own viewport (`+unity2`)
- commits `2241828c7ee4cd4c621ccc5ef52d3cffefe64eec`, `5610bd424b5c78226d286b38f8ec5703e51c4f29`, pushed - CURRENTLY_VERIFIED.
- test_state: `research/compiz-restart/` - HISTORICAL_FACT.
- migration_result: **LEGACY_PARTIAL** - not re-checked since 2026-09-24.

### A-L11 cinnamon-session: one end-session dialog under Unity (`+unity1`)
- commit `a8febcc4143b73b8f7c1aeb4c67702b8abf47985` (gbp, patches in `debian/patches`), pushed to `origin` = github.com/Ubuntu-Unity-LifeSupport/cinnamon-session - CURRENTLY_VERIFIED.
- migration_result: **SUPERSEDED** as a version (all patches carried in +unity3, A-L13); behaviour covered by A-L02.

### A-L12 cinnamon-session: dialog when inhibitors have nobody to be shown to (`+unity2`)
- commit `5819ad8722e1b3c5e446ac6354e6e44c9bcf29ec`, pushed - CURRENTLY_VERIFIED.
- migration_result: **SUPERSEDED** as a version (in +unity3).

### A-L13 cinnamon-session: #214 backport + request reboot/shutdown once (`+unity3`)
- commits `76635a14bce598a386a6e2d07909e035fa2a8c70`, `c38715c307b8578e6f293de3a6c77fb7a675803d`, `7a42c71c721183fb67d1cb0c1b677556173bc874`, `fadd8c6e97a43bb2d0e205da2fb8389b0c3a8ee3`, `patch-queue/unity/resolute` `a3d4c79ed27a8df070e35a9584b406ef01ccee40`; all pushed - CURRENTLY_VERIFIED. **Two commits both say `+unity3`** (`c38715c…` then `fadd8c6…`); which tree the published build came from is UNVERIFIED.
- test_state: 12 restart requests -> 1, session gone in 3 s (`research/cinnamon-session-214-202/`); release re-check found none of the five patches in 6.6.4 - HISTORICAL_FACT.
- aptly: +unity1, +unity2, +unity3; target +unity3 - CURRENTLY_VERIFIED.
- migration_result: **LEGACY_PARTIAL** - measured, but the version-to-commit ambiguity above.

### A-L14 lightdm: SIGTERM handler leaves with `_exit()` (LP #2168421) (`+unity1`)
- commits `91ac0049a44ed678feec3a39bf6535156aa7deaf`, `50a6a5dd8974a95db064f4a19dabe22becc329c0`, `patch-queue` `26bc280c70a5cfae035c2288d342e5ba5552db20`, pushed to lifesupport - CURRENTLY_VERIFIED.
- test_state: reproduced on the real binary only under the reporter's conditions (libgnutls loaded); target's default PAM stack does not trigger it (`research/lightdm-sigterm-exit/`) - HISTORICAL_FACT. Upstream #484 open, not in 1.33.1 (release re-check) - HISTORICAL_FACT.
- migration_result: **LEGACY_PARTIAL** - not reproducible on our default configuration.

### A-L15 light-locker: follow the display session / find the LightDM session (#5) (`+unity2`)
- commits `26fb96d021ee77beca73df81c653693476549c6c`, `518fdadbfa160174d1f3192c9c34a284cf3929ed` (+unity1), `5c06ce56dffb5b1ee5f4bfc63ad3f816108774de`, `ce58b9a926336f8e7f3c6f80b80b1614105d6716` (+unity2), pushed to `origin` = github.com/Ubuntu-Unity-LifeSupport/light-locker - CURRENTLY_VERIFIED.
- test_state: stock light-locker aborted at every stock boot after the 2026-09-26 rollbacks (5 of 5, `/var/log/apport.log*` on target), none on ours in ~30 boots (`research/recheck-2026-09-26/`) - HISTORICAL_FACT.
- aptly: only +unity2; target +unity2 - CURRENTLY_VERIFIED.
- migration_result: **LEGACY_VERIFIED**.

### A-L16 unity-session: login race, guard the stop in run-systemd-session (`+unity1`)
- commits `0078ead823c04b3c5ec246c9a3673ef724b716fd`, `951b46361fb28378a12044638a198c2273e2f8a3`, pushed to lifesupport - CURRENTLY_VERIFIED.
- test_state: race seen 3 logins in 13 before (`research/login-gvfs-race/`), after-fix numbers in that README - HISTORICAL_FACT (not re-read today).
- migration_result: **LEGACY_PARTIAL** - not re-checked since 2026-09-24.

### A-L17 unity-settings-daemon: cursor plugin guess and xvfb tests (`+unity1`)
- commits `bc1d84304b541a8d2037140fcdd5bc6f9a4c7035` (cursor), `682b9eada26abc908a252122c71beba73be75435`, `cf8794e9876fa9026ca13f9f002281d05628aa9e` (xvfb-run tests), pushed - CURRENTLY_VERIFIED. The cursor change was reverted in +unity4 (`3b549066b2c2aee5542567588f551622bfe333f8`).
- migration_result: **SUPERSEDED** - the cursor change was a guess, replaced by A-L19; the xvfb test change survives in later versions.

### A-L18 unity-settings-daemon: color plugin crash at logout and restart (`+unity2`, `+unity3`)
- commits `10bb1c9500a8d14aabd33f51c35e68cf719a1565`, `1180e2186818ae56858d620fce1e3057f7556f33`, `cc665b60b410612c6ff9a93cbc87aef3a71b6a37`, `63119bab8240fccf404ae9ad23e5f01e5deac86e`; pushed (`unity/resolute`); local branch `fix/color-restart` contained - CURRENTLY_VERIFIED.
- test_state: `research/usd-color-logout-crash/` - HISTORICAL_FACT.
- migration_result: **LEGACY_PARTIAL** - not re-checked since 2026-09-25.

### A-L19 unity-settings-daemon: known issue #1 - pointer invisible after login (`+unity4`)
- commits `90f57737d9f952bbe42a041cb52055bf350743a3` (idle monitor filter), `b503ffde1addf6b49de8c2b72957193c421578cc` (libexecdir), `85d351158c4a063a87028276f1e3dbdef2b9c8ba` (single launcher), `3b549066b2c2aee5542567588f551622bfe333f8` (revert), `40ed659438ec97fa4f4e57cea6731eb79f3ce9ce`; pushed - CURRENTLY_VERIFIED.
- test_state: archive 2/12 hidden, +unity4 0/12; gdb re-adding the filter showed the pointer; deterministic reproducer 3/3 vs 3/3; greeter login 12/12, relogin 11/11, user switch 12/12; clean-snapshot series 12/12 (`research/cursor-after-login/`, `research/recheck-2026-09-26/`) - HISTORICAL_FACT.
- migration_result: **LEGACY_VERIFIED**.

### A-L20 unity-settings-daemon: apport hook raw string (`+unity5`)
- commits `c7d66302bd3610539aacb1db641578e2e8c2ecfc`, `d2c24b7e883f7e597211aa9507ca2fe9ea84861b`; pushed - CURRENTLY_VERIFIED. test_state: `py_compile -W error` clean in the built package - HISTORICAL_FACT. aptly: +unity1..+unity5; target +unity5 - CURRENTLY_VERIFIED.
- migration_result: **LEGACY_VERIFIED** - mechanical.

### A-L21 xorg-server: 11 CVEs and FindGlyphRef (`21.1.24-1ubuntu1~26.04.1` removed, `1.3+unity1` removed, `1.3+unity2`)
- no package git repository. Carried series: `docs/research/xorg-versioning/patches/series-carried.txt` (31 upstream commits 21.1.22..21.1.24 + `8d604fa14`) - HISTORICAL_FACT. Sources: `~/work/a/xorg/cl/b13u2/` (not a git tree) - HISTORICAL_FACT.
- versions: aptly holds only `2:21.1.22-1ubuntu1.3+unity2` - CURRENTLY_VERIFIED; `~26.04.1` and `1.3+unity1` were removed from aptly (DECISIONS 2026-09-25/26) - HISTORICAL_FACT. Archive: resolute-proposed still `1ubuntu1.3`, no newer resolute upload - CURRENTLY_VERIFIED (`rmadison`).
- test_state: CVE triggers deliberately not reproduced; smoke test + logout cycles only - HISTORICAL_FACT. The changelogs of `+unity1/+unity2` say "29 fixes" - actually 31 (DECISIONS correction) - HISTORICAL_FACT.
- target: `1.3+unity2` - CURRENTLY_VERIFIED.
- migration_result: **LEGACY_PARTIAL** - security fixes applied without reproduction; version scheme measured with apt.

### A-L22 xorg-watch.timer (builder monitoring)
- units in `docs/research/xorg-versioning/` and `~/.config/systemd/user/`; `systemctl --user is-active xorg-watch.timer` -> active - CURRENTLY_VERIFIED. `grep -c 'XORG-WATCH new upload' ~/AGENTS-LOG.md` -> 0: no alert written so far - CURRENTLY_VERIFIED. Whether the Launchpad query still works was not re-run today - UNVERIFIED.
- gap: writes alerts into `~/AGENTS-LOG.md`, which the new process calls activity history only; alerts should reach the coordinator/task board instead.
- migration_result: **REQUIRES_REVALIDATION** - works, but its output channel predates the process.

### A-L23 unity-greeter: rebuildable after the lightdm-vala split (`+unity1`)
- commits `18f1cdc1e037a5cddee28c2426a1fd32324d1132`, `8baefeff895b7ca5cb51918b83b68ac24262c937`, `cc86227a5ea1952b2c28f0f21303b6b9a52fb046`, `0e71beffcf57042ce84f81a6d8291d97e1ee28c0` on `unity/resolute`, pushed to lifesupport (repo created 2026-09-26) - CURRENTLY_VERIFIED. `cc86227…` mixes a test change and a changelog line (amended).
- test_state: live greeter, password login, user switch and back on target (`research/unity-greeter-rebuild/`); package tests compile and run but fail under valgrind (ignored, as before) - HISTORICAL_FACT.
- target `+unity1` installed; lightdm config says `greeter-session=lightdm-greeter` (the alternatives name) - CURRENTLY_VERIFIED; which greeter that link resolves to today was not checked - UNVERIFIED.
- migration_result: **LEGACY_VERIFIED** - build fix, live check done.

### A-L24 session-migration: CMake 4 and '+' in the build path (`+unity1`)
- commit `35f62a312de8262b043cd2fe2d04ed25ff892fe9` on top of the archive import `d8d054d34cde…`, pushed to lifesupport - CURRENTLY_VERIFIED. Patch prepared by agent B (`docs/package-patches-b/debdiff/`), built and verified by A.
- test_state: 9/9 tests; a test migration ran once at the first login, not at the second (two reboots) - HISTORICAL_FACT.
- target +unity1 - CURRENTLY_VERIFIED. migration_result: **LEGACY_VERIFIED**.

### A-L25 unity-control-center: apport hook, libcrypt-dev (`0ubuntu13+unity1`)
- commits `467c7ef837d68ea5a4ed25fe7cef8b96ec487254`, `b5ef7afd654b0a90a06a5cdf4e83be4a9ea6c2b3`, `98e70731225555607145d229d8e08d4316d4d25f`, `1ab1f21f560032d3957b215e8628e6fd2b3a6a3a`, pushed to lifesupport - CURRENTLY_VERIFIED.
- migration_result: **SUPERSEDED** as a version by +unity2 (A-L26), content carried.

### A-L26 unity-control-center: network panel sort on a missing title (`0ubuntu13+unity2`)
- commits `5059f797479d033ad0c74a83683080db5d895804`, `ef8324f7d93d8c7babe499f2d17282074e76e117`, pushed - CURRENTLY_VERIFIED.
- test_state: 2 CRITICALs at every opening before, 0 after (`research/ucc-panels/`) - HISTORICAL_FACT. Why the title is NULL at sort time was not proven.
- target +unity2 - CURRENTLY_VERIFIED. migration_result: **REQUIRES_REVALIDATION** - a NULL guard without a proven mechanism.

### A-L27 gtk-nocsd `4.8-1+unity1` (before hand-over to B)
- A's commit `92ed59e7b622fe2f76490e3ea04e43131a08f06d` (merge of Debian 4.8-1; on top of A's earlier backports `ddc0822212da927224446f5e15ef76e0997a089c`, `23900a7a468e53a1bf48614b73b4416f82067c38`); the branch now points at B's `a2a074786f6139a82d08f88f4aa42f35fb0a8e7a` (4.8-1+unity3) - CURRENTLY_VERIFIED. aptly: `4.8-1+unity1/2/3` and an older `0~20260321…+unity2` - CURRENTLY_VERIFIED.
- target: `libgtk-nocsd0 4.8-1+unity2` while aptly has `+unity3` - CURRENTLY_VERIFIED; whether target is behind cannot be decided without `apt update` (not run) - UNVERIFIED. B's package since 2026-09-26.
- migration_result: **SUPERSEDED** (by B's +unity2/+unity3).

### A-L28 Research: rule-0 release re-check of A's fixes (`research/release-recheck-a/`)
- measurement builds (cinnamon-session 6.6.4 relaxed, u-s-d 26.10.1ubuntu, xorg-server 21.1.24, lightdm 1.33.1) - HISTORICAL_FACT; outcomes true as of 2026-09-25 only.
- migration_result: **LEGACY_PARTIAL** - time-bound; needs repeating for any new task.

### A-L29 Research: six known issues from a clean snapshot (`research/recheck-2026-09-26/`)
- migration_result: **LEGACY_VERIFIED** as a record; its title-bar finding (1) was withdrawn as a harness artifact the same day (A-2).

### A-L30 Research: cinnamon-session #202 (`research/cinnamon-session-214-202/`, A-4)
- outcome: not reachable in our session (name owned without replacement flags; `g_variant_unref` only in stock boots) - HISTORICAL_FACT.
- migration_result: **LEGACY_VERIFIED** (outcome NOT_REPRODUCED).

### A-L31 Research: every unity-control-center panel (`research/ucc-panels/`, A-7)
- 19/19 panels open, 11 settings applied through the panels - HISTORICAL_FACT.
- migration_result: **LEGACY_VERIFIED** as a record.

### A-L32 Research: unity-settings-daemon libcolor crash at restart (DECISIONS 2026-09-24 "agent A's Layer A list", item 5)
- closed as "probable consequence of the compiz exit crash, not investigated further" - HISTORICAL_FACT.
- migration_result: **REQUIRES_REVALIDATION** - root cause never shown.

### A-L33 Research: #3 before the fix - 400 UI actions, 60 lock cycles, not reproduced (`research/cursor-stops/`, 2026-09-24)
- migration_result: **SUPERSEDED** by A-L06 (the XTEST-driven stress could not trigger it).

### A-L34 Deferred: `Logout(1)` to a background (switched-away) session waits for a dialog
- cinnamon-session asks the inactive session's Unity for the dialog, times out, waits (`research/cinnamon-session-214-202/`) - HISTORICAL_FACT.
- migration_result: **REQUIRES_REVALIDATION** - open, no task.

### A-L35 Deferred: accountsservice does not see autologin set in `lightdm.conf.d`
- `accounts-daemon` reads only `/etc/lightdm/lightdm.conf` (`research/ucc-panels/`) - HISTORICAL_FACT; target's autologin file is our test snapshot's, how the installer writes it is UNVERIFIED. Owner: accountsservice (not ours).
- migration_result: **REQUIRES_REVALIDATION**.

### A-L36 Deferred: unity-control-center info panel updates button needs PackageKit 0.8.x
- permanently disabled with PackageKit 1.3.4 - HISTORICAL_FACT. migration_result: **REQUIRES_REVALIDATION** (old behaviour, no task).

### A-L37 Deferred: activity-log-manager panel untranslated
- owner: activity-log-manager (not ours). migration_result: **REQUIRES_REVALIDATION**.

### A-L38 Deferred: libgnomekbd removal (LP #2136945)
- removed from Debian 2026-08-13; in resolute and 26.10; 26.04 not affected; exit path listed in `research/ucc-panels/` - HISTORICAL_FACT (subagent research, not re-checked).
- migration_result: **REQUIRES_REVALIDATION** - planning item, no task.

### A-L39 Deferred: unity-greeter package tests fail under valgrind
- 150 errors in 8 contexts in one test process; ignored by `debian/rules` (`-dh_auto_test`) - HISTORICAL_FACT. migration_result: **REQUIRES_REVALIDATION**.

## Artifact identity (CURRENTLY_VERIFIED, `sha256sum`, first 16 hex)

cinnamon-session +unity1 8285efb981272202, +unity2 95f1b01efc850ff4, +unity3 b39e41c643032e9c;
compiz-core +unity1 e71d705b30468764, +unity2 dbde150410b6ee92;
light-locker +unity2 3d2425c89ccb84e7; lightdm +unity1 04c1489b6ac10a9a;
session-migration +unity1 d99881863c380a36;
unity-control-center +unity1 babb77a970d3f9c3, +unity2 37ab9911de5c25cd;
unity-greeter +unity1 a344791d473d52c6; unity-session +unity1 6eba77eb6db549f8;
unity-settings-daemon +unity1 8113e10904714be6, +unity2 1e7f4a606ebb5e15, +unity3 0ae2cf23221676d0, +unity4 d9dfc499ed7cba27, +unity5 5cfebe37685e6901;
unity +unity1 166f0e929b3c250c, +unity2 d423774532105857, +unity4 500e90bca65af4ad, +unity5 fd2df7b3eed41f8f, +unity8 6fdef4df2817a6a6, +unity9 6c1d9360a12dbfb7, +unity10 bcd2e2ff3eee094d, +unity11 a55f069e61126bba;
xserver-xorg-core 1.3+unity2 0bb888325e7ac407.
Each equals the local build of the same name; the matching `.build` log sits next to it. Only the main binary of each source was compared.

## Incomplete work (needs a new task ID to continue)

- A-L01 upstream MR (`mr/stale-pending-action`, `docs/upstream/unity-stale-pending-action/`) - prepared, never sent (upstream on hold).
- A-L22 xorg-watch alert channel -> coordinator/task board.
- A-L26 root cause of the NULL title in the network panel.
- A-L32 u-s-d libcolor crash at restart.
- A-L34, A-L35, A-L36, A-L37, A-L38, A-L39 deferred findings.
- Re-checks never done on the clean snapshot: A-L04, A-L05, A-L09, A-L10, A-L16, A-L18.

## Doubtful fixes (root cause, test or scope)

- **A-L06 unity +unity10** - early return in `Edge::ButtonDownEvent` while a "resize"/"move" grab exists. Root cause instrumented, but under the current rules an early return needs a design review (correct layer: Unity dropping compiz's X grab vs compiz keeping its internal list); compiz hardening was weighed and not done.
- **A-L26 u-c-c +unity2** - NULL guard in the sort; the mechanism that yields a NULL title was not shown.
- **A-L05 unity +unity9** - third-party patches; the shaped-shadow change rebuilds on a missing pixmap (guard-like); not re-checked.
- **A-L14 lightdm +unity1** - reproduced only with the reporter's PAM conditions, not on our default stack.
- **A-L13 cinnamon-session "request reboot/shutdown once"** - a once-guard in `csm_manager_quit()`; the repeated `end_phase()` re-entry it suppresses is upstream behaviour kept as is.
- **A-L21 xorg-server** - 31 upstream commits carried where 11 CVE fixes were the goal (includes hardening commits beyond the CVEs); CVE triggers not reproduced; changelog text says 29.
- **A-L19 u-s-d +unity4** - three changes in one version (filter, launcher, libexecdir) plus a revert; the libexecdir change also re-enabled autostart entries that had been dead since the 0ubuntu7 base (effects checked for u-s-d and the mount helper only).
- **A-L23 unity-greeter** - package tests still fail (valgrind); `cc86227…` mixes a test change with a changelog line.

## Counts

- items: 39 (A-L01…A-L39)
- LEGACY_VERIFIED: 12 (L01, L02, L06, L07, L15, L19, L20, L23, L24, L29, L30, L31)
- LEGACY_PARTIAL: 11 (L03, L04, L05, L09, L10, L13, L14, L16, L18, L21, L28)
- REQUIRES_REVALIDATION: 9 (L22, L26, L32, L34, L35, L36, L37, L38, L39)
- SUPERSEDED: 7 (L08, L11, L12, L17, L25, L27, L33)
- provenance gap: every published version (26 source versions in aptly across 11 source packages of A's zone, plus gtk-nocsd 4.8-1+unity1 now in B's zone) - no manifest, gate, version-safety record, snapshot or publish record.
- doubtful fixes: 8; incomplete items needing a task: 10 (+6 re-checks never done on the clean snapshot).
