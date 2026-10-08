# UNITY-20261002-012: the automount helper mounts only in an unlocked session

Agent A, target `target-desktop`.

## What is fixed

| package | version | change |
|---|---|---|
| unity-settings-daemon | 15.04.1+21.10.20220802-0ubuntu7+unity12 | The automount helper mounts a volume only when the session is known to be unlocked: logind's `LockedHint` for the session has been read and is "no", and every lock provider present on the bus has answered "unlocked". Any unknown state queues the volume. Volumes present at login go through the same check. Fixes a use-after-free when the volume queue is drained, and a missing reference drop when a queued volume is removed. |

## Build

Built with `scripts/build_sbuild.py` from this task's package branch
(unity-settings-daemon `a/UNITY-20261002-012`, b116af2), in chroot snapshot
T=20261008T083223Z. The manifest is in `build-usd/`.

## Checks (properties measured on the target)

The target is the published stack plus unity-settings-daemon +unity12.

- In an unlocked session the helper mounts no worse than +unity11.
- A medium present at login is mounted.

Target record: `gate/target-test.txt`. tested_build: this_build.

## Verification

- **Design and code review** (Design Challenger, temporary subagent):
  APPROVE after the reviewer asked for two changes:
  - presence of a lock provider is unknown until the bus-name watchers
    report;
  - a provider that vanishes re-checks the queue.
- **Verifier** (independent temporary subagent): PASS, review status
  REVIEWED. It checked:
  - the code against the design;
  - the build provenance (manifest, chroot, artifact hashes, source tarball
    equal to `git archive b116af2`);
  - the target results above.
- **Follow-ups on the board:**
  - UNITY-20261008-009: unit tests for the unlocked-only check, covering
    the locked and unknown states;
  - UNITY-20261008-010: a lock-provider proxy that is replaced before it
    is ready is not freed.

## Publication (slot 1)

- **Database backup:** `/home/claude/backups/UNITY-20261002-012-20261008T180458Z`.
  18 files, complete, equal to live; list sha256
  `06d522cf38023ae3fab6ccf30395b05d556da5cf003960ba91e505e9ca3222b6`.
- **Repository:** 8 records added to `unity-resolute` (the source, 5 .deb
  and 2 .ddeb). The sha256 of every pool file matches the build manifest.
- **Snapshot:** `unity-resolute-20261002-012-usd`, which is the live
  `unity-resolute-20260929-001` plus these 8 records
  (`gate/snapshot-diff.txt`).
- **Version safety:** SAFE (`gate/version-check.json`,
  `gate/version-safety.json`).
- **Peer notice:** agent B, ACK.

## Slot 2: unity +unity13 (UNITY-20261008-015)

| package | version | change |
|---|---|---|
| unity | 7.7.1+26.04.20260306-0ubuntu3+unity13 | `GetActive` on `org.gnome.ScreenSaver` answers true while the session is locked, not only while the screen is blanked. `ActiveChanged` is sent once per change of that value. While Unity's own lockscreen is the session's locker, the lock is reported to logind with `SetLockedHint`. In legacy mode (screen reader or on-screen keyboard enabled) the hint is left to the other locker. |

**Build.** Built with `scripts/build_sbuild.py` from the unity package
branch `a/UNITY-20261002-012` at c5339fc6 (tree 8b742c7b), in chroot snapshot
T=20261008T083223Z. The published nux 4.0.8+18.10.20180623-0ubuntu15+unity3
was passed as an extra package, as for the previous unity build. The
manifest is in `build-unity/`.

The same tree was built three times, all in the same chroot with the same
nux:

1. under the commit 80d5fc4e, whose messages were later rewritten (the tree
   is unchanged); this is the build the earlier target tests used;
2. under c5339fc6 for another task ID;
3. under c5339fc6 for this task (the gated build).

Builds 1 and 3 are byte-identical in all 10 packages. Build 2 differs only
in `libunityshell.so`, and only in `.note.gnu.build-id` and
`.gnu_debuglink`, which follow the debug information. Code and data
sections are identical in all three.

The gated build was also tested on the target in its own right
(this_build).

**Checks (properties measured on the target).** The target is the published
stack after the update from the live repository (unity-settings-daemon
+unity12, hud +unity4) plus unity +unity13.

- In the published configuration another locker owns the ScreenSaver names
  and locks the session. Unity is not locked, and it reports that: its
  `GetActive` is false, `LockedHint` stays "no", and Unity sends no
  `ActiveChanged` and calls no `SetLockedHint`.
- With Unity's lockscreen as the locker (a run outside the published
  configuration, with the other locker kept out of the session, then
  restored):
  - while locked, `GetActive` is true and `LockedHint` is "yes", with one
    `ActiveChanged(true)` and one `SetLockedHint(true)`, both from Unity;
  - after the unlock both are false and "no", with one `ActiveChanged(false)`
    and one `SetLockedHint(false)`.
- **Unit tests** (the session manager and the ScreenSaver D-Bus manager
  suites, built with tests enabled from the same tree, outside the package
  build, which has tests disabled):
  - with the fix, all 52 + 12 tests pass;
  - with the fix's logic reverted, exactly the four new tests fail.

Target record: `gate-015/target-test.txt`.

**Verification.**
- Design and code review: APPROVE after one change. A switch from legacy
  mode back to Unity's lockscreen no longer writes "no" over another
  locker's hint.
- Verifier: PASS, review status REVIEWED.

## Not changed / known limits

- Under cinnamon-session the automount helper does not mount on hotplug at
  all, because `org.gnome.SessionManager` has no `SessionIsActive`
  (UNITY-20261008-008).
- The installed header `UnityCore/SessionManager.h` changes layout (a new
  property) without a soname bump. The only consumer in our repository is
  unity, which depends on libunity-core-6.0-9 with the exact version.
