---
name: upstream-contribution
description: Rules and checklist for sending anything out of this project to Launchpad, the Ubuntu SRU process, or gitlab.com/ubuntu-unity. Use whenever preparing a bug report, SRU, merge request, patch description or reply to upstream review - and before claiming a bug is reproduced or already fixed.
---

# Sending work upstream

Full text: `docs/CONTRIBUTING-UPSTREAM.md`. This is the operating summary.

## Hard rules

1. **Nothing goes out without May reading the final text and agreeing.** Every
   contribution carries his name. Neither the builder agent nor the host session
   sends anything outward on its own.
2. **`Signed-off-by:` is May's alone.** It signs the DCO - a legal statement.
   Never add it for an AI, and never add it for May unprompted. Mark AI
   involvement with a separate `Assisted-by: LLM <model>` trailer.
3. **Never write "None" or "Low" under `[Where problems could occur]`.** That
   section is an SRU rejection trigger.

## Rule 0: is it already solved?

Fires before everything else, including before analysis. Search outward:

1. the installed system - `apt-cache policy/showsrc/search`, `dpkg -S`,
   `dpkg -l | grep`, `ldd`, and `Task:` in the metadata (`ubuntu-unity-desktop`
   means it is part of our own flavour)
2. the package's history - `rmadison`, Launchpad changelog, `git log -- <file>`,
   all series including devel and `-proposed`
3. bug trackers, by symptom not by your theory; closed bugs often mean "done but
   never delivered"
4. the web, through the host session, as specific questions

Twenty minutes, then record in `docs/DECISIONS.md` where you looked - found or
not - and carry on. Skip for our own code, typos, formatting, and anything
already searched this session.

Caught us three times in one day. Once the answer was a package already
installed on the machine we were working on, visible in a crash dump we had
dismissed.

## Before writing any code

Five steps, in order. Skipping step 2 or 4 has already cost us twice.

1. Reproduce in a clean environment - sbuild chroot, or target on `Clean`.
2. Check it is not already fixed: package changelog, upstream git, development
   series, `-proposed`, bug tracker. The nux PCRE2 port existed six months
   before we looked.
3. Check nobody already filed it.
4. Test the **exact** scenario from the bug description. "shutdown menu not
   working *after cancelling*" is not "shutdown menu not working".
5. Record evidence: versions, steps, expected, actual, log or screenshot.

A bug that fails to hold up is a good outcome, not a wasted afternoon.

## Deferred drafts

Finished contributions wait in `docs/upstream/<package>-<topic>/` until May is
ready to send them. Before sending one that has been sitting, **re-run step 1
today**: newer package version, someone else's bug, patch drift, still
reproduces. Each directory's `README.md` carries its own re-check list.

Send **one at a time**. A first impression forms around the weakest patch in a
batch.

## Shape of the submission

- Conversation first, patch second. Issue or bug, then the code.
- One patch, one problem. No incidental refactoring, no reformatting, no
  renames, and never touch existing tests. Side findings go to
  `docs/PATCHES.md` as separate candidates.
- You must be able to explain every line without AI help.
- Commit: summary under 79 columns, blank line, body explains *why*,
  `(LP: #NNN)`.

## Tone

Short, specific, numeric. "Fails against 0ubuntu12, builds against 0ubuntu13 in
372 s" beats a paragraph of adjectives.

No cheerful openings, no emoji, no decorative rules, no self-praise
("comprehensive", "completely resolves"), no explaining basics to a maintainer,
no promises on the project's behalf.

Answering review: gather replies into one pass, never paste raw model output,
never argue with a rejection, never ping.

## SRU specifics

Entry condition: the fix must already be `Fix Released` in the development
series.

Four sections, headings in brackets: `[Impact]`, `[Test Plan]`,
`[Where problems could occur]`, `[Other Info]`. The test plan must be followable
by someone who does not know the package. Verification uses the `-proposed`
package only, then `verification-done-<series>`, then a seven-day minimum.

## Checklist

Run `docs/CONTRIBUTING-UPSTREAM.md` section 9 in full before sending anything.
Any "no" stops the submission.
