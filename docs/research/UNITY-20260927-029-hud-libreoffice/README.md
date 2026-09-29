# UNITY-20260927-029: the HUD is empty in some LibreOffice Writer starts

Owner: agent B (target2). This comes from the legacy reconciliation, B-L45.
The HUD (Alt) finds nothing in about a third to half of Writer starts, in
the archive hud as in ours (research/hud: 10/15 and 11/24 good). Two
mechanisms were recorded, neither traced to the end:

1. window-stack-bridge drops the window when bamf has not exported its
   application;
2. the window is known, but its GMenu yields nothing.

```yaml
task_id: UNITY-20260927-029
package: hud
target_series: resolute
issue: local - intermittent empty HUD for LibreOffice (legacy B-L45)
status: REPRODUCED  # mechanism 1; mechanism 2 NOT_REPRODUCED (see below)
issue_search_result: FOUND  # the symptom: LP #1771173 (HUD not working for LibreOffice, 2018, New, no diagnosis); the cause: none; see "Search"
source_version: hud 14.10+17.10.20170619-0ubuntu6 (archive; ours +unity1 is a rebuild with FTBFS fixes)
binary_version: target2 Clean-2: hud 0ubuntu6, bamfdaemon 0.5.6+22.04.20220217-0ubuntu6, LibreOffice 26.2.5.2-0ubuntu0.26.04.1
observed: >
  FACT (logs/01): 12 Writer starts: 4 with an empty HUD. In 3 of them the
  window is missing from window-stack-bridge's GetWindowStack and its
  journal says "Could not get desktop file … UnknownMethod". In 1 (the first
  start) the window is in the stack and the HUD is still empty. 20 more
  starts: 4 empty, all of the first kind. 5 first starts after a reboot:
  1 of the first kind; in 3 the window is kept but its application id is
  the window number (58720292, 60817444) instead of libreoffice-writer.
  FACT (logs/02, observed): in the failing runs Parents() of the Writer
  window names a temporary application (a pointer-style path,
  application/0x652c…). bamf then closes that application and opens the
  matched one (application/746707297, libreoffice-writer.desktop). A
  DesktopFile() on the temporary one answered "no interface
  org.ayatana.bamf.application on object …" (run 14) or "" (run 15). The
  watcher is synchronous and logs signals late, so its timings (~50 ms)
  are only an upper bound.
  FACT (source, bamf 0.5.6): the re-match is on_raw_window_class_changed
  (bamf-matcher.c:2117-2160). When the temporary application loses its last
  child it closes itself (bamf-application.c:1122-1127) and is unregistered.
  (Observed in run 14, though, is an object that still existed without its
  application interface, not a missing object: the exact state is bamf's;
  see unknowns.) So the object can disappear between window-stack-bridge's Parents() and
  DesktopFile() calls (BamfWindowStack.cpp:45, :60) even with bamf working
  as designed. bamf offers ChildAdded/ChildRemoved and
  WindowAdded/WindowRemoved for following it.
  FACT (logs/03, deterministic): with a stand-in bamf on a private bus, the
  installed window-stack-bridge drops a window whose parent application
  does not answer (3 of 3), and gives a window whose application has no
  desktop file its own number as application id (3 of 3).
expected: every Writer window is in the window stack and the HUD answers for it
reproduction: >
  lo4.sh / lo7.sh on target2 (the live stack; ~25% of starts);
  fakebamf-run.sh with fakebamf.py (deterministic, any machine with
  window-stack-bridge and python3-gi)
evidence: logs/01-03
root_cause: >
  window-stack-bridge (hud, window-stack-bridge/BamfWindowStack.cpp): the
  BamfWindow constructor asks Parents() and then the first parent's
  DesktopFile(). On any error it sets m_error, addWindow() never stores the
  window, and nothing retries (ViewOpened is emitted once). An empty desktop
  file already falls back to the window id; an error does not.
root_cause_mechanism: >
  LibreOffice's Writer window is matched by bamf to a temporary application
  first and re-matched a moment later (on_raw_window_class_changed in
  bamf-matcher.c; that LibreOffice sets the window class after mapping is
  inferred from bamf's re-match and TDF #119202, not observed).
  window-stack-bridge reads the parent in that window and treats the
  resulting error as permanent.
invariant: >
  window-stack-bridge keeps every window bamf announces, unless the window
  object itself is gone (GetXid or Parents fails). A parent that
  disappears or answers badly does not lose the window.
existing_fix_result: NOT_FIXED  # see "Search"
design_challenger_required: true
design_review_result: APPROVE  # round 1 REVISE (card and tests), round 2 APPROVE
architectural_task: false
correct_layer: >
  hud's window-stack-bridge (BamfWindow constructor): it is the component
  that turns a parent that disappears mid-query into a permanent loss.
  Parents() and DesktopFile() are separate calls, so no bamf ordering can
  make the second one safe.
defensive_workaround_rejected: >
  Not a guard in the wrong place: the failing call is in this component,
  and the fallback is the one it already uses for an application without a
  desktop file.
unknowns:
  - mechanism 2 (window known, HUD empty) seen once in 37 starts that
    recorded both the window stack and the HUD answer (lo4 12, lo7 20,
    coldloop 5); the 15-run lo7 batch and the 38 observer runs recorded
    failures of mechanism 1 only. That one run (lo4 run 1, the first of the
    session) is also the only one with xid 56623243 and recorded no app id,
    so it is not shown that the measured window was the Writer window and
    not a first-start dialog (Tip of the Day). A second sighting with
    +unity2 (logs/06, cold boot 4, where the changed branch was not taken):
    the HUD answered, and 5 s later did not. At that moment hud-service
    logged DBusMenuImporter "no interface com.canonical.dbusmenu on object
    /org/ayatana/bamf/window…": its dbusmenu collector was pointed at a bamf
    window object. In the same boot window-stack-bridge logged "name
    'org.ayatana.bamf' had owner '' but we thought it was ':1.38'" and
    hud-service activated bamfdaemon.service twice, so bamf may have lost
    its name or restarted there. That is a lead, not a cause:
    UNITY-20260929-002
  - side effects of the window-id fallback (present upstream already for an
    empty desktop file, BamfWindowStack.cpp:75-77): the HUD shows no icon
    (it looks for "<xid>.desktop", ApplicationImpl.cpp:86-103), and usage
    history is stored under the window number (ItemStore.cpp:295,
    SqliteUsageTracker.cpp:117), which repeats across starts (58720292 in
    most runs)
  - the application id stays the window number when the first parent was
    the temporary one. With +unity2 that is 19 of 20 Writer starts (logs/05)
    and 4 of 5 first starts (logs/06), so for LibreOffice it is the usual
    case, not the exception. The HUD still answers; it shows no icon, and
    the usage history is kept under the window number. Following bamf's
    re-match would fix it (UNITY-20260929-001)
  - bamf's temporary application lacking its application interface for a
    moment is bamf's own; not traced further
```

## Layer

| Layer | Change | Assessment |
|---|---|---|
| **hud: window-stack-bridge** | on a DesktopFile error keep the window, with the window id as application id, as for an empty desktop file | the component that turns a transient answer into a permanent loss; one branch; fixes mechanism 1 as measured |
| hud: window-stack-bridge, more | follow bamf's re-matching: on an application's ViewOpened/WindowAdded (and ChildAdded for an already running one) ask Xids() and re-emit WindowDestroyed/WindowCreated for fallback windows | makes the id right in the 3-of-5 case; ~30 lines with its own tests; re-asking Parents on ActiveWindowChanged is not enough (it arrives before the temporary application closes, logs/02). **A follow-up task**, not this one: the HUD answers without it |
| bamf | announce a window only once it is matched, or keep the temporary application exported until its children moved | re-matching on a class change is by design (LibreOffice changes the class after mapping). A client's Parents() and DesktopFile() are two calls with nothing held between them, so the parent can close in between even then; a bamf change would only narrow the window. bamf gives clients the signals to follow re-parenting |
| LibreOffice | set the final WM_CLASS before mapping | not ours; the class change is legitimate X11 behaviour |

## Search (2026-09-28)

A delegated search; the trunk history was checked by the owner through
Launchpad's API.

- **hud upstream:** Launchpad bzr lp:hud, trunk.15.10, 420 revisions. The
  merge proposals merged after the 2017-06-19 snapshot that every Ubuntu
  ships are "reupload-to-focal" (2020-03-05) and "fix-build-vala"
  (2020-03-16), build fixes only. There is no git mirror without login.
  26.10 has the same 0ubuntu6; hud is not in Debian.
- **Launchpad bugs:**
  - LP #1771173, "HUD not working for Firefox, LibreOffice & others in
    18.04" (2018, New): the symptom, with no diagnosis.
  - LP #1243654 and #1238338, #1242032, #1242339 (2013, Fix Released):
    window-stack-bridge crashes, not this silent drop.
  - None mentions "Could not get desktop file".
- **bamf** (from the delegated search, not re-checked by the owner): the re-match is deliberate. Commit dd81623 (2013, "If a Window
  has changed its class, then we try to rematch it", "mostly the case of
  LibreOffice") says the old application "may eventually be closed".
  libbamf itself had to handle re-matched views (453e2d0, LP #1238064).
  Latest resolute/26.10: 0.5.6+22.04.20220217-0ubuntu6.
- **LibreOffice:** TDF #119202 "should not change their WM_CLASS after being
  launched" was fixed for the kde5 VCL only (2018). Whether the gtk3
  backend of 26.2 still does it is inferred from bamf's re-match, not
  checked in LibreOffice.

## Design review, round 1: REVISE (design approved; card text and tests)

- Layer: window-stack-bridge owns it, because the race exists even with
  bamf working as designed; the card now says so (from source, not from the
  launcher argument).
- Invariant reworded: a GetXid or Parents error still drops the window (it
  is gone); only a failing parent no longer does.
- Evidence: "1 in 37 measured" for mechanism 2 with its open alternative;
  observed and source-read parts told apart; the ~50 ms timing is an upper
  bound.
- Side effects of the fallback id recorded under unknowns.
- Following the re-match: a follow-up task.
- Tests: both entry paths (startup WindowPaths and ViewOpened) with
  WindowCreated(id, "<id>"), and WindowDestroyed with the same fallback id.

## Design review, round 2: APPROVE

The design, the code (hud af43552) and the three tests are approved. The
reviewer's wording notes are applied: the WM_CLASS change is inferred; the
observed "no interface on object" state is kept apart from "object gone";
the search references are marked as not re-checked. Before DONE: the
control and +unity2 test results, and a target2 run with +unity2.

## Result

- **Tested binary:** the target2 runs used `hud_…+unity2_amd64.deb` of
  the first build of 0e99dca (sha256 e29723ee17aa47fd…, installed with
  `dpkg -i`). That build came out as a native source package, because no
  orig tarball lay next to the tree (Verifier finding 1). It was rebuilt
  from the same tree as non-native 1.0 (orig.tar.gz + diff.gz, like +unity1;
  the orig is the one +unity1's .dsc names, sha256 3cb825f0…). The `hud`
  package of the two builds has identical contents (0 differing files;
  window-stack-bridge sha256 e7cbdf88…), so the target2 runs stand for the
  rebuild. `build/`: the non-native build (tests 6/6, successful).
- **Package:** hud `14.10+17.10.20170619-0ubuntu6+unity2`, local git tree
  `packages/hud`:
  - 0a94d01 archive 0ubuntu6;
  - 621d1fc +unity1 from its debdiff (identical to the published +unity1
    source);
  - **af43552** the fix and three tests;
  - 0e99dca changelog.

  Source format 1.0 as before: the change is in the tree, not a quilt
  patch.
- **Tests** (logs/04): the control (the tests without the fix) fails
  exactly the three new tests. +unity2 passes all 6 test suites; sbuild
  successful (`build/`).
- **target2 with +unity2:**

  | run | before (archive hud) | +unity2 |
  |---|---|---|
  | lo7 Writer starts: window in the stack | 16 of 20 | 20 of 20 (logs/05) |
  | lo7 Writer starts: HUD answered | 16 of 20 | 20 of 20 |
  | first start after a reboot: window kept | 4 of 5 | 5 of 5 (logs/06; the changed branch was not taken in any of these 5, so this shows no regression, not the fix) |

  "Could not get desktop file" still appears (5 of 20). Now the window is
  kept each time. In one of the 5 cold starts the HUD went empty 5 s later
  without that branch being taken: mechanism 2, see unknowns.
- **Follow-ups:**
  - UNITY-20260929-001: follow bamf's re-match in window-stack-bridge, to
    get the right application id; for LibreOffice it is the window number
    most of the time;
  - UNITY-20260929-002: mechanism 2, with the dbusmenu lead.

## Verification: PASS (REVIEWED), with notes

The independent Verifier read the evidence, the trees and the build logs:
- the base equals the published +unity1;
- the change is one branch plus tests;
- fail before / pass after;
- 20/20 on target2.

Its notes, applied:
- the first build was native (rebuilt, above);
- the cold-boot row shows no regression rather than the fix;
- the bamf name-owner lines belong to the mechanism-2 lead;
- the tested .deb is identified.

`docs/PATCHES.md` and `docs/DECISIONS.md` entries were added through
`append_record.py`.

## Status

REVIEW, then BLOCKED at the publication gate (freeze no. 1).
