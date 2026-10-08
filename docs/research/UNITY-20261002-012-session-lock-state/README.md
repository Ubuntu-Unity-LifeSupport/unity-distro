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

## Not changed / known limits

- Under cinnamon-session the automount helper does not mount on hotplug at
  all, because `org.gnome.SessionManager` has no `SessionIsActive`
  (UNITY-20261008-008).
