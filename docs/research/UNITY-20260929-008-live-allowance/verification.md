# UNITY-20260929-008 - independent verification

## Round 1 (2026-09-29, ephemeral Verifier; branch tip d743b73)

Verdict: **FAIL**, `INDEPENDENTLY_REPRODUCED`. Findings: FIX_PARTIAL (F1),
TEST_INVALID (F2).

- F1: the shadow scan could not see the functions shell snapshots actually
  define. They use the form `eval $'name () \n{...}'`, and
  `export BASH_FUNC_...%%=` was not matched either. The Verifier
  reproduced that in bash 5.3.9 a function named `/usr/bin/true` replaces
  the binary, in the eval form too.
- F2: the shadowing test used no real snapshot form.

Checked and holding:

- only the eight exact strings are admitted (list membership);
- plain-shape entries only;
- Monitor, background and a missing tool_name are denied;
- all of C's requirements are met in code, with cross-marker rejection
  tested in both directions;
- `private=False` is used only for the list, which is sha-bound;
- the pinned config sha equals the current file, and the content denylist
  is acceptable given the sha;
- no false positive on the builder's real home;
- tests 22/22 and full suite 156/156;
- the before-log reproduces (1 FAIL, 47 ERROR);
- the corpus rerun over 6863 commands: 0/0;
- docs consistent apart from F1; scope limited.

Remarks: `LD_PRELOAD`-type injection was missing from the stated limit;
`run_in_background is True` was exact; `~/.aptly.conf` is 0664, so the path
denies until L0's `chmod g-w`.

Fixed in 8cde590; see README "Verifier round 1: FAIL
(INDEPENDENTLY_REPRODUCED) - fixed".

## Round 2 (2026-09-29, same Verifier; branch tip 7403106)

Verdict: **PASS** (PATCH_CORRECT), `INDEPENDENTLY_REPRODUCED`.

- F1 is fixed. The new pattern catches every real way bash writes a
  shadowing function, all checked in a probe: the snapshot eval form,
  declare -f output (bash 5.3.9), the name followed by a newline before (),
  function followed by a space or a tab, and eval in double quotes. bash
  rejects quoted or escaped function names, and it refuses to import
  BASH_FUNC_/usr/bin/... from the environment. Indirect definitions in rc
  files (escapes, variables, base64, a sourced file) appear in the snapshot
  under the literal name, and are caught there.
- F2 is fixed: the tests use the real format, a non-aptly function that must
  pass, and the real home.
- No false positives over the 7 snapshots, the user rc/profile files,
  /etc/bash.bashrc, /etc/profile and /etc/profile.d/*.
- The background check denies any run_in_background value other than absent
  or false.
- Tests 23/23, full suite 157/157. The new tests against d743b73: 13
  failures (= logs/05).
- Scope as stated; the section 6 limit wording matches the code.

Missing proof: the live-session proof after C's merge, a precondition of
DONE, not of PASS. Running phase L needs May's separate GO, and C writes the
marker after the L0 record.

Remarks:
- Same-uid limit: the snapshot is sourced after the hook decides. This is
  the documented best-effort limit.
- ~/.aptly.conf is 0664 until L0 runs chmod g-w.
