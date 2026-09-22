# Upstream queue

Contributions that are finished but not yet sent.

May decided on 2026-09-23 to hold off on submitting anything upstream for now.
A first approach to an unfamiliar team is worth doing calmly rather than in
passing. Development is unaffected: packages we fix are published to our own
aptly repository and installed on target, so we get a working system regardless
of what the archive does.

One directory per contribution, named `<package>-<topic>`. Each holds
everything needed at the moment of sending, so nothing has to be reconstructed
from memory:

```
<package>-<topic>/
  README.md      where it goes, to whom, what to re-check first
  bug-report.md  text for the bug tracker
  sru.md         the four SRU sections, when it is an SRU
  evidence/      logs, command output, screenshots - proof of both bug and fix
```

Status of each is tracked in `docs/PATCHES.md`:
`draft` -> `ready` -> `sent` -> `merged` / `rejected`.

## Two standing rules

**Re-verify before sending anything that has been sitting.** The longer a draft
waits, the likelier the ground has moved. Before sending, run the first step of
the checklist again: has a new package version fixed it, has someone filed the
bug meanwhile, has our patch drifted from the tree, does it still reproduce on a
current system? For a fresh submission that check is a formality. For a deferred
one it is the point.

**One at a time.** Three patches in one go are harder to review than three in
sequence, and a first impression forms around the weakest of them. `nux-pcre2`
goes first: it is the best evidenced and the most consequential.

Nothing goes out without May reading the specific text and agreeing to it. See
`../CONTRIBUTING-UPSTREAM.md`.
