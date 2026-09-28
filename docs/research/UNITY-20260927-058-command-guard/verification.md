# UNITY-20260927-058: verification record

Verdict by part, 2026-09-28. **E is NOT VERIFIED.** This record does not
claim full adversarial or security coverage of the guard.

| Part | What | Verdict | By |
|---|---|---|---|
| A | New tests fail on the old hook, pass on the new; full suite | PASS | independent Verifier 2 |
| B | Tightening only: legacy floor in `inspect()`; corpus replay | PASS | independent Verifier 2 |
| C | Today's incident as hook input: heredoc closed early by an `EOF` line inside the data, followed by `aptly publish` (plain, `find -exec`, `nice`, `exec`, subshell, `sudo`, `sudo bash -c`) | PASS | independent Verifier 3 |
| D | `-config` family: all four flag forms, `HOME`, `env`, `sudo`, `command`, absolute paths, `..`, `--` | PASS | independent Verifier 3 |
| E | Adversarial search for bypasses across the hook's mechanisms | **NOT VERIFIED** | - |
| F | Documentation examples and the Aptly freeze text | PASS | independent Verifier F (second round) |

Review status: REVIEWED. The C/D cases were partly written by the
implementer (24 of 41); the verifier added 17 of its own.

## Details

- **A.** Against origin/main 03f5cea the new test file gives 122 failures
  and 1 error. Against 02454b8 the full suite passes, 43 tests.
- **B.** `inspect()` applies the pre-058 tokenisation and rules first.
  Replaying the builder's Claude Code transcripts (4566 unique Bash/Monitor
  commands at the time of verification) gives 0 commands that the old hook
  denied and the new one allows, and 88 the other way round
  (`logs/04-corpus.txt`).
- **C, D.** 41 cases, all denied by the new hook. The old hook allows the
  original incident form (rc 0). Case files: `logs/06-cases-cd-implementer.json`
  and `logs/07-cases-cd-verifier.json`.
- **F.** `doc_examples.py` passes every fenced shell block of the process
  documents and skills (7) and 36 forms named in ENGINEERING-PROCESS
  sections 6 and 9 and in the card's Known false positives to the hook. It
  executes nothing. Result: 0 mismatches (`logs/05-doc-examples.txt`). The
  first round was FAIL because 4 documented forms were missing from the
  list; they were added. The Aptly freeze paragraph in section 6 states
  exactly the three decided points. CLAUDE.md is unchanged.
  `scripts/taskctl.py` runs only `aptly publish show`.
- **E: NOT VERIFIED.** Each attempt to write an adversarial test matrix
  was stopped by the environment's safety classifier: three verifier
  subagents, and the implementer's own attempt. On the owner's decision the
  classifier is not worked around and no adversarial cases are generated in
  another form.

## Bounds of what was checked

- 127 must-deny and 43 must-allow cases in `scripts/tests/test_command_guard.py`,
  from the five Design Challenger rounds and the implementation.
- The 41 C/D cases.
- The 36 documented forms and 7 documentation blocks.
- 4566 real commands with no newly allowed command.

**Residual risk.** A command form outside these cases may still reach
aptly's publish, task or api commands through a mechanism of the hook that
no adversarial test exercised. The candidates are the scanner, the heredoc
TEXT/BLOB/SCRIPT classification, `_exposed()`, the reader allow-list and the
command prefixes. This risk is unknown and unmeasured. Full adversarial
testing is UNITY-20260928-002 (backlog).

## Incident during verification

On 2026-09-28 at 06:54:37Z the first verifier subagent ran `aptly publish
list` about 13 times, 3 of them as root. A test-data heredoc was closed
early, and the main-branch hook let the remainder through. Nothing was
published or changed. The files the root calls created were removed on the
owner's decision (evidence JSON, `incident_cleanup`). Every later verifier
ran under the mandatory mode: data only, no heredocs, no sudo, no aptly.
