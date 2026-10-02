# UNITY-20260927-028: hud builds with C++17 only for its tests

Owner: agent B. This comes from the legacy reconciliation, B-L24 (§4:
broader than needed). hud's +unity1 rebuild raised the whole project from
C++14 to C++17 (`CMakeLists.txt`), while only resolute's googletest needed
C++17, for the tests. The task: restrict C++17 to the tests, or prove that
the library and the service behave the same under C++17. Build on +unity2
(UNITY-20260927-029) as +unity3.

**Outcome: restricted, as +unity3.** hud itself builds with C++14 again,
as 0ubuntu6 did, and `tests/` with C++17.

- Every package's file list is identical to +unity2's.
- The exported dynamic symbols of every ELF file are identical.
- All 6 test suites pass.
- On target2 the LibreOffice window was kept 10 of 10 times, and HUD
  answered 9 of 10 (see Measurements for the one miss).

```yaml
task_id: UNITY-20260927-028
package: hud
target_series: resolute
issue: local - +unity1 set -std=c++17 for the whole project (legacy B-L24)
status: REPRODUCED  # a build-scope finding: +unity2's sbuild log compiles every hud and test unit with -std=c++17
issue_search_result: NOT_FOUND  # our own change; upstream and 26.10 ship 0ubuntu6 with -std=c++14 (UNITY-20260927-029 search)
source_version: 14.10+17.10.20170619-0ubuntu6+unity2 (0e99dca, not yet published) -> +unity3
source_commit: 2f2fa89 (B's local git tree packages/hud; 31fb59c the change); the whole series from archive 0ubuntu6 is in patches/full-series
binary_version: +unity2 and +unity3 built from packages/hud (0e99dca, 2f2fa89); target2 ran +unity3 via dpkg -i
reproduction: the sbuild logs (build/; +unity2's in research/UNITY-20260927-029-hud-libreoffice/build/), counted by the last -std= of each compile command
evidence: logs/01-03, build/
observed: >
  FACT (logs/02): +unity2's build compiles all 78 C++ units of hud and all
  47 of tests/ with -std=c++17 (the 4 googletest/gmock units with
  -std=gnu++17 from googletest's own CMake).
expected: hud compiled as upstream (C++14); only the tests, which include resolute's googletest, with C++17
root_cause: CMakeLists.txt:141 set -std=c++17 for CMAKE_CXX_FLAGS of the whole tree in +unity1
invariant: >
  hud's shipped files, exported symbols and behaviour do not depend on the
  tests' language level
existing_fix_result: NOT_FIXED  # our own change
candidate_approaches:
  - (A) keep C++17 and prove equivalence - not chosen: the machine code of every C++ binary differs (logs/02), so "the same" would need behaviour tests of all of it
  - (B) C++14 for hud, C++17 appended in tests/CMakeLists.txt - chosen
chosen_approach: B
why_chosen: it restores upstream's language level for everything shipped and keeps the tests building (section 4, not wider than needed)
design_challenger_required: false  # build flags, no code change
design_review_result: NOT_REQUIRED
architectural_task: false
correct_layer: the build system (CMakeLists.txt, tests/CMakeLists.txt)
code_risks:
  ownership_lifetime: not_applicable
  callbacks_cancellation: not_applicable
  threading_reentrancy: not_applicable
  ABI_API_file_list: checked  # logs/01: file lists and exported symbols identical
unknowns:
  - the tests (C++17) link objects of common/ and service/ built with
    C++14. 0ubuntu6 did not have that mix: it built everything, tests
    included, with C++14. INFERENCE: sound, because GCC keeps one libstdc++
    ABI across these levels; it concerns only unshipped test binaries, and
    the 6 suites pass
```

## Measurements

- **Compile flags** (logs/02), counting the last `-std=` of every C++
  compile command in the sbuild log:

  | build | hud | tests/ |
  |---|---|---|
  | +unity2 | c++17 (78) | c++17 (47) |
  | +unity3 | **c++14 (78)** | c++17 (47) |

  Plus 4 googletest/gmock units with `-std=gnu++17` from googletest's own
  CMake in both builds. An earlier count said 82 for hud because its regex
  missed `gnu++17` (Verifier finding 2).

- **Packages** (logs/01, `abicompare.py`, +unity2 against +unity3, all 14
  .deb packages; the 5 .ddeb are not compared):
  - every file list is identical;
  - the exported dynamic symbols of the libraries are identical: libhud
    25, libhud-client 67, libhud-gtk 3. The executables export nothing.
    The Verifier also compared every dynamic symbol including imports,
    with versions, and found them identical. libhud-client's 31 C++
    symbols are all hud::client::HudClient (pimpl): no [abi:cxx11] tags, no
    std:: in its headers, and the vtable and typeinfo sizes are unchanged;
  - contents differ in the changelogs and the ELF files.
- **ELF sections** (logs/02):
  - `libhud.so` (C) differs only in its build-id; its code is identical;
  - `libhud-client.so` (it has C++ files), `hud-service` and
    `window-stack-bridge` have different machine code, which is expected
    from a different language level.
- **Tests:** 6 of 6 suites pass in the sbuild (`build/`), including
  UNITY-20260927-029's three window-stack-bridge tests.
- **target2** (logs/03): after a reboot with +unity3, 10 LibreOffice
  Writer starts. The window was in the stack 10 of 10 times, and HUD
  answered 9 of 10.
  - The empty run is the session's first start, with xid 56623243. That
    is the same xid as the one mechanism-2 case in UNITY-20260927-029,
    also a first start, on the archive hud. INFERENCE, not proven: it is
    unrelated to the language level. The case has been seen on the two
    C++14 builds (archive and +unity3) and not on +unity2. In 029, +unity2
    answered 20/20, and 5 of 5 on first starts, where boot 4 was empty 5 s
    later. It stays open for UNITY-20260929-002.

## Result

- **Package:** hud `14.10+17.10.20170619-0ubuntu6+unity3`, on top of
  +unity2 (UNITY-20260927-029); non-native 1.0 (orig + diff.gz); sbuild
  successful (`build/`).
- **Series:** `patches/` has this task's two commits. `patches/full-series/`
  has everything from archive 0ubuntu6 (+unity1, 029's fix, +unity2, this
  change, +unity3). The git tree `packages/hud` exists only on builder
  (~/work/b/unity-distro/packages/hud), and the series rebuilds it: `git
  am` on `dpkg-source -x` of the archive 0ubuntu6.

## Verification: PASS (REVIEWED)

The independent Verifier checked:
- the diff (two flag lines);
- the flags per compile unit in the sbuild log;
- the ABI (all dynamic symbols with versions, libhud-client's C++ class);
- the tests (6/6);
- the source format (non-native 1.0) and the manifest against 2f2fa89.

Its notes are applied above: the unit counts, the 0ubuntu6 statement,
INFERENCE labels, 14 .debs, and the missing card fields.

## Status

See the evidence (`~/coordinator/evidence/UNITY-20260927-028.json`) and
docs/status/B.md.

## Gated rebuild and target test of this build (2026-10-02)

- **Source.** On the GitHub hud repository, branch `b/UNITY-20260927-028`
  = `b/UNITY-20260927-029` (+unity2, ef39a8d) plus `99097d9` (the change)
  and `9e7c093` (the release), pushed. The tree hash (2d9b6dba…) is the one
  of the tested build 2f2fa89.
- **Gated build** on the pinned chroot 20260929T201245Z:
  `build-gated/UNITY-20260927-028-hud-build-manifest.json`, PASS, 6 of 6
  test suites, with the archive's orig tarball (sha256 3cb825f0…).
- **Payload against the tested build** (logs/05): all 14 .debs have the same
  control fields, file lists and exported symbols, and every file inside is
  byte-identical (0 of 83 differ).
- **Target test, mode this_build** (logs/04), on the UNITY-20260927-029
  session of target2 (Clean-2, our repository, gated +unity2): the gated
  +unity3 .debs installed from a file repository, the upgrade path +unity2
  to +unity3; the installed hud .deb is the manifest's (sha256 53519934…).
  After a reboot into the auto-login Unity session, no drop-in, no test
  environment: hud-service c2534c84… and window-stack-bridge 95ab8785… are
  the gated .deb's files, no "(deleted)" mapping; `lo7.sh 20`: 20 of 20
  windows in the stack, the HUD answered 20 of 20, now and after 5 s; no
  warning from either service.
- **Clock:** NTPSynchronized=yes on both phases (see the -029 card and
  UNITY-20260929-022).

## Known gaps before the gate

| gap | state |
|---|---|
| tests (C++17) link objects built with C++14 | closed with a reason: only unshipped test binaries; shipped file lists and symbols identical to +unity2 (logs/01, logs/05); 6 of 6 suites pass on the gated build |
| mechanism 2 (HUD empty with the window known), seen once on a C++14 build | task UNITY-20260929-002; 0 of 20 on this build (logs/04) |
