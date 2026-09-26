---
name: bugfix-verification
description: Independently challenge a package patch by testing the reported failure, its root cause, and likely regressions without editing the patch.
---

# Bug-fix verification

Use a reviewer separate from the implementer for a behavior fix or a
non-mechanical build fix. Prefer the other physical builder agent when
available; otherwise use an isolated, read-only subagent. The coordinator
assigns and tracks work but does not substitute for technical review. The
reviewer reads the task's evidence card and diff, but does not accept the
implementer's root-cause claim without checking its evidence. Do not modify the
patch. The owner of an assigned VM alone operates that VM; the reviewer can
challenge the recorded runtime evidence without taking VM ownership.

Try to disprove the result:

1. Confirm the original scenario fails on the unmodified source/package.
2. Confirm the same scenario passes on the patched build.
3. Check a nearby input, lifecycle path, or alternate caller that could still
   trigger the root cause or expose a regression.
4. Check that the patch repairs the recorded invariant at the right layer and
   is no broader than needed.
5. Where applicable, inspect ownership and object lifetime, callbacks and
   cancellation, threading/reentrancy, error paths, and ABI/API/file-list
   effects.
6. Check the focused test, relevant existing tests, clean target-series build,
   and every compatibility/ABI/API/file-list claim made in the record.
7. Separate observed facts from inference and name anything not checked.

Return exactly one verdict:

```text
PASS
FAIL
INCOMPLETE
```

Include concise evidence for the verdict, a counterexample if found, and any
remaining unknowns. `PASS` means the stated reproduction and relevant checks
support the fix; it does not mean untested scenarios are safe. Only `PASS`
advances a behavior fix to `READY_TO_PUBLISH`.
