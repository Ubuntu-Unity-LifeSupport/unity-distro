# Stack health

What our Unity 7 session on Ubuntu 26.04 stands on, and how healthy each piece
is outside this project: is upstream alive, what is open against it, did 26.04
break it, are there unfixed CVEs. It exists so May can decide where effort
goes; a dead upstream with nothing open is a useful, low-risk row.

Rules for this file:

- One row per component. A negative result is written like a positive one.
- Every claim has a source (link, or the command that shows it). What was not
  checked is written as "not checked", never guessed.
- Versions are what target runs (host session, 2026-09-24), unless a row says
  otherwise.
- Agent A owns section A, agent B owns section B; each writes only its own.

Columns:

| Column | Meaning |
|---|---|
| Component | source package, and the upstream project if it differs |
| Ours | version on target; `+unityN` = ours from aptly |
| Upstream | last commit and last release, with dates; "dead" if nothing in years |
| Open, important | Launchpad (Ubuntu package): High/Critical, and anything filed since the 26.04 release; upstream tracker if there is one |
| 26.04 regressions | known breakage from the move to 26.04 |
| CVEs | unfixed in 26.04 |
| Risk for us | low / medium / high, one line why |
| Not checked | what is missing from this row |

Checked on: A - 2026-09-24 (Launchpad API, gitlab/GitHub/codeberg APIs, Ubuntu CVE tracker, Debian tracker; searches run in subagents); B - pending.

## Cross-cutting

| Question | Finding | Source |
|---|---|---|
| Python 3.14 (26.04 moved from 3.12; the ISO ships python3 3.14.3-0ubuntu2) - what of our Python code breaks (unity-tweak-tool, lenses/scopes, indicators in Python) | pending (B) | |
| sudo-rs as `sudo`, password echo on by default - what expects the old behaviour | `/usr/bin/sudo` on target is sudo-rs 0.2.13-0ubuntu1.2 (alternatives, auto). Nothing in the Unity stack calls sudo: update-notifier and u-c-c's Sharing panel use pkexec/polkit, software-properties/update-manager only mention it in text. Differences that bite scripts: pwfeedback on, `sudo -E` unsupported (`--preserve-env=VAR` works), env_reset always on, `logfile`/lecture/visiblepw ignored, no sudoers.ldap. LP: 1 High open (#2150073, `sudo apt … \| …` stops in T+), 13 filed since 04-01 incl. sudoedit PAM account bypass #2160217 (fixed upstream 0.2.14, not in ours); no open CVEs. Risk: **low** for the session, **medium** for admin scripts. Not checked: `-n` behaviour, sudoedit from inside Unity. | ssh target; [sudo-rs README](https://github.com/trifectatechfoundation/sudo-rs/blob/main/README.md); [LP rust-sudo-rs](https://launchpad.net/ubuntu/+source/rust-sudo-rs); [26.04 notes](https://github.com/ubuntu/ubuntu-release-notes/blob/main/docs/26.04/summary-for-lts-users.md) |
| Xorg in 26.04 - who besides us still ships an X11 session and tests it | Ubuntu (GNOME) and Budgie are Wayland-only; Kubuntu Wayland by default (X11 session in the archive, unsupported); Xubuntu, Lubuntu and Cinnamon depend on xorg (X11 by default, their notes do not say more); Ubuntu MATE shipped no 26.04 image. xorg-server stays in **main** in resolute and 26.10, no announced demotion. So: three flavours plus us. Health of the server itself: row `xorg-server` in section A. | [26.04 notes](https://github.com/ubuntu/ubuntu-release-notes/blob/main/docs/26.04/summary-for-lts-users.md), [Kubuntu](https://kubuntu.org/news/kubuntu-26-04-release-notes/), [Budgie](https://ubuntubudgie.org/blog/ubuntu-budgie-2604-lts-release-notes/), [MATE](https://linuxiac.com/ubuntu-mate-missed-26-04-lts-but-a-new-team-is-keeping-it-alive/), packages.ubuntu.com |

## A - session core

| Component | Ours | Upstream | Open, important | 26.04 regressions | CVEs | Risk for us | Not checked |
|---|---|---|---|---|---|---|---|
| unity (gitlab ubuntu-unity/unity) | 7.7.1+26.04.20260306-0ubuntu3+unity8 | Packaging only: last commit 2026-04-21 (individual volunteers); last release 7.4.0, 2016. A team member's post (Oct 2025) says the lead is absent and 25.10 never went stable ([discourse 71095](https://discourse.ubuntu.com/t/71095)) | 1764 open, 64 High/Critical (mostly 2010-2017). Since 04-01: [#2160299](https://bugs.launchpad.net/bugs/2160299) crash when the default file manager is neither Nautilus nor Nemo (resolute, patch attached, New); [#2165662](https://bugs.launchpad.net/bugs/2165662) crash in `ComputeShapedShadowQuad`, null pixmap (noble, same code in 7.7.1, patch attached) | #2160299 | None real (CVE-2026-25918 tagged `unity` is the Unity game engine CLI) | **High**: our own fixes are the only maintenance; two crash reports with patches unapplied | Whether #2146966 (snaps unpinned) is fixed in 0ubuntu3; the GitLab MR history. None of our 5 unity fixes is reported anywhere |
| unity-session | 49.4+unity1 | Last commit 2026-09-15 (licence file), last real change 2026-03-31 | 1 open ([#2137437](https://bugs.launchpad.net/bugs/2137437) packaging); nothing since 04-01 | None found | None | **Low**: tiny package; our login race (fixed) was not reported anywhere | - |
| unity-greeter | 25.04.1-0ubuntu1 | Dormant: last commit 2024-11-15 (Canonical, packaging); last release 17.04.1, 2016 | 362 open, 26 High/Critical (2011-2022); nothing since 04-01 | None found | None | **Medium**: nobody maintains it; any lightdm/GTK change is ours to follow | Whether it works with lightdm 1.33 if that comes |
| compiz (lp:compiz) | 1:0.9.14.2+25.10.20250930-0ubuntu3+unity2 | Last commit 2025-09-30 (one volunteer, Shachnev); last release 0.9.14.2, 2022; last code upload 2025-09-30 | 40 High/Critical (8 Critical), almost all 2011-2016, untriaged; since 04-01 only [#2157485](https://bugs.launchpad.net/bugs/2157485) (flashback Alt-Tab, noble) | None filed | None for 26.04 | **Medium**: single volunteer, no release since 2022 | Whether [#1555734](https://bugs.launchpad.net/bugs/1555734) (compiz crash on unity logout, 2016) is our XSMP `exit(0)` crash; errors.ubuntu.com. Our 2 compiz fixes: not reported |
| bamf | 0.5.6+22.04.20220217-0ubuntu6 | Last commit 2025-08-08 (Trevisan, snap/flatpak app-id matching, not in Ubuntu); last release 0.5.6, 2022 | 5 High (2012-2016); nothing since 04-01 | None found | None | **Low**: small, quiet | Whether the 2025-08 matching fix matters for us |
| unity-settings-daemon | 15.04.1+21.10.20220802-0ubuntu7+unity1 | Last commit 2026-04-14 (one volunteer). **Resolute has 0ubuntu6; 0ubuntu7 was never uploaded** - our base is the unreleased git head. 26.10 has `26.10.1ubuntu` (sorts above ours) | 121 open, 14 High/Critical (2014-2016); since 04-01 only [#2148713](https://bugs.launchpad.net/bugs/2148713) (packaging) | None | CVE-2015-1319 only, fixed | **Medium**: one maintainer, and our base differs from the archive | Runtime changes in `26.10.1ubuntu`. Cursor-hidden: only [#1390628](https://bugs.launchpad.net/bugs/1390628) (2014). libcolor crash: not filed |
| unity-control-center | 15.04.0+23.04.20230220-0ubuntu13 | Last commit 2026-03-31; unmerged branch 2026-07-16 moving Bluetooth to Ayatana | 336 open, 20 High; [#2136945](https://bugs.launchpad.net/bugs/2136945) "stop using libgnomekbd" (High); nothing since 04-01 | None; all Depends present in resolute | None | **Medium**: works, but depends on libgnomekbd (archived upstream) and old indicator-bluetooth | Every panel actually run |
| cinnamon-session (linuxmint) | 6.4.2-1+unity2 | Active: last commit 2026-09-22; stable 6.6.4 (2026-06-18) in Debian sid and 26.10; resolute is a series behind | LP: 0 open. GitHub since 2026: [#202](https://github.com/linuxmint/cinnamon-session/issues/202) session aborts on `g_variant_unref(NULL)` to the greeter (open); [#214](https://github.com/linuxmint/cinnamon-session/issues/214) session not closed at shutdown with a `delay` inhibitor (fixed in 6.7 only); #216 intermittent reboot failure | None on LP | None | **Medium**: #202/#214 are in the end-of-session code our patches touch | Whether #202 reproduces on 6.4.2; overlap of the #214 fix with our inhibitor patch. Our 2 fixes: not reported upstream |
| cinnamon-settings-daemon | 6.4.3-1build1 | Active: 2026-09-22; stable 6.6.4 | 2 open, none High; nothing since 04-01 | None | None | **Low**: does not run under Unity | Whether nemo or cinnamon-session use any of its schemas |
| nemo (linuxmint) | 6.4.5-1build1 | Active: last commit 2026-09-24; stable 6.6.4 (Feb 2026) in Debian sid and 26.10 | 71 open, 1 High (2017); since 04-01 [#2167243](https://bugs.launchpad.net/bugs/2167243) glycin without sandbox (resolute). GitHub: 104 issues in 2026 - hangs on stale MTP mount (#3834), SMB, crashes (#3782, #3787, #3794), memory growth (#3702) | #2167243 | CVE-2022-37290 (medium) needs-triage for resolute; upstream #3671 (autorun command injection, reporter: low) open | **Medium**: it is our desktop; many open crash/hang reports | Which GitHub crashes reproduce on 6.4.5; whether the glycin message is only a warning |
| light-locker | 1.8.0-3ubuntu4+unity2 | **Dead**: last commit 2019-09-05, last release 1.9.0 (2019) | 2 High (2016, 2019). Since 04-01: [#2167241](https://bugs.launchpad.net/bugs/2167241) "crashes every time plasma opens" - same abort pattern as ours ([#2038808](https://bugs.launchpad.net/bugs/2038808)); #2154403 | #2167241 (Kubuntu) | None | **High**: no upstream; our fix is the only fix | Whether #2167241 is exactly our `init_session_id` abort (trace unsymbolized) |
| lightdm (canonical/lightdm) | 1.32.0-6ubuntu4 | Revived: 1.33.0/1.33.1 in Aug 2026, last commit 2026-08-31; resolute has 1.32.0 (2022) | 17 High/Critical (newest 2024). Since 04-01 (all third-party): [#2168421](https://bugs.launchpad.net/bugs/2168421) = [lightdm#484](https://github.com/canonical/lightdm/issues/484) SIGTERM handler calls `exit()`, 90 s login hang (filed 2026-09-24 by Markus Kuhn); #2154813 lightdm.conf overrides conf.d; #2161262, #2150287, #2150781. Upstream: #435 double free on XDMCP timeout in 1.32.0 | None 26.04-specific | 12 historical, none open | **Medium**: #2168421 is a login hang we could hit; a feature release behind | Whether 1.33 is planned for resolute; error tracker |
| gtk-nocsd (codeberg MorsMortium) | 3+0~20260321+0b77e1b-1+unity2 | Very active: 4.0-4.8 between 2026-04-28 and 09-12; Debian and 26.10 have 4.8-1; resolute unchanged since 03-22, no SRU | 0 High; since 04-01 [#2158965](https://bugs.launchpad.net/bugs/2158965) Chromium browsers lose decorations on Unity (Confirmed; = codeberg #67, upstream says take a newer version) | #2158965 | None | **Medium**: resolute misses six months of fixes; ours carries two backports only | Which 4.x fixes #67. Our crash-handler bug: not reported on LP/Debian |
| xorg-server | 2:21.1.22-1ubuntu1 (-updates has -1ubuntu1.2, not security) | 21.1 branch maintained: last commit 2026-08-31, 21.1.24 on 2026-07-08; XLibre fork active | 23 High/Critical (2011-2024), 287 open. Since 04-01: [#2163497](https://bugs.launchpad.net/bugs/2163497) FindGlyphRef crash (upstream fix not backported), #2162118 NVIDIA freeze, #2158792 merge 21.1.23 | #2163497 | **11 open, medium, needs-triage**: CVE-2026-50256..50264 (fixed in 21.1.23), CVE-2026-55999/56000 (21.1.24); 21.1.24 only in 26.10-proposed | **Medium**: fixes exist upstream, not in resolute | Whether a resolute security upload is queued; whether our session hits #2163497 |

**A - what could turn into work** (options for May, nothing started):

- unity [#2160299](https://bugs.launchpad.net/bugs/2160299) and [#2165662](https://bugs.launchpad.net/bugs/2165662): crash reports with patches attached, in code we carry; #2165662 is in the decoration shadow code we changed in `+unity8`.
- xorg-server: 11 medium CVEs fixed upstream (21.1.23/21.1.24) and open in resolute.
- lightdm [#2168421](https://bugs.launchpad.net/bugs/2168421): 90 s login hang from `exit()` in the SIGTERM handler.
- cinnamon-session [#214](https://github.com/linuxmint/cinnamon-session/issues/214)/[#202](https://github.com/linuxmint/cinnamon-session/issues/202): end-of-session bugs next to our patches; 6.6.4 is in 26.10.
- gtk-nocsd 4.8 (26.10) fixes Chromium decorations on Unity ([#2158965](https://bugs.launchpad.net/bugs/2158965)).
- light-locker [#2167241](https://bugs.launchpad.net/bugs/2167241): probably our abort, reported under Kubuntu - evidence for our fix.
- None of our own fixes (unity 5, compiz 2, cinnamon-session 2, unity-session 1, light-locker 1) is reported anywhere.

## B - toolkit, indicators, menus, lenses

| Component | Ours | Upstream | Open, important | 26.04 regressions | CVEs | Risk for us | Not checked |
|---|---|---|---|---|---|---|---|
