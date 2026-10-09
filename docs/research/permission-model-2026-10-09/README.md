# Permission model, phase 0 - the review of 2026-10-09 and May's decisions

Kind: `infra` (documentation only). Phase 0 of the permission-model change. The review below was made read-only on main 96122ab. May's decisions of 2026-10-09 follow it and take precedence where the review offered options (its sections 4.3, 4.4 and 7); the review's findings and recommendations are the review's own.

## May's decisions (2026-10-09)

**Decision (May, 2026-10-09).**

1. The architecture is accepted as a whole: the phased rollout, the
   independent Verifier, routine publication automated through C, and a
   separate signer. The guard is not weakened until the signer is ready and
   integrated.
2. Publication run: the task owner runs `scripts/publish_aptly.py` in the
   task worktree on C's GO. C checks all gates, issues the authorization,
   supervises the run and writes the final record. May's separate
   confirmation of each ordinary release is not required. The authorization
   is bound to the specific task, branch, commit, gate and publication
   artifacts.
3. Guard relaxation comes after phase 5, when the signer is deployed,
   integrated and verified. Until then the current confirmed prohibitions
   stay; only necessary defects are fixed, without widening allowed actions.
4. Routine policy, initial conservative configuration: one already-known
   source package; at most 40 binary records; no new or changed maintainer
   scripts relative to the approved version; at most one automatic
   signature per 10 minutes; at most six automatic signatures per day. The
   signer must verify the exact composition, versions, architectures,
   checksums and provenance of the artifacts. On any mismatch, on anything
   it cannot verify, or outside the policy limits: no automatic signature
   and a separate review. New packages are not routine merely because they
   fit the numeric limits.
5. Rollback is an exceptional operation: C prepares the plan, the Verifier
   checks the expected result, then May's separate GO is required. The
   automatic rollback policy is not extended in this rollout.
6. GitHub: `main` gets protection against force-push and deletion; builder
   uses a fine-grained token without admin rights, with the minimal rights
   the normal workflow needs. Before rollout, compatibility with all
   existing operations is checked and a clear path to restore access is
   kept.
7. May keeps: the first live migration, key rotation, changes to
   `policy.json` and to the global `~/.claude/settings.json`. An Upstream
   Liaison is wanted as a specialised role for research, patch preparation
   and message drafts; external sends remain under the current approval
   policy.
8. UNITY-20260929-019 is unblocked and implementation continues per the
   approved phases: development, testing and deployment preparation are
   allowed; the separate GO for the first live migration, key
   generation/rotation and the other actions reserved above stays.

General rules May set: work in phases with separate tasks, tests,
independent verification and rollback; never combine the false-positive
fixes, the permission-policy change and the signer integration into one
inseparable change; show the diff before any global-settings change; after
a protection change, prove it works in new sessions. The goal is the
coordinator's autonomy for routine publication, with May's control over
exceptional operations and trust-boundary changes.


## Phase order (architecture session, under decision 3)

0 (this record) -> 1 (UNITY-20260929-003) and 4 (publication authority) -> 3 (permissions block) -> 5 (signer) -> 2 (guard narrowing) -> 6 (cleanup). Each phase is its own task with tests, independent verification, a rollback and a fresh-session proof.

## The review as delivered (2026-10-09 01:55Z)

### unity-distro: permission and publication architecture review

Date: 2026-10-09 (UTC). Read-only review. Nothing in the repository, the settings, the system or the live aptly state was changed. The only commands run were reads, hashes, `gh api` GET calls and the existing unit-test suite.

#### 0. What was inspected, and what could not be

**Authoritative checkout.** `/home/claude/unity-distro`, branch `main`, HEAD `96122abd0f32d5ec5d92a3327067462853c7d160`, working tree clean apart from `__pycache__`. 44 further worktrees under `~/work/{a,b,docs-maint}` carry task branches; 13 of them hold older copies of `command_guard.py` (four distinct hashes). Those copies are inert: the installed hook handler names the base checkout by absolute path.

**Live files and the frozen baseline agree.** The sha256 of `~/.claude/settings.json`, `~/unity-distro/.claude/settings.json`, `command_guard.py`, `install_command_guard.py`, `safe_git.py` and `taskctl.py` equal `~/coordinator/permission-freeze/baseline-20261009/SHA256SUMS`.

**Tests.** `python3 -m unittest discover -s scripts/tests` on main 96122ab: 417 tests, OK, 1 skipped (the live-allowance test skips because `/usr/bin/aptly` exists but the live list file is absent). Runtime 164 s.

**Settings.** The user file `~/.claude/settings.json` contains theme flags and exactly one `PreToolUse` hook (`Bash|Monitor`) with the fail-closed wrapper. There is no `permissions` block anywhere, no `settings.local.json`, and `~/.claude.json` lists one project only: `/home/claude`, with `allowedTools: []`. The sessions A, B and C run as `ccd-cli 2.1.284` with `--permission-prompt-tool stdio` (prompts go to the desktop app); the CLI on PATH is 2.1.278.

**OS.** User `claude` has `(ALL) NOPASSWD: ALL` (`/etc/sudoers.d/99-claude-nopasswd`) and is in groups `sudo`, `adm`, `lxd`, `sbuild`. `/srv/aptly` is owned by `claude`. The only secret key in `~/.gnupg` is the archive signing key `7BF3F77FC27B152C`. nginx serves `/srv/aptly/public` read-only on 192.168.56.10:8080. A GitHub token with `admin` on `Ubuntu-Unity-LifeSupport/unity-distro` and an ssh key are on the machine; `main` has no branch protection and no rulesets.

**Signer.** The signer code (`signer/`, `scripts/signer_client.py`, `scripts/gpg_standin.py`) is merged into main (UNITY-20260929-021 DONE). It is not deployed: `~/.config/aptly-signer/` does not exist, `publish_aptly.py` still runs `aptly publish switch` with the local gpg key, and the integration task UNITY-20260929-024 is BACKLOG. UNITY-20260929-019 is BLOCKED on May's "who writes it" question, with May's option-2 decision (move the key out of `claude`'s reach) recorded.

**Not accessible from here (reported as unavailable, not inferred):** the permission mode the three sessions run in; whether a signer VM exists on the host; the vbox MCP server configuration on the host; GitHub organisation settings beyond the repository; the content of May's chat confirmations (only their records in `PENDING-MAY.md` and `AGENTS-LOG.md`).

**Claude Code facts used below** were checked against the official documentation by a read-only subagent: permission rules are evaluated deny, then ask, then allow; Bash rules match after compound commands are split and wrappers (`timeout`, `nice`, `env` assignments, ...) are stripped, but not full paths or `bash -c`; the documentation states that permission rules are not a security boundary; deny rules apply in every mode including `bypassPermissions`; subagents inherit settings hooks and permission rules; a hook timeout does not block the call (which is why the wrapper carries its own inner `timeout`); a hook may return `permissionDecision: allow|deny|ask|defer` on stdout; `disableAllHooks` in project settings overrides user settings; the Linux sandbox (bubblewrap) exists but is explicitly "not a security guarantee". Whether `ask` decisions are honoured in the mode the sessions use is not documented and must be proven in a fresh session.

### 1. Current-state security model and trust boundaries

### 1.1 One trust domain

Everything that acts on builder runs as uid 1000 `claude`: coordinator C, agents A and B, every subagent, the hook, the guard, `taskctl.py`, the registry, the publish records, the backups, the gpg key, the GitHub token, the ssh key to the targets (which have passwordless sudo). With `NOPASSWD: ALL` that domain also includes root. Consequences that the project's own records already state, and that this review confirms:

- `--actor A|B|C` in `taskctl.py` is a label (TWO-AGENTS.md says so). The registry is self-declared.
- The rehearsal and live markers bind to a `session_id`, but any session can write a marker. They are C's intent record, not authentication.
- The "write-once" publish record is `chmod` read-only by its owner, who can change it back.
- `~/.claude/settings.json` can be edited by any session; `disableAllHooks` would switch the guard off. `install_command_guard.py --check` detects that; nothing prevents it.
- The guard is, in its own words, "a narrow Bash command-pattern safety net; not a shell security boundary". Verification part E of UNITY-20260927-058 (adversarial search) is NOT VERIFIED, and UNITY-20260929-018 was merged as FIX_PARTIAL with May's decision that the remainder is closed by an OS or key boundary, not by the guard.

A subagent is not a boundary either: it inherits the hooks and rules of the parent, runs as the same user, and can be given any prompt by the agent that spawns it. The `adversarial-verifier` and `design-challenger` roles are quality controls (fresh context, no implementation stake), which is what the process needs from them, and nothing more.

### 1.2 The boundaries that are real

Only controls that live outside uid `claude` can stop an agent that is wrong rather than merely careless:

| Boundary | Where it lives | Status |
|---|---|---|
| May's decision on a channel agents cannot drive | the desktop app, the signer console (planned) | in use for every publication today (chat confirmation) |
| vbox MCP server `allowed_vms` / `never_allowed` | May's Windows host | in place for builder-server; signer VM not yet listed |
| Signing key held by a separate machine | signer VM (UNITY-20260929-019 option 2) | designed, coded, not deployed |
| GitHub server-side rules | github.com | none configured on `main` |
| apt on consumer machines trusting only the archive key | the targets and any future consumer | depends on the key boundary above |

Everything else (guard, gates, manifests, records, markers) is traceability and accident prevention. The owner's requirement document accepts exactly this: "address concrete risks with proportionate controls", "do not introduce separate OS users".

### 1.3 How a publication is authorised today

From ENGINEERING-PROCESS section 6 step 10, `PENDING-MAY.md` and `AGENTS-LOG.md`: owner finishes evidence, creates the gate last, moves the task to `READY_TO_PUBLISH`; C checks the gate; **May confirms in the owner's chat session**; the owner runs `scripts/publish_aptly.py --gate`. The script checks provenance, hashes, snapshot content and version safety and refuses on any mismatch, but it has no notion of authorisation: nothing in it reads May's or C's confirmation. The confirmation is a process rule, enforced by the agent asking. Between 2026-10-08 11:04Z and 2026-10-09 01:34Z May confirmed nine publications this way (-001, -012, -011, -015, -016, -053, -013, -020, -024). That is the interruption to remove.

### 2. Restriction-by-restriction classification

Legend: **INCIDENT** = supported by a documented real incident; **PREVENTIVE** = deliberate control without an incident; **UNJUSTIFIED** = insufficiently justified or undocumented; **FP** = known false positive; **HEURISTIC-MISPLACED** = a workflow rule that should not be a shell-text heuristic. Evidence pointers are files in the repository or `~/coordinator`.

| # | Restriction (where) | Class | Evidence | Verdict |
|---|---|---|---|---|
| 1 | Fail-closed hook wrapper: inner `timeout -s KILL 20`, `python3 -I`, stdout discarded, any rc other than 0 becomes exit 2 (`~/.claude/settings.json`, `install_command_guard.py`) | INCIDENT | hook not loaded in sessions rooted at `/home/claude` until 2026-09-29, so the 2026-09-28 rehearsal ran unguarded (APTLY-FREEZE.md, UNITY-20260928-012); Claude Code lets a timed-out hook through (docs) | keep unchanged |
| 2 | Guard denies parse failures ("could not parse shell quoting") | INCIDENT for the fail-closed stance; FP for the trigger | 13 of 44 corpus refusals (RC1) plus C's repeated cases are quoted-delimiter heredocs with an apostrophe or backtick in the body (UNITY-20260929-003 README, evidence `additional_cases`) | keep fail-closed; fix the legacy floor so bodies are not lexed as shell (-003 RC1, already designed) |
| 3 | `aptly publish` in any literal form, `task`, `api`, flags before the command word, wrappers, nested shells (rule E, legacy rule) | INCIDENT | 2026-09-28 06:54Z: a verifier's heredoc closed early and bash ran `aptly publish list` ~13 times, 3 as root (DECISIONS 2026-09-28, UNITY-20260927-058 verification.md); the `-config` bypass found in -047 | keep |
| 4 | Words `publish`/`task`/`api` anywhere in a command that has **any expansion**, even with no aptly occurrence (rule A, -058 round 3) | FP, PREVENTIVE against a theoretical form | closes `${a}ly publish`, `$(printf apt)ly publish`; no incident of such a form; 6 of the 9 new false positives are `api` in GitLab/GitHub URLs or `publish` as a JSON key next to a `$var` (evidence -003 `additional_cases` 1, 2, 4, 5, 6, 8) | narrow: trigger only when the expansion is in the command-word position of a non-reader group (section 3.2) |
| 5 | Any mention of aptly in a non-reader command: `python3 -c` strings, `ssh host '...'`, `timeout`, `xargs` (rule R) | FP (RC2, RC7), accepted in -058 | 10 corpus refusals are `python3 -c` data strings; case 3 of the new evidence is a read-only `os.walk('/srv/'+'aptly'+'/pool')` | narrow for interpreter code strings (section 3.2); keep for wrappers |
| 6 | `/srv/aptly` exemption only when the token is exactly the directory (rule R, RC5) | FP | `--root=/srv/aptly`, `s|x|/srv/aptly|` denied (corpus record 30) | fix as designed in -003 |
| 7 | `sed` is a reader only for `p/d/=` scripts (RC4) | FP | 2 corpus refusals | fix as designed in -003 |
| 8 | `git commit -F -` heredoc body classed SCRIPT (RC1b) | FP | 3 corpus refusals | fix as designed in -003 |
| 9 | Copy or link of the aptly binary (rule C) | PREVENTIVE | -058 design, no incident; rarely fires | keep |
| 10 | Heredoc TEXT only when nothing can run it (-018) | INCIDENT (a false negative found by the Design Challenger; proven with `inspect()`) | -018 README, 23 data cases | keep |
| 11 | Rehearsal allowance: `/usr/bin/aptly -config=/var/tmp/aptly-rehearsal/... publish ...` with C's dated marker, strict config, logged | PREVENTIVE, used | 21 logged commands in -047 R and -021 rehearsals | keep (needed for the signer rehearsal and cut-over) |
| 12 | Live allowance: exact strings of `live-commands.json` with C's live marker | PREVENTIVE, used once | 7 logged commands, phase L of -047; the list was deleted at DONE, so the prefix is now always denied | retire after the signer is live (dead code and 150 lines of process text) |
| 13 | `git push --force`, `--force-with-lease`, `+refspec` | PREVENTIVE, documented rule | CLAUDE.md "Do not rewrite history"; `safe_git.py push` only pushes the current branch to its own ref | keep; add GitHub branch protection as the server-side belt |
| 14 | `git add -A`, `--all`, `.`, `docs`, `docs/` | INCIDENT-adjacent | two content leaks to the public repository (2026-09-25 conversation record, COORDINATOR.md; 2026-10-03 lock-bypass recipe, PENDING-MAY.md) were not caused by broad staging, but the rule exists to make content review per file possible; 46 real commands in the -058 corpus hit it | keep |
| 15 | `rm -rf` with a glob or an unguarded variable | INCIDENT | May rejected such commands twice on 2026-09-26 (memory `feedback-rm-rf-vars`) | keep |
| 16 | `pkill -f`, `pgrep -f` | INCIDENT | self-kill over ssh at least three times on 2026-09-25 (memory `feedback-pgrep-f-self-match`); all 7 corpus hits are the installer's probe | keep (reliability, not security) |
| 17 | `xwd` | HEURISTIC-MISPLACED but harmless | DECISIONS: xwd misses the wallpaper under Compiz and "invents bugs"; a measurement-quality rule | keep as is (zero cost); it is not a security control and must not be described as one |
| 18 | `Monitor` matched like `Bash` | PREVENTIVE | -058 round 4 | keep |
| 19 | Only `publish_aptly.py` publishes; it accepts no aptly arguments; gate pinned by sha256; switch-time apt view; write-once record | PREVENTIVE, incident-informed | the gate/hash discipline caught a card edited after the gate (memory `feedback-gate-last-commit`) | keep |
| 20 | `taskctl.py` is the only board writer; `--actor` label; evidence fields; `released_in`/`published_by` with raw-object history walk | PREVENTIVE | -019 Verifier rounds 2-3 found git-config execution paths, hardened | keep; it is workflow integrity, not identity |
| 21 | `append_record.py`, `agent_registry.py` under flock | PREVENTIVE | concurrent-edit losses in the two-agent era (TWO-AGENTS.md) | keep |
| 22 | Aptly freeze policy (section 6): only May declares/lifts; no `aptly publish show/list` by agents | INCIDENT | 2026-09-28 incident | keep the policy; note the stale statement "freeze #1 OPEN" in `HANDOVER-C.md` (APTLY-FREEZE.md records the lift at 2026-09-29 14:53Z) |
| 23 | May confirms every publication in the owner's session | PREVENTIVE (process only, not tool-enforced) | nine confirmations in 15 hours on 2026-10-08/09 | replace for routine publications (section 4.3) |
| 24 | "Nothing leaves this machine without May reading it" (upstream, Launchpad, trackers, replies) | PREVENTIVE, documented, owner reaffirms it | CONTRIBUTING-UPSTREAM.md, COORDINATOR.md | keep; make it an `ask` rule for the few external-write command forms (section 4.2) |
| 25 | Security material not pushed before the fix (rule S) | INCIDENT | 2026-10-03 push of a/UNITY-20260927-053 | keep as process; optional pre-push grep tool later |
| 26 | Design Challenger APPROVE before code; Verifier PASS before the gate; no self-merge of task branches | PREVENTIVE, incident-informed | memory `feedback-no-code-before-dc-approve`, `feedback-no-task-branch-merge` | keep |
| 27 | `NOPASSWD: ALL` for `claude`; `lxd` group (root-equivalent) | UNJUSTIFIED beyond convenience, acknowledged (UNITY-20260928-001 BACKLOG) | -019 inventory lists the real root uses (unshare chroots, gdb, apt, nginx) | accept per the owner's instruction; move the asset that matters (the key) instead |
| 28 | Signing key readable by every agent | risk, decided | -019: May chose option 2 | implement (section 4.4) |
| 29 | GitHub `main` unprotected; token with admin on builder | UNJUSTIFIED (never discussed in the records) | `gh api` 404 "Branch not protected", rulesets `[]` | decision for May (section 7) |

Facts versus inference: every "INCIDENT" entry points to a record in the tree or in `~/coordinator`. The classification of #14 as "incident-adjacent" is my inference; the records show the leaks were content decisions, not staging mistakes.

### 3. False-positive evidence

### 3.1 The corpus

Two bodies of evidence exist, both collected without executing anything:

- **UNITY-20260929-003 corpus** (2026-09-29, `~/work/b/unity-distro-003/.../corpus/denials-classified.json`): 44 refusals from the transcripts; 10 true positives (7 `pgrep -f` probes, 1 `git add -A`, 2 `aptly publish list` through another path), 3 collector artefacts, **31 false positives**.
- **`additional_cases`** in `~/coordinator/evidence/UNITY-20260929-003.json` (2026-10-08/09): 9 entries, all false positives, all from publication or research work of the last two days.

### 3.2 Which failures come from which mechanism

| Mechanism | Cases | Fix type |
|---|---|---|
| **A. Legacy floor lexes heredoc bodies as shell** (`_legacy_groups` runs shlex on the whole text before the heredoc-aware scanner). An apostrophe in a quoted-delimiter body is "No closing quotation" and the call is refused as unparsable. | 13 corpus (RC1) + C's recurring cases | narrow: apply the floor line by line with a lexing fallback, as designed in -003 step 1. The invariant holds (every denial the old floor made on a line is kept). No weakening. |
| **B. Word rule with "any expansion"** (`_aptly_rules`: `reach_expansion` is true when any exposed level has `$`, a glob or a brace, and the word `publish`/`task`/`api` appears anywhere). | 6 of the 9 new cases: `gitlab.com/api/v4/...$p`, `api.github.com/...`, `g['publish']` with `$C`, `d.get('publish',{})` with `$f`, `publish hud` in an echo with `$(date)` | different mechanism: the rule exists to catch a command word built by expansion (`${a}ly publish`). Restrict the trigger to that: an expansion, substitution, glob or brace **in the command-word token** of a non-reader group. Argument expansions (`"$url/api/v4"`) no longer count. This is a precise statement of -058 round 3's threat and removes the whole URL/JSON-key class. Two forms become allowed that are denied today (`p=publish; curl "$p"`-like data with no aptly at all) and none of them can reach aptly. |
| **C. Interpreter code strings are runners** (`python3 -c CODE`, `python3 - <<EOF`): every string literal inside CODE counts as an aptly mention or a denied word. | 10 corpus (RC2) + new case 3 (`'/srv/'+'aptly'+'/pool'`) + new case 6 | different mechanism: treat the code string of `python3|perl|ruby|node -c` like a heredoc BLOB. Its words count only when `_STARTS_PROCESS` matches (`subprocess`, `os.system`, `exec(`, `eval(`, `__import__`, backticks in perl/ruby/php ...). The must-deny `python3 -c "import os; os.system('aptly ... publish')"` stays denied. This is the RC2 proposal that -003 deferred as "a separate decision"; with the signer as the boundary it is the right trade. |
| **D. `/srv/aptly` only as a whole token** | 1 corpus (RC5) | narrow (-003 step 4). |
| **E. `sed` substitutions, `git commit -F -` bodies** | 5 corpus (RC4, RC1b) | narrow (-003 steps 2-3). |
| **F. Opaque remotes and wrappers** (`ssh target 'command -v aptly'`, `timeout 60 aptly repo list`, `apt-get source aptly`) | 1 corpus (RC7), listed as accepted in -058 | leave as is; the workaround (run aptly directly, `dpkg-query` instead of `dpkg -L`) is cheap and documented. |

After A, B, C, D and E the remaining known false positives are class F plus "aptly and publish in one `git commit -m` string" (the heredoc commit form is the documented alternative). The `denials.py` collector and the `inspect()` replay used in -003 and -018 are the measurement tools; they must be rerun after each change (section 6).

### 3.3 What no guard change should try to fix

The key-splitting workaround C recorded (`'pub' + 'lish'` in a scratchpad script) and the "write it with the Edit tool instead" habit are symptoms of a rule that judges data as code. The right answer is B and C above, not a longer reader list. The -058 README already says that every list of what *runs* a string is open-ended; the same is true of every list of what *does not*. After this change the guard keeps judging only two things about aptly: literal invocations (rule E) and text that can reach a runner whose command word is literal or unknown.

### 4. Recommended target architecture

### 4.1 Principle

Put the decision "may this content be published under the archive key" where it cannot be forged from builder: the signer. Define *routine* deterministically there. Then May is needed only for what the signer's policy refuses, and the shell guard can be reduced to accident prevention with literal matching, because bypassing it no longer yields a trusted publication. Nothing in this design adds an OS user, removes `NOPASSWD`, or introduces a sandbox.

Layers, from outermost to innermost:

```
L4  May: signer console (exceptional publications, policy, key), desktop-app prompts (ASK), GitHub settings
L3  Signer VM: key, deterministic routine policy, re-sign cadence, console log       <- the boundary
L2  Builder tools: publish_aptly.py (+ signer client, + C's GO record), taskctl.py, create_release_gate.py, safe_git.py
L1  Claude Code permissions block (allow / ask / deny) in ~/.claude/settings.json      <- fewer prompts, ASK for trusted files
L0  PreToolUse guard (command_guard.py): literal destructive forms, fail closed       <- accident prevention
```

### 4.2 Permission model for routine work (ALLOW / ASK / DENY)

Where a behaviour depends on the sessions' permission mode (unknown, see section 0), it is marked *verify*.

| Operation class | Mechanism | Behaviour |
|---|---|---|
| Read-only shell: `git status/log/diff/show/ls-files/rev-parse`, `ls`, `cat`, `grep`, `find`, `stat`, `sha256sum`, `dpkg-query`, `apt-cache`, `curl`/`wget` GET, `ssh target*` reads, `python3 scripts/{taskctl,apt_view,version_safety,agent_registry,append_record,peer_inbox,create_release_gate,backup_aptly_db,alerts}.py` | `permissions.allow` prefixes in `~/.claude/settings.json`, generated and checked by `install_command_guard.py` so the block is reproducible; guard stays silent | ALLOW, no prompt (*verify*: if the sessions already run without prompts, this changes nothing and costs nothing) |
| Normal task work: builds via `build_sbuild.py`, `tmux`, `sbuild`, `gbp`, `quilt`, `scp`, VM operations through the vbox MCP server, `aptly repo/snapshot/...` literal reads and the step-4 `repo add`/`snapshot create` | guard rule E unchanged; MCP ACL on the host unchanged | ALLOW |
| Words `aptly`, `publish`, `task`, `api` in data: URLs, JSON keys, log lines, commit messages, Python string literals that start no process | guard narrowed (section 3.2 B, C) | ALLOW |
| `aptly publish/task/api` literal, under any flag, wrapper, nested shell or copy; a non-literal command word together with those words | guard (fail closed) plus a `permissions.deny` belt `Bash(aptly publish *)`, `Bash(aptly task *)`, `Bash(aptly api *)` (deny rules hold in every mode) | DENY |
| `git push --force*`, `+refspec`, `git add -A/--all/./docs`, `rm -rf` with glob or unguarded variable, `pkill -f`/`pgrep -f`, `xwd` | guard unchanged; GitHub branch protection on `main` (server side) as the belt for force pushes and deletion | DENY |
| Changes to trusted state: `~/.claude/settings.json`, `.claude/**` (hooks, agents, skills, settings), `scripts/{publish_aptly,taskctl,safe_git,install_command_guard,create_release_gate,signer_client,gpg_standin}.py`, `signer/**`, `docs/ENGINEERING-PROCESS.md`, `/etc/sudoers*`, `~/.gnupg/**`, `~/.config/aptly-signer/**` | `permissions.ask` rules for `Edit`/`Write` on those paths; one narrow guard rule that denies shell writes into them (`>`/`>>`/`tee`/`cp`/`mv`/`sed -i` with such a target) with the message "use Edit"; `Bash(sudo visudo*)`, `Bash(sudo tee /etc/sudoers*)`, `Bash(sudo usermod*)`, `Bash(gpg --import*|--delete*|--gen*|--export-secret*)` as ask rules | ASK (*verify* that ask prompts reach the desktop app in the sessions' mode; if they do not, fall back to guard JSON `permissionDecision: "ask"` for the same set, which needs the wrapper to pass stdout through when the guard exits 0 with a JSON body) |
| External writes: `gh issue/pr/release/repo ... create|edit|comment`, `gh api` with `-X`/`--method` other than GET, `git push` to any remote other than `origin`, `git remote add`, `curl -X POST|PUT|PATCH|DELETE`, Launchpad/`bzr`/`dput`/`debsign` uploads, mail | `permissions.ask` rules; process rule unchanged (May reads the text first) | ASK |
| Publication through `scripts/publish_aptly.py --gate ...` | ALLOW at Claude Code level; authority comes from C's GO record (L2) and the signer's policy (L3), section 4.3 | ALLOW |
| Exceptional publication (first publication of a source package, removal, downgrade, policy limit exceeded), key rotation, trust-policy change, first live migration to the signer | signer console only | May, explicitly |

What is deliberately **not** in the model: per-role permission differences. A, B and C share the OS user, the home directory and the one effective settings file (`/home/claude/.claude/settings.json` is both the user settings and, because the sessions' project root is `/home/claude`, the project settings). Role authority stays where it is today: in `taskctl.py` (actor/owner checks) and in C being the only writer of approvals and the only merger of `main`. That is workflow integrity, and the owner's requirements accept that it is not a security boundary.

### 4.3 Routine publication authority

**Roles.**

- The task owner (A or B) builds, gets the Verifier verdict, creates the gate last, moves to `READY_TO_PUBLISH`, and asks C for the slot, as today.
- **C** checks the gate (as today) and then **records the GO**: `python3 scripts/taskctl.py approve-publication UNITY-... --actor C --gate-sha256 ...`. The new subcommand refuses unless the board state is `READY_TO_PUBLISH`, the gate at that sha256 is pushed, no other approval is open, and the task is not marked exceptional. It writes `~/coordinator/publication-approvals/<task>.json` (task, gate sha256, snapshot, approved_by `C`, session id, `not_after` = 4 h, the list of known gaps from the slot request, and `authorized_by: May` with a reference when May's decision was needed).
- **`publish_aptly.py`** requires that file: gate sha256 equal, window valid, snapshot equal; it copies its sha256 into the publish record and deletes it after the switch (single use). Without it the script refuses before touching aptly. `taskctl.py` `PUBLISHED` requires the approval sha256 in the record.
- **May** is no longer asked per publication. He is asked by the signer console when the signer's routine policy refuses, and by the ASK layer for trusted-state changes.

**Who runs the switch.** Recommendation: the task owner, in the task worktree, as today. The gate, manifests and `source_repo` already live there, and `publish_aptly.py` resolves its repository from its own location. C "owns" the workflow by being the only approver, the only merger and the reader of every gate. The alternative (C executes from its own worktree of the task branch) would make C run a `scripts/publish_aptly.py` taken from the task branch, which the branch can modify; it is possible but needs an extra check (`git diff main -- scripts/ signer/` must be empty), and it moves the gate's repository-root logic. May decides (section 7, decision 2).

**Review depth.**

- *Established package, routine update*: Verifier `PASS` with `REVIEWED` is enough when the earlier evidence applies (the practice of the last week: most PASS verdicts were `REVIEWED`); C reads the card; C's GO; signer auto-signs.
- *New source package or first publication*: Design Challenger round on packaging and the existing-fix gate; Verifier `INDEPENDENTLY_REPRODUCED`; C reads the card and the gate; the signer policy classifies it as exceptional by construction (a source name absent from last-live), so May approves on the console. libcolumbus +unity1 (2026-10-09) is the model.
- Mandatory for both and never skipped: artifact hashes and provenance (`create_release_gate.py`, `publish_aptly.py`), the snapshot content check, version safety `SAFE` at gate and switch time, the target verification record, the write-once publish record.

**Independence of the Verifier.** Unchanged: it runs as an ephemeral subagent with `permissionMode: plan` and no write tools, spawned by the owner, and C refuses a gate whose verification record is missing or `INCOMPLETE`. It is not a security control (section 1.1); it is the quality control the process needs.

### 4.4 Signer: deterministic routine policy

The -019/-021 design stands: two-phase signing (proposal with index set and new `.deb` bytes; switch through the gpg stand-in; refresh of the trio; `/live` confirmation), Release built from the signer's template, `Valid-Until` = Date + 3 days, cadence re-sign only for the unchanged last-live set, single-use approvals bound to their base, refusal tests per field. One addition is needed for the owner's goal: **the signer signs a proposal without May when a deterministic policy says it is routine.** Everything else goes to the console as designed.

`policy.json` on the signer (a change to it is a trust-policy change: May only):

```
distribution: resolute, component: main, prefix: .
routine if ALL hold against last-live:
  - no record removed (a replacement of the same package name counts as replaced, not removed)
  - every added or replaced source package name already exists in last-live
  - for each such source, the new version is strictly greater (Debian ordering, apt_pkg.version_compare)
  - every added binary's Source field names one of those sources at that version
  - at most 1 source package and at most 40 binary records change
  - no added binary carries a maintainer script where the previous version of that binary had none
  - the proposal's task_id is UNITY-YYYYMMDD-NNN and differs from the last N task ids
  - at least 10 minutes since the last auto-signed set; at most 6 auto-signed sets per UTC day
console (May) otherwise, and always for: a new source name, a removal, a downgrade,
  a Release field difference, limits exceeded, policy edits, key operations, rollback (see decision 5)
```

Every auto-signed set is logged on the console with the same diff May would have seen, so he reviews after the fact instead of before. The maintainer-script and count rules are proposals; May sets the numbers (section 7).

**Trust limit, stated plainly.** The signer cannot tell C's GO from a forged one, because both come from uid `claude`. The routine policy therefore depends on *content*, not on who asked. An agent that builds a bad version of an established package and walks it through the gates can get it signed automatically. What bounds that today: the package goes only to the two test desktops (per -019, consumers the agents already control), the `Valid-Until` of 3 days, the backups and publish records, and the console log. That is the residual risk the owner's model accepts (section 7, risk 1).

### 4.5 Upstream Liaison subagent

A `.claude/agents/upstream-liaison.md` with `tools: Read, Grep, Glob, Bash, WebSearch, WebFetch`, `permissionMode: plan`, `disallowedTools: Edit, Write, NotebookEdit, Agent`, spawned by C only. It researches trackers and upstream history, prepares patch descriptions and drafts replies into C's context; C writes the draft to `~/coordinator/` (outside git); May reads and sends. No external write capability is given to it, and the ASK rules of section 4.2 apply to it as to every subagent. This is a documentation-only change that fits COORDINATOR.md as written.

### 5. Phased plan (independently reviewable tasks)

Each phase is one task on the board with its own Design Challenger round where the process requires one, its own Verifier, its own tests, rollback and fresh-session acceptance. Phases 1, 2 and 3 touch the guard or the settings and run under the freeze rule "one editor at a time". Phases 4 and 5 touch the publication tools. The order below is the dependency order; 1 and 4 can run in parallel, 2 should not precede the signer cut-over unless May accepts the trade (decision 3).

| Phase | Task | Scope | Tests and acceptance | Rollback | Failure handling |
|---|---|---|---|---|---|
| 0 | docs (C) | Record this design decision with `append_record.py`; correct `HANDOVER-C.md` ("freeze #1 OPEN"); note that the effective settings file is the user file; note the ccd-cli/CLI version split | none | n/a | n/a |
| 1 | resume UNITY-20260929-003 | Guard false-positive fixes with the tightening invariant: RC1 line-wise legacy floor, RC1b, RC4, RC5, plus `/srv/aptly` paths inside tokens. No change to rule A or to interpreter strings. | all 417 existing tests; the 31 corpus false positives and the applicable `additional_cases` as new ALLOWED entries; the must-still-deny list from the -003 README; replay of all transcript commands through `inspect()` of main and of the branch: every deny→allow change is in the enumerated classes, 0 allow→deny; fresh A/B/C sessions: the permission-freeze checklist | copy `baseline-20261009/command_guard.py` back, or `git checkout 96122ab -- .claude/hooks/command_guard.py`; `install_command_guard.py --check` | any unexpected deny→allow in the replay is a Verifier FAIL; the task stays unmerged |
| 2 | new task (SECURITY, tool) | The two deliberate relaxations: (a) rule A's expansion trigger limited to the command-word position; (b) interpreter code strings as BLOB (words count only if `_STARTS_PROCESS`). Design Challenger required. | must-still-deny: every constructed-word form of -058 round 3 that keeps a literal `aptly` or has the expansion in the command word (`${a}ly publish`, `$(printf apt)ly publish`, `/usr/bin/apt?y publish`, `{apt,...}ly publish`), `python3 -c "...os.system('aptly ... publish')"`, the whole -018 data file; newly allowed: the 6 URL/JSON-key cases and case 3; replay as in phase 1 with the two classes enumerated; fresh-session checklist | as phase 1 | if the Challenger finds a reachable publish form that (a) or (b) opens *and* the signer is not yet live, defer that half to after phase 5 |
| 3 | new task (infra) | `permissions` block in `~/.claude/settings.json` written by `install_command_guard.py --apply` and verified by `--check`: allow prefixes from the transcript corpus (the `fewer-permission-prompts` procedure can produce the candidate list), the deny belt, the ask rules for trusted files and external writes, the guard rule "shell write into a trusted file: use Edit". May approves the user-file change (TWO-AGENTS.md rule). | `test_install_command_guard.py` extended: the block is present, deny precedes ask precedes allow, no allow rule covers a denied prefix; fresh throwaway session: an allowed read runs without a prompt, `Edit ~/.claude/settings.json` prompts, `gh issue create` prompts, `aptly publish list` is denied by both layers; record in the task which of the ask prompts were actually shown in the sessions' mode | restore `baseline-20261009/user-settings.json` | if ask prompts are not shown in the sessions' mode, stop; the fallback is the hook JSON `ask` route, which is its own task because it changes the fail-closed wrapper |
| 4 | new task (tool + process) | `taskctl.py approve-publication` (actor C), `publish_aptly.py` requires the approval record, `PUBLISHED` requires its sha256 in the publish record; ENGINEERING-PROCESS section 6 step 10 rewritten (C's GO for routine; May for exceptional and for the first publication of a source); section 5 review-depth text; `.claude/agents/upstream-liaison.md`. | `test_publish_contract.py` and new tests: refusal without approval, with a stale window, with another gate sha, with a used approval; a rehearsal publication on `/var/tmp/aptly-rehearsal` under C's marker proves the whole path end to end; fresh C session: `approve-publication` works for C and is refused for `--actor A` | revert the two scripts to 96122ab; the approval file is ignored by the old publisher | a publication that fails after the switch keeps today's behaviour (record not written, "do not rerun blindly") |
| 5 | UNITY-20260929-024 + May's steps 3-4 of -019 | Signer deployment and integration: May installs the service and generates the key on the signer VM and lists it in the vbox MCP `never_allowed`; `publish_aptly.py` gains the proposal step, the stand-in on `PATH` through its own `env`, the switch, `refresh --switch`, `/live`, "repository has expired" reporting, leftover `*.tmp` reporting, `go-w` on its trees; `policy.json` with the routine rules of section 4.4 and their refusal tests; a user timer on builder for `refresh --current`; the first live publication under the new key is approved by May on the console; rotation per -019 steps (both keys on the targets, then the new key only, old key removed from builder last). | the -021 end-to-end test with a throwaway key plus the new policy tests (one positive routine case, one refusal per rule); a rehearsal end to end on `/var/tmp/aptly-rehearsal/021` under C's marker; the first live publication is exceptional by definition and goes through the console; after it, one routine publication of an established package proves auto-signing; `apt update` on both targets verifies the new key | until the old key is removed from builder, the previous publisher path still works: revert `publish_aptly.py`, remove the stand-in from the env, publish with the local key (this window is deliberately kept until the first successful live signer publication) | signer unreachable or refusing: `publish_aptly.py` fails before the switch with the signer's reason; a refusal at the switch leaves the old trio live (proven in the -021 rehearsal); refresh failure leaves a marker and a log line and the repository expires visibly within 3 days |
| 6 | new task (cleanup) | Retire the live allowance (code, `live-commands.json` wording in sections 6 and 9); keep the rehearsal allowance; rerun the false-positive replay and record the new rate; update the memory guidance that C gives A and B (the "do not rephrase" rule stays for commands that contain a real aptly invocation) | guard tests still pass with the live code removed; replay shows no allow→deny | `git revert` | none |

**Proving each control works in a fresh session** (the permission-freeze README checklist, extended):

1. `install_command_guard.py --check` prints OK (after phase 3 it also checks the permissions block).
2. `pgrep -f unity-guard-probe-zzz` is denied; `true` and `git status` run.
3. `aptly publish list`, `rm -rf $X/`, `git add -A`, `git push --force` are denied in Bash and in a subagent.
4. A throwaway hook that exits 1 or sleeps 25 s on a harmless command: the command does not run (fail closed).
5. The `additional_cases` of -003 are rerun through `inspect()` as data: each is allowed or documented as still denied with the class it belongs to.
6. After phase 3: an `Edit` of `~/.claude/settings.json` prompts; after phase 4: `approve-publication` is refused for a non-C actor; after phase 5: a routine proposal is auto-signed and a proposal with a new source name reaches the console.

Strings for forbidden commands are written only with the Write tool into JSON and fed to the hook from Python, never through a shell (memory `feedback-guard-test-strings`; this is how the 06:54 incident happened).

### 6. Required regression tests and acceptance criteria (consolidated)

- **Guard, invariant tests** (`scripts/tests/test_command_guard.py`): every current DENIED entry stays denied; every current ALLOWED entry stays allowed; the -018 data file stays as is; the new ALLOWED entries are the minimal forms of the 31 corpus false positives and of `additional_cases` 1-8; the new DENIED entries are the must-still-deny lists of -003 and of phase 2.
- **Guard, corpus replay**: the `inspect()` replay over all distinct transcript commands, main versus branch, with every deny→allow change assigned to an enumerated class and 0 allow→deny changes outside tightening tasks. The result file is committed under the task's research directory.
- **Wiring** (`test_install_command_guard.py`): the handler is byte-identical in both files, fail-closed for rc≠0, timeout and stdout; the permissions block is present, ordered and free of allow/deny overlap.
- **Publisher** (`test_publish_contract.py`, `test_publish_snapshot_content.py`): approval required, single use, window, gate sha; the signer proposal, switch and refresh paths with the stand-in; "expired" and leftover-`*.tmp` reporting.
- **Signer** (`signer/` tests): the existing per-field refusal tests; the routine policy: one positive case and one refusal per rule; rate limits; rollback rule per decision 5.
- **Fresh-session acceptance**: the six checks of section 5, in new A, B and C sessions, recorded in the task's evidence with the session ids.
- **Operational acceptance for phase 5**: one exceptional and one routine live publication, `apt update` clean on both targets with the new keyring, `InRelease` `Valid-Until` present, a cadence refresh observed within 24 h.

### 7. Residual risks and decisions that remain May's

**Residual risks (accepted under the owner's model unless May decides otherwise):**

1. Any agent, subagent or compromised tool running as `claude` can forge C's GO, edit the settings, disable the hook, alter the board and the publish records, and, until phase 5, read and use the signing key. After phase 5 the key is out of reach, but a routine publication of an established package needs no human: a bad build that passes the gates is signed automatically. Bounded by the 3-day `Valid-Until`, backups, the console log, and the fact that today's only consumers are the test desktops.
2. The guard remains bypassable by construction (part E NOT VERIFIED, -018 FIX_PARTIAL). Phase 2 widens that by two documented classes. It is accident prevention, and the design treats it as such.
3. `NOPASSWD: ALL` and the `lxd` group stay. Root on builder can read every credential on it: GitHub token (admin), ssh keys to the targets, the Claude credentials file.
4. The public repository can be pushed to by every agent (the "ours" rule). Content leaks are a process control (rule S) with two incidents already. A server-side rule set does not stop content, only force pushes and deletion.
5. The signer policy is content-based; a wrong Debian version comparison or a Packages parser gap on the signer would be a policy hole. The refusal tests are the control.
6. The ASK layer may not function in the sessions' permission mode; if so, trusted-state edits stay detectable (`--check`) but not interruptible until the hook-JSON route is built.

**Decisions required from May before implementation:**

1. Approve the target architecture (sections 4.1-4.4) and the phase order.
2. Who runs `publish_aptly.py`: the task owner on C's GO (recommended), or C from its own worktree with the extra branch check.
3. Whether phase 2 (rule A and interpreter-string relaxations) may precede the signer cut-over, or must wait for phase 5.
4. The routine-policy numbers: sources per publication (1), binaries (40), the maintainer-script rule, the rate limits (10 min, 6 per day).
5. Rollback to the immediately preceding last-live set: routine (fast, previously approved content) or exceptional (as the -019 round-2 design says).
6. GitHub: enable branch protection on `main` (no force push, no deletion) and consider a fine-grained token without `admin` for builder.
7. Confirm that the first live migration, key rotation, `policy.json` edits and changes to `~/.claude/settings.json` remain his alone, and that the Upstream Liaison subagent is wanted.
8. Whether UNITY-20260929-019 can now move from BLOCKED to the signer deployment (its "who writes it" question is answered by -021).

### Appendix: stale items and small findings noticed on the way

- `~/coordinator/HANDOVER-C.md` still says freeze #1 is OPEN; `APTLY-FREEZE.md` records the lift on 2026-09-29 14:53Z.
- `.claude/hooks/live-commands.json` was removed at -047 DONE; the live prefix is therefore always denied, and `test_command_guard_live.py` skips. ENGINEERING-PROCESS sections 6 and 9 still describe the mechanism in the present tense.
- The three sessions run `ccd-cli 2.1.284`; the CLI on PATH is 2.1.278; `install_command_guard.py --check` tests the hook with `/bin/sh -c` independently of either, which is correct.
- `~/unity-distro/.claude/settings.json` is not loaded by sessions whose project root is `/home/claude`; the user file is the only effective one (this is why -012 installed the handler there). Keeping the byte-identical copy in the repository is still right: it documents the handler and the test suite reads it.
- `publish-records/*.json` carry no field for who authorised the publication; phase 4 adds the approval sha256.
- The `feedback-guard-aptly-no-rephrase` memory asks agents to record every false positive in the -003 evidence; that practice produced the evidence this review rests on and should continue through phases 1-2.
