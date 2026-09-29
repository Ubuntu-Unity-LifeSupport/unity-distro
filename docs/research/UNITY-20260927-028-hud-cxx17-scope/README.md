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
- On target2, HUD answered for LibreOffice as with +unity2.

```yaml
task_id: UNITY-20260927-028
package: hud
target_series: resolute
issue: local - +unity1 set -std=c++17 for the whole project (legacy B-L24)
status: REPRODUCED  # a build-scope finding: +unity2's sbuild log compiles all 129 C++ units with -std=c++17
issue_search_result: NOT_FOUND  # our own change; upstream and 26.10 ship 0ubuntu6 with -std=c++14 (UNITY-20260927-029 search)
source_version: 14.10+17.10.20170619-0ubuntu6+unity2 (0e99dca, not yet published) -> +unity3
source_commit: 2f2fa89 (B's local git tree packages/hud; 31fb59c the change); the whole series from archive 0ubuntu6 is in patches/full-series
observed: >
  FACT (logs/02): +unity2's build compiles all 82 C++ units of hud and all
  47 of tests/ with -std=c++17.
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
  - the tests (C++17) link objects of common/ and service/ built with C++14
    (the same mix 0ubuntu6's own test build used before googletest needed
    C++17); GCC keeps one libstdc++ ABI across these levels, and the 6
    suites pass
```

## Measurements

- **Compile flags** (logs/02), counting the last `-std=` of every C++
  compile command in the sbuild log:

  | build | hud | tests/ |
  |---|---|---|
  | +unity2 | c++17 (82) | c++17 (47) |
  | +unity3 | **c++14 (82)** | c++17 (47) |

- **Packages** (logs/01, `abicompare.py`, +unity2 against +unity3, all 15
  binary packages):
  - every file list is identical;
  - the exported dynamic symbols of all ELF files are identical: libhud 25,
    libhud-client 67, libhud-gtk 3, and the executables;
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
    which was also a first start on the archive hud. So it is not specific
    to this change; it is a lead for UNITY-20260929-002, pointing to a
    first-start dialog.

## Result

- **Package:** hud `14.10+17.10.20170619-0ubuntu6+unity3`, on top of
  +unity2 (UNITY-20260927-029); non-native 1.0 (orig + diff.gz); sbuild
  successful (`build/`).
- **Series:** `patches/` has this task's two commits. `patches/full-series/`
  has everything from archive 0ubuntu6 (+unity1, 029's fix, +unity2, this
  change, +unity3). The git tree `packages/hud` exists only on builder
  (~/work/b/unity-distro/packages/hud), and the series rebuilds it: `git
  am` on `dpkg-source -x` of the archive 0ubuntu6.

## Status

See the evidence (`~/coordinator/evidence/UNITY-20260927-028.json`) and
docs/status/B.md.
