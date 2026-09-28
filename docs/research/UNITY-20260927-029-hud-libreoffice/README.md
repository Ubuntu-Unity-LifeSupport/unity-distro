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
issue_search_result: UNKNOWN  # pending
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
  FACT (logs/02): when it fails, bamf announces the Writer window
  (ViewOpened window) while the window's parent is a temporary application
  (a pointer-style path, application/0x652c…). Within ~50 ms bamf publishes
  that application, closes it and opens the matched one
  (application/746707297, libreoffice-writer.desktop). A DesktopFile() on
  the temporary one in that window answers UnknownMethod (no application
  interface, or no object), or "".
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
  bamf-matcher.c: LibreOffice sets the window class after mapping).
  window-stack-bridge reads the parent in that window and treats the
  resulting error as permanent.
invariant: window-stack-bridge keeps every window bamf announces, as long as bamf can give its XID
existing_fix_result: UNKNOWN  # pending search
design_challenger_required: true
design_review_result: PENDING
architectural_task: false
correct_layer: PENDING (see "Layer")
unknowns:
  - mechanism 2 (window known, HUD empty) seen once in ~57 starts (the very
    first start of the session in logs/01), not reproduced since, also not
    in 5 first starts after a reboot; its cause is not known
  - the application id stays the window number when the first parent was
    the temporary one (3 of 5 first starts); the HUD still answered in all
    of them, and what the id changes (the HUD's usage history is kept per
    application) is not measured
  - bamf's temporary application lacking its application interface for a
    moment is bamf's own; not traced further
```

## Layer

| Layer | Change | Assessment |
|---|---|---|
| **hud: window-stack-bridge** | on a DesktopFile error keep the window, with the window id as application id, as for an empty desktop file | the component that turns a transient answer into a permanent loss; one branch; fixes mechanism 1 as measured |
| hud: window-stack-bridge, more | follow bamf's re-matching (update the application id when the window gets a new parent) | makes the id right in the 3-of-5 case; more code (subscribe to the new application's children or re-ask on ActiveWindowChanged); not needed for the HUD to answer |
| bamf | announce a window only once it is matched, or keep the temporary application exported until its children moved | re-matching on a class change is by design (LibreOffice changes the class after mapping); every bamf client already sees views come and go; a change in announce order would affect Unity's launcher too |
| LibreOffice | set the final WM_CLASS before mapping | not ours; the class change is legitimate X11 behaviour |

## Status

INVESTIGATING: Design Challenger next, then the existing-fix search, then
the fix in hud with a unit test in tests/unit/window-stack-bridge
(TestBamfWindowStack runs against a D-Bus mock of bamf).
