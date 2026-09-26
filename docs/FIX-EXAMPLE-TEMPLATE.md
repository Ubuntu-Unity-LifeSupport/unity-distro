# Canonical fix example

Use this template for a fix that has passed independent verification and is
useful as a future implementation example. Do not label a merely working patch
canonical.

```markdown
# <Short problem and fix>

## Problem
- Task ID:
- Package and target series:
- Source version / source commit:
- Issue reference:
- Observed behavior:
- Expected behavior:

## Root cause proof
- Reproduction on unmodified package:
- Root cause and source location:
- Evidence:
- Invariant that was violated:
- Ownership/lifetime, callback/cancellation, threading/reentrancy, and ABI/API
  implications checked where relevant:

## Decision
- Chosen approach:
- Why this implementation:
- Why not these alternatives:
- Scope deliberately excluded:

## Patch
- Patch name / commit:
- Files changed:
- Why each change is needed:

## Verification
- Regression test fails before and passes after:
- Relevant existing tests:
- Clean target-series build:
- Independent verifier and result (`PASS` / `FAIL` / `INCOMPLETE`):
- Live target verification:
- ABI/API, file-list, or behavior checks actually performed:

## Release and limits
- Published source / binary version:
- Repository and target verification:
- Known limitations and unverified claims:
- Last rechecked:
```

Use `UNKNOWN` or `NOT_RUN` instead of leaving a field blank. A later package
version can invalidate an example; re-check the source and tests before
reusing it.
