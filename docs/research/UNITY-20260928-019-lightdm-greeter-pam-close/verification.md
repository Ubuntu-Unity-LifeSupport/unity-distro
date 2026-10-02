# UNITY-20260928-019 verification record

Candidate: lightdm `1.32.0-6ubuntu4+unity2`, Ubuntu-Unity-LifeSupport/lightdm
`a/UNITY-20260928-019` `f5af23c0b9d5931aea0dfc7a2eaf424415cf8920` (patch
`db13faf`, `d/p/0010-session-child-finish-the-cleanup-when-SIGTERM-arrive.patch`).
Independent temporary Verifier subagents (`.claude/agents/adversarial-verifier.md`);
the task owner (agent A) ran every target test.

| Round | What it reviewed | Verdict |
|---|---|---|
| 1 | test build (`~/work/a/019-build/out/`), card section 4, runs/05-06 | **FAIL** (REVIEWED) - TEST_INVALID: T5 signalled before the handler was installed; user sessions on +unity2 not run |
| 2 | same build, T5 at `fork()`, T7 user sessions, T1b, T6c (runs/07-09) | **PASS** (REVIEWED) - PATCH_CORRECT |
| 3 | gated build (`build-gated/`, `scripts/build_sbuild.py` from `packages/lightdm` at `f5af23c`): manifest identity, payload against the tested build, rt on the gated build (runs/10) | **PASS** (REVIEWED) |

Round 3 facts (recomputed by the Verifier): manifest `result: PASS`, schema
1, `source_commit` `f5af23c` and `source_tree_hash` `aebb2b51...` of the
`packages/lightdm` checkout, log and all 16 artifacts matching their sha256,
the `.dsc` naming exactly the recorded source files, no `build_dependencies`;
the 7 gated `.deb` equal to the tested build's in file lists, `DEBIAN/md5sums`,
`DEBIAN/control` and unpacked trees (`runs/10-gated-vs-test-build.txt`);
`/usr/sbin/lightdm` in the gated `.deb` has the sha256 recorded installed on
target during the full verification (`runs/09`); rt on the gated build
(`runs/10-gated-rt.txt`, `tools/rt-gated.sh`): 3 forced late-SIGTERM and 3
natural greeter stops, all with `pam_close_session`, `pam_setcred` and
`pam_end` returned, no leftover cookie. PATCHES and DECISIONS entries in main.

Limits stated in the card (section 4, Evidence card): when both SIGTERMs are
passed on before reaping no alarm is armed and a blocked cleanup waits for the
90 s scope SIGKILL as before (follow-up UNITY-20260929-006); EINTR inside PAM
modules only incidentally covered.
