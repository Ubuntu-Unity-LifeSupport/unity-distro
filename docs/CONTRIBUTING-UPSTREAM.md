# Sending work upstream

Rules for anything that leaves this machine: Launchpad bugs, SRU uploads, merge
requests to `gitlab.com/ubuntu-unity`, mailing list posts.

Nothing goes out without May reading the final text and agreeing. Not the agent
on builder, not the session on the host. Every contribution carries his name and
his signature.

## Why these rules exist

Ubuntu Unity is held up by a handful of volunteers. Between 2025 and 2026 the
open source world turned sharply against AI-assisted contributions, for
arithmetic rather than ideological reasons: the cost of producing a patch fell
to nearly zero while the cost of reviewing one did not, and volunteers pay that
cost.

- curl shut down its bug bounty in early 2026 under a flood of AI reports.
  Confirmed vulnerabilities fell from over 15% to under 5%; roughly one report
  in five during 2025 was pure invention, complete with plausible function names
  and file paths, and reproduced nothing.
- Ghostty moved to zero tolerance in January 2026: drive-by AI patches are
  closed on sight and authors of unverified model output are permanently
  blocked, on a public list offered to other projects.
- Gentoo, NetBSD and QEMU ban AI-generated code outright - on provenance
  grounds, not quality, because an unclear origin makes the DCO impossible to
  sign honestly.
- Debian's August 2026 general resolution, "Responsible Use of Generative AI",
  neither bans nor endorses: responsibility rests with whoever submits.

Across 281 surveyed project policies, 83% permit AI. Of those, 67% require
meaningful human involvement, 49% require disclosure, 43% place responsibility
on a named person. Prohibition is rare; conditions are the norm.

**We will not be rejected for using AI. We will be rejected for what usually
arrives with it:** an unverified bug, a bloated diff, no understanding of the
code, machine-sounding prose, and review work pushed onto the maintainer. All
of that is avoidable.

## 1. Prove the bug before writing any code

The most common and most irritating failure mode is a plausibly described
problem that does not exist. That is what killed curl's bounty programme.

Before touching code:

1. **Reproduce it in a clean environment** - an sbuild chroot, or target on the
   `Clean` snapshot. "It breaks for me" without a clean environment proves
   nothing; it may be our own configuration.
2. **Check whether it is already fixed** - package changelog on Launchpad, the
   upstream git tree, the development series, `-proposed`, the bug tracker.
   This has already saved us once: the nux PCRE2 port had been written six
   months before we arrived and we nearly rewrote it. An hour of searching
   beats a day of work.
3. **Check whether someone already filed it.** Duplicates are their own kind of
   annoyance: several people ask the same model, get the same answer, and file
   the same bug.
4. **Test the exact scenario, not a similar one.** A known bug often has a
   precondition that is easy to miss. This has also caught us: the 26.04 note
   reads "shutdown/logout menu not working *after cancelling*", and testing a
   plain first open produced the wrong conclusion.
5. **Record the evidence**: package version, series, exact steps, expected
   behaviour, actual behaviour, log or screenshot.

If the bug does not hold up after those five steps, **that is a good outcome**.
We saved a maintainer's time rather than spending it.

## 2. Conversation first, code second

A drive-by patch - one arriving with no prior discussion - is the most
frequently rejected form of contribution, and some projects close them
automatically.

File or find the bug, describe the reproduction, give it time to be seen, and
only then offer a patch. For Ubuntu this is structural: an SRU without a
Launchpad bug is impossible. For `gitlab.com/ubuntu-unity`: issue first, then a
merge request referencing it.

The only exception is a trivial one-line typo.

## 3. Keep the diff minimal

One patch, one problem. If the description starts to grow, the patch needs
splitting.

Never include in an outgoing patch:

- incidental refactoring
- reformatting, reindentation or rewrapping of lines the fix does not touch
- renaming things "for clarity"
- **changes to existing tests** - that edits the project's specification rather
  than fixing a bug
- a second or third fix, because you were passing through

Anything found along the way goes into `docs/PATCHES.md` as a separate
candidate. We already have one: `Validator::Validate` returns `Acceptable` from
both branches of its `if` on the Windows path. Real, but it does not travel
with the build unblocking - it would weigh down a first contact and blur the
subject.

## 4. Understand every line

Ghostty's wording is worth adopting verbatim: **if you cannot explain what your
changes do and how they interact with the rest of the system, without AI
assistance, you should not submit them.**

In practice: know why this line and not the one beside it; know what happens to
existing users; understand ABI, API and default-behaviour compatibility;
anticipate edge cases and races. For a mature project, "works in 80% of cases"
means "does not work".

Low-quality submissions that push verification onto the maintainer read as
disrespect, not inexperience. That is close to a direct quote from Ghostty's
policy, and the sentiment is far more widespread than one project.

## 5. Disclosure and sign-off

A wrong sign-off is not a style slip. It is a false legal statement.

- **`Signed-off-by:` is May's alone.** It signs the Developer Certificate of
  Origin, a statement of the right to submit the code. An AI cannot make it and
  it must never be added on an AI's behalf. The Linux kernel states plainly that
  coding assistants must not add `Signed-off-by`.
- AI involvement is marked with a separate trailer. The kernel uses
  `Assisted-by: LLM <model/tool>`, and that spelling is becoming the common
  convention elsewhere.
- Ordinary tools - compiler, git, editor - are never named in trailers. Only AI
  and specialised analysers.
- One honest sentence in the merge request or bug comment saying which part of
  the work was AI-assisted. Not an apology, not an advertisement.

Debian encourages disclosure without requiring it. We disclose anyway: it is
honest, and if it surfaced later the reputational cost would dwarf anything
gained by silence.

## 6. Write like a person

Machine register is recognised instantly and sets the reader against the work
before they reach the code.

Avoid: cheerful openings, thanking someone for their question, emoji in
headings, decorative rules, bold every other line, ten bullets where three do,
explaining to a maintainer what pkg-config is, and self-praise -
"comprehensive", "completely resolves", "this will improve the experience for
all users".

Do: short, specific, numbers. "Fails to build against 0ubuntu12, builds against
0ubuntu13 in 372 s" beats any paragraph of adjectives.

**Answering review comments.** Pasting raw model output into a thread - relay
chat - is a visible red flag: it shows a person acting as a transmitter rather
than taking part. Also: gather replies into one pass rather than pinging the
maintainer per comment; do not lose context and break one thing while fixing
another, which is what blind editing looks like; and never argue with a
rejection or ping for attention. A rejection is accepted quietly, with thanks.

## 7. Commit format (Debian/Ubuntu)

- First line is the summary, under 79 columns, no trailing full stop.
- A blank line after it is mandatory. Without it `git log --oneline`,
  `shortlog` and `rebase` all misbehave.
- The body explains **why**, not how - how is visible in the diff.
- Bug reference in the conventional form: `(LP: #2147013)`.
- For a package changelog, Debian form:
  `* d/p/patch-name.patch: what it does (LP: #NNN)`.
- The patch is self-contained: the description alone should explain what and
  why, with no need to read the surrounding conversation.

## 8. The Ubuntu SRU process

Requirements here are checked literally.

**Entry condition:** the fix must already be in the development series with
status `Fix Released`. Without that an SRU is not considered at all.

**Bug template - four sections, headings in square brackets:**

- `[Impact]` - how the bug affects users, why the fix is worth backporting, and
  how this specific upload addresses it.
- `[Test Plan]` - reproduction steps detailed enough that **someone unfamiliar
  with the package** can follow them. Verification is done only with the package
  from `-proposed`.
- `[Where problems could occur]` - risk analysis. **Never "None" and never
  "Low".** List what actually changes and construct scenarios in which it could
  break. Writing "low risk" is a reliable way to be turned down.
- `[Other Info]` - anything else: deviations from normal procedure, answers to
  questions a reviewer will obviously ask.

**Out of scope for SRU:** security vulnerabilities (Security Team handles those)
and new features requiring a new upstream version (backports).

**After acceptance:** the package lands in `-proposed`; the author or affected
users verify it on a system resembling an ordinary one, set
`verification-done-<series>`, wait a minimum of seven days, and resolve
autopkgtest regressions before it reaches `-updates`.

## 9. Pre-submission checklist

Run the whole list. Any "no" means it does not go out.

```
[ ] Bug reproduced in a clean environment (chroot / Clean snapshot)
[ ] Checked it is not already fixed: changelog, git, devel series, -proposed
[ ] Checked nobody else has filed it
[ ] Tested the exact scenario from the bug description, not a similar one
[ ] Evidence recorded: versions, steps, log or screenshot, before and after
[ ] Diff is minimal: one problem, no refactoring, no reformatting
[ ] Existing tests untouched
[ ] I can explain every line without AI assistance
[ ] Effect on existing users and backward compatibility thought through
[ ] Commit: under 79 columns, blank line, explains why, carries (LP: #NNN)
[ ] Signed-off-by from May only; Assisted-by present
[ ] Prose free of machine register, emoji and self-praise
[ ] For an SRU: all four sections, [Where problems could occur] is not "None"
[ ] May has read the final text and agreed to send it
```

## 10. Never

- Sign `Signed-off-by` as an AI, or as May without his knowledge
- Submit a patch for a bug not reproduced in a clean environment
- Submit a fix without checking it was not already made
- Paste raw model output into a comment
- Attach three screens of "comprehensive analysis" instead of three useful
  paragraphs
- Argue with a maintainer's rejection, or ping them again
- Mix a fix and a cleanup in one patch
- Write "None" under `[Where problems could occur]`
- Send anything outward without showing May first

## Sources

- curl and the bug bounty: https://www.theregister.com/security/2026/01/21/curl_shutters_bug_bounty/
- Ghostty AI policy: https://github.com/ghostty-org/ghostty/blob/main/AI_POLICY.md
- Linux kernel, coding assistants: https://docs.kernel.org/process/coding-assistants.html
- Debian GR, Responsible Use of Generative AI: https://www.debian.org/vote/2026/vote_002
- Fedora AI-assisted contribution policy: https://communityblog.fedoraproject.org/council-policy-proposal-policy-on-ai-assisted-contributions/
- Survey of 281 policies: https://arxiv.org/html/2609.07542v1
- Why AI pull requests get rejected: https://blog.codepipes.com/llms/your-pr-was-rejected.html
- Ubuntu SRU bug template: https://ubuntu.com/project/docs/SRU/reference/bug-template/
- Ubuntu SRU requirements: https://ubuntu.com/project/docs/SRU/reference/requirements/
- The Assisted-by trailer: https://allthingsopen.org/articles/open-source-ai-contributions-assisted-by-git-trailer-standard
