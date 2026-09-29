# UNITY-20260927-041: calamares-settings-ubuntu, Ubuntu Unity sudoers.oem ships 0644

Owner: agent B, VM `oem-test`. Found during UNITY-20260927-021
(`docs/research/calamares-oem/README.md`, "Seen along the way").

```yaml
task_id: UNITY-20260927-041
package: calamares-settings-ubuntu
target_series: resolute
issue: >
  local: Makefile line 51 copies ubuntuunity/oem/sudoers.oem into the
  Ubuntu Unity oemconfig and then chmods kubuntu/oemconfig/etc/sudoers.oem
  instead, so the Ubuntu Unity sudoers.oem keeps mode 0644 and becomes
  /etc/sudoers of the installed system in OEM mode
status: REPRODUCED
issue_search_result: NOT_FOUND  # Launchpad calamares-settings-ubuntu "sudoers", all statuses: 0
source_version: 1:26.04.12 (resolute); ours 1:26.04.12+unity1 published, +unity2 pending (UNITY-20260927-021)
binary_version: calamares-settings-ubuntu-unity 1:26.04.12 (archive) and +unity1/+unity2 - same mode
source_commit: c03daf4e  # branch b/UNITY-20260927-021 of the packages clone (+unity2, not published)
observed: >
  oemconfig.tar.gz in calamares-settings-ubuntu-unity 1:26.04.12:
  ubuntuunity/oemconfig/etc/sudoers.oem -rw-r--r-- root/root (Kubuntu and
  Lubuntu: -r--------). On oem-test in OEM mode (snapshot OEM-ready, archive
  package): /etc/sudoers 644 root:root, /etc/sudoers.orig 440 root:root.
  sudo-rs 0.2.13 (the active alternative) and sudo.ws 1.9.17p2 both run with
  0644 and log nothing; visudo -c of both reports "bad permissions, should
  be mode 0440".
expected: >
  /etc/sudoers in OEM mode has the mode sudo requires, 0440 root:root, as the
  distribution's own /etc/sudoers (kept as /etc/sudoers.orig) does.
reproduction: see Reproduction below
evidence: logs/01-04
root_cause: >
  Makefile:51 (ubuntuunity section):
  (cp ubuntuunity/oem/sudoers.oem ubuntuunity/oemconfig/etc/ && chmod 400
  kubuntu/oemconfig/etc/sudoers.oem) - the chmod names the Kubuntu copy
  (introduced in c8f33d6, 2024-03-17, "Add Ubuntu Unity config"), so the
  Ubuntu Unity copy keeps the source file's 0644. The tarball is made with
  fakeroot/tar, calamares-oemprep.sh extracts it as root (modes preserved)
  and moves etc/sudoers.oem to /etc/sudoers.
root_cause_mechanism: >
  wrong path in the chmod of the Ubuntu Unity section; tar preserves the
  unchanged 0644 into the OEM system's /etc/sudoers.
root_cause_evidence: docs/research/UNITY-20260927-041-calamares-oem-sudoers/logs/01-oemconfig-modes.txt
invariant: >
  In OEM mode /etc/sudoers is root:root 0440, the mode both sudo
  implementations' visudo -c accept, like the distribution's /etc/sudoers.
existing_fix_result: NOT_FIXED  # stonking 26.10.5 (64cfce8) has the same line 51; no LP bug
candidate_approaches:
  - chmod 440 ubuntuunity/oemconfig/etc/sudoers.oem on line 51 (path and mode)
  - chmod 400 ubuntuunity/... (path only, like the Kubuntu/Lubuntu lines) -
    rejected: measured, 0400 is also "bad permissions, should be mode 0440"
    for visudo -c of sudo-rs and of sudo.ws
  - change the source file's mode in git - rejected: git keeps only the
    executable bit, the build tree's mode is not a reliable input
chosen_approach: line 51 chmods ubuntuunity/oemconfig/etc/sudoers.oem to 440
why_chosen: >
  It fixes the wrong path, and 0440 is the mode sudo checks for and the mode
  of the file it replaces (/etc/sudoers.orig).
alternatives_rejected:
  - see candidate_approaches
code_risks:
  ownership_lifetime: not_applicable
  callbacks_cancellation: not_applicable
  threading_reentrancy: not_applicable
  ABI_API_file_list: checked  # only a mode inside oemconfig.tar.gz changes
design_challenger_required: false
design_review_result: NOT_REQUIRED
architectural_task: false
correct_layer: >
  The Makefile builds oemconfig.tar.gz and is the only place that sets the
  mode of the shipped sudoers.oem; oemprep and the OEM session only extract
  and move it.
defensive_workaround_rejected: >
  A chmod in calamares-oemprep.sh would fix the installed file but leave
  the shipped archive wrong and duplicate the Makefile's job.
unknowns:
  - Kubuntu and Lubuntu ship sudoers.oem as 0400, which visudo -c also
    rejects; not this task (other flavours), reported separately
  - after the end-user setup, calamares-oemfinish.sh removes /etc/sudoers
    and moves /etc/sudoers.orig (0440) back - from code; the finished system
    is not affected by this defect either way
```

## Reproduction

1. `logs/01-oemconfig-modes.txt`: `tar tvzf` of `etc/calamares/oemconfig.tar.gz`
   from the archive `calamares-settings-ubuntu-unity`, `-kubuntu` and
   `-lubuntu` 1:26.04.12 and from our +unity2: Ubuntu Unity `sudoers.oem` is
   `-rw-r--r--`, Kubuntu and Lubuntu `-r--------`.
2. `oem-test` restored to `OEM-ready` (archive package, OEM mode, before the
   end user's first boot), booted; `probe-sudoers.sh` as `oem`
   (`logs/02-oemtest-archive-oem-mode.txt`): `/etc/sudoers` 644 root:root,
   `/etc/sudoers.orig` 440, sudo is sudo-rs 0.2.13, `sudo -n true` works,
   nothing in the journal.
3. `modes.sh` (`logs/03-oemtest-sudo-modes.txt`): for 0644, 0440 and 0400,
   `sudo -n true` with sudo-rs and with sudo.ws, and `visudo -c` of both.
   Both sudo implementations run in all three modes; both `visudo -c`
   accept only 0440 ("bad permissions, should be mode 0440, but found
   0644/0400"). The printed `rc=0` is the pipeline's, not visudo's.
4. `logs/04-existing-fix.txt`: 26.10 has the same line; the line dates from
   `c8f33d6`; no Launchpad bug.

Impact: no failure. sudo-rs neither refuses nor warns; `/etc/sudoers` in OEM
mode is world-readable (its content is the public file from the package) and
fails `visudo -c`. The fix is conformance, not a security hole.

## Implementation

Plan, before the change:

1. Packages clone, branch `b/UNITY-20260927-041` from `c03daf4e`
   (UNITY-20260927-021's +unity2, which restores the changelog; building on
   the published +unity1 would bring the truncated changelog back). One
   commit: Makefile:51 `chmod 440 ubuntuunity/oemconfig/etc/sudoers.oem`,
   changelog entry `1:26.04.12+unity3`.
2. Build; check the mode inside `oemconfig.tar.gz` of the new
   `calamares-settings-ubuntu-unity` (0440), that Kubuntu/Lubuntu tarballs are
   unchanged (0400), and that nothing else in the file lists changes.
3. Regression: `logs/01` check on the built `.deb` (fails on the archive,
   passes on +unity3); on `oem-test`, the installed `/etc/sudoers` in OEM
   mode must be 0440 and pass `visudo -c`.
4. Publication and the target check wait for UNITY-20260927-021 and the
   infrastructure tasks 045-048; this version depends on 021's +unity2.

## Preliminary results (before the gated build)

Change: commit `221c691` on `b/UNITY-20260927-041` of the packages clone
(on top of `c03daf4e`, 021's +unity2), exported in `patches/`: Makefile:51
now reads `chmod 440 ubuntuunity/oemconfig/etc/sudoers.oem`, plus the
`1:26.04.12+unity3` changelog entry.

Plain sbuild (resolute, `Status: successful`; `build_sbuild.py` cannot be
used yet, see UNITY-20260927-021) in `~/work/b/t041/out`:

- `oemconfig.tar.gz` of `calamares-settings-ubuntu-unity`: the only changed
  entry against +unity2 is `ubuntuunity/oemconfig/etc/sudoers.oem`,
  `-rw-r--r--` → `-r--r-----`. Kubuntu and Lubuntu tarballs are unchanged
  (`-r--------`); the file lists of all five `.deb`s equal +unity2's
  (`logs/05-built-unity3.txt`).
- Regression on `oem-test` (OEM-ready, OEM mode): the oemconfig of the
  archive and of +unity3 extracted as `calamares-oemprep.sh` does and its
  `sudoers.oem` moved to `/etc/sudoers` (`oemprep-install.sh`,
  `logs/07-oemtest-installed-sudoers.txt`):

  | oemconfig | /etc/sudoers | visudo -c (sudo-rs, sudo.ws) | sudo -n true (both) |
  |---|---|---|---|
  | archive 1:26.04.12 | 644 root:root | bad permissions, should be mode 0440 | ok |
  | +unity3 | 440 root:root | parsed OK | ok |

  `visudo -c -f` on the extracted file does not check the mode (it is not
  `/etc/sudoers`), so it cannot tell the two apart
  (`logs/06-oemtest-oemprep-steps.txt`); the check has to run on the real
  path.
- `oem-test` was restored to `OEM-ready` afterwards and checked from inside
  (`logs/08-oemtest-restored.txt`).

The target check through the real path (live ISO session → our aptly →
vendor install → OEM mode) runs after publication, together with
UNITY-20260927-021's.

## Gated build (2026-09-29, resumed)

The blockers below are resolved:

- `build_sbuild.py` handles epochs.
- The source is on our GitHub:
  `Ubuntu-Unity-LifeSupport/calamares-settings-ubuntu` `b/UNITY-20260927-041`
  = 221c691, on top of 021's c03daf4.
- 021's +unity2 is published (UNITY-20260927-021 DONE).

Results:

- **Pre-build check** (`gate/prebuild-version-safety.txt`): UNKNOWN, as
  expected before a build. The candidate is newer than resolute 1:26.04.12.
- **Gated sbuild** from `packages/calamares-settings-ubuntu` (221c691):
  manifest PASS, `Status: successful`. Six binaries, as with +unity2.
- **logs/09**, against 021's build-r2:
  - All file lists are the same, except that the build IDs in `-dbgsym`
    change.
  - `oemconfig.tar.gz` of `-ubuntu-unity` has exactly one changed entry:
    `ubuntuunity/oemconfig/etc/sudoers.oem` goes from 0644 to 0440,
    root:root, with the same content.
  - The Kubuntu and Lubuntu tarballs are unchanged (sudoers.oem 0400).
  - The changelog has 96 entries, with +unity3 on top.
  - basicwallpaper's bytes differ (ca88f9c3), although its source is
    unchanged. The difference is only the build ID, the package-version
    note and a build-path string. The target check runs this binary through
    cold boots again.
- **Regression (mode in the shipped tarball)**: 0644 in the archive
  1:26.04.12 (logs/01) and in +unity2; 0440 in +unity3 (logs/09).
- **On the real path**, logs/07 covers the preliminary build. The published
  build is checked in the target verification: live session, our
  repository, OEM install, then `/etc/sudoers` 0440 and `visudo -c`.

## Blocked

Same as UNITY-20260927-021: `build_sbuild.py` (epoch), no remote of ours for
this source, aptly snapshot publication, `version_safety.py` before
publication (infrastructure tasks 045-048). This version also depends on
021's +unity2 being published first. Resume at IMPLEMENTING (gated rebuild).
