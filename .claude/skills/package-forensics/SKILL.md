---
name: package-forensics
description: Investigate an Ubuntu Unity package issue, prove whether it reproduces, and determine whether a fix already exists before code changes.
---

# Package forensics

Use this before changing package code or claiming that a reported package bug
is present or unfixed. Follow the fixed fields and status values in
[`docs/ENGINEERING-PROCESS.md`](../../../docs/ENGINEERING-PROCESS.md).

For repeated discovery across multiple tasks, search this repository's
`docs/PATCHES.md` index and `docs/research/` before reopening an issue. Do not
create a second manually maintained package-status table.

1. Read the assigned task and confirm its ID and owner on the private task
   board. Record the package, target series, exact source and installed binary
   versions, and the bug's stated scenario.
2. Reproduce that exact scenario on the assigned clean target or clean build
   environment. Record boot identity, commands/steps, expected and observed
   result, and evidence paths. If it does not reproduce, investigate once for
   setup mismatch; then close as `NOT_REPRODUCED` or leave `UNKNOWN` with the
   missing evidence stated.
3. Search installed/source identity, all relevant local refs and patch queues,
   this repository's research/decision/patch records, target-series archive and
   update pockets, newer Ubuntu and Debian, then upstream history/releases and
   bug trackers. Search exact symptoms and signatures, not just the suspected
   cause.
4. Record one exact `existing_fix_result` value from the process document and
   cite the version, commit, patch, issue, or dated queries behind it. Record
   `issue_search_result` as `FOUND`, `NOT_FOUND`, or `UNKNOWN` with the trackers
   searched. If the bounded search is incomplete, use `UNKNOWN`; do not turn
   absence of a result into `NOT_FIXED`. `UNKNOWN` blocks package code until
   May authorizes more investigation or defers the task.
5. If a newer release may contain the fix, record the relevant commits and
   measure its build and dependency cost in the target-series chroot before
   selecting it over a backport. Record why the selected solution preserves
   the invariant and why plausible alternatives were rejected.
6. Save the evidence card at `docs/research/<task-id>-<topic>/README.md`. Move
   the task to `READY_FOR_FIX` only when reproduction, root-cause evidence,
   invariant, existing-fix result, and approach decision are present.

Do not edit package source in this skill's investigation stage. A successful
investigation may end with `ALREADY_FIXED`, `NOT_REPRODUCED`, `DEFERRED`, or
`UNKNOWN`; all are valid findings when recorded accurately.
