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
3. The task owner checks only the small, task-local facts needed to identify
   the installed/source package and reproduce the report. Delegate result-heavy
   searches to one or more ephemeral `package-investigator` subagents defined in
   `.claude/agents/package-investigator.md`, split into bounded independent
   scopes: local refs and patch records; other active/closed/deferred work;
   Ubuntu/Debian archive versions; upstream history/releases; and issue
   trackers. Parallelize independent scopes. Ask each worker for concise
   findings with exact versions, commits, links, search scope, and gaps; do not
   pull raw search output into the owner's context. Search exact symptoms and
   signatures, not just the suspected cause. The subagents do not operate the
   VM, change source, own the task, or decide whether implementation may begin.
   If subagents are unavailable, keep the task `BLOCKED` or `UNKNOWN`; do not
   replace a result-heavy sweep with a direct search in the owner's context.
4. Aggregate all investigator reports. The physical task owner sets one exact
   `existing_fix_result` from the process document and cites the version,
   commit, patch, issue, or dated queries behind it. Set
   `issue_search_result` to `FOUND`, `NOT_FOUND`, or `UNKNOWN` based on the
   named trackers searched. A subagent's `NO_MATCH_IN_SCOPE` is not a global
   `NOT_FIXED`. If any required search is incomplete, use `UNKNOWN`; do not
   turn absence of one result into `NOT_FIXED`. `UNKNOWN` blocks package code
   until May authorizes more investigation or defers the task.
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

This skill is the physical task owner's checklist and does not itself launch
workers. The owner launches the temporary investigator for broad searches,
validates its findings, and writes the final evidence card. The subagent does
not acquire persistent task or VM ownership.
