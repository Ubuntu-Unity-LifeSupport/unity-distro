# Phase 3 - Claude Code permissions block (design; Design Challenger APPROVE at round 11 and at the final round on the consolidated structural revision, 2026-10-09)

Kind: `infra`. Changes `~/.claude/settings.json` (May's diff and separate GO
required before `--apply`, decision 7) through `scripts/install_command_guard.py`,
so the block is generated, reproducible and verified by `--check`. No guard
rule is relaxed; two narrow guard rules are added (shell writes into trusted
files are refused with "use Edit"; shell writes under `/etc/sudoers` are
refused). The installer never writes the live user file: it proposes, and
the Write tool, which asks May, writes.

## Measurement (2026-10-09)

The agent sessions A, B, C and this one run `ccd-cli --permission-mode
bypassPermissions --allow-dangerously-skip-permissions`; the CLI on PATH is
2.1.278, the sessions run 2.1.284. Three throwaway non-interactive sessions
(`claude -p`, haiku, cwd in the scratchpad, extra settings passed with
`--settings`, the live settings untouched) ran `echo probe-plain-1`,
`echo probe-ask-2` and `echo probe-hook-3` with:

- A. `bypassPermissions` + an `ask` rule `Bash(echo probe-ask*)` + a
  PreToolUse hook returning `permissionDecision: "ask"` for `probe-hook`:
  `probe-plain-1` ran; `probe-ask-2` and `probe-hook-3` both ended as
  permission denials (a non-interactive session cannot answer a prompt);
- B. `default` + the same settings: `probe-plain-1` ran, `probe-ask-2` was
  refused as "requested permissions ... not granted", the run stopped;
- C. `bypassPermissions` without the probe settings: all three ran.

So in 2.1.278 both an `ask` rule and a hook's `ask` decision are honoured
under `bypassPermissions`: they produce a permission request, which an
interactive desktop session shows to May through `--permission-prompt-tool
stdio`. Deny rules are documented to hold in every mode. The fresh-session
acceptance repeats A in a real desktop session (2.1.284), and probes the
`sudo` spellings (round 1 finding 5), before the block is relied on.

## Rule forms (round 1 finding 1)

Every Bash rule is written in the documented prefix form: either an exact
command `Bash(cmd args)` or a prefix `Bash(cmd args *)` with a space before
the `*`. Where both the bare form and the form with further arguments must
match, both rules are listed. No glued `*`, no `*` inside a word. The
documentation test checks exactly this. `sudo` is not in the documented
wrapper list (`timeout`, `time`, `nice`, `nohup`, `stdbuf`, `command`,
`builtin`, `noglob`), so `sudo` forms are matched as written and the bare
forms are listed as well.

## Design

### Part A - deny belt

`permissions.deny`, a second layer that needs no Python and survives a
disabled or broken hook (literal invocations only, the documented limit;
the guard stays the primary accident control; `xwd` mirrors the existing
guard rule; the belt covers the `Bash` tool only, `Monitor` is the guard's):

```json
"deny": [
  "Bash(aptly publish)", "Bash(aptly publish *)",
  "Bash(aptly task)", "Bash(aptly task *)",
  "Bash(aptly api)", "Bash(aptly api *)",
  "Bash(git push --force)", "Bash(git push --force *)", "Bash(git push -f)", "Bash(git push -f *)",
  "Bash(xwd)", "Bash(xwd *)",
  "Edit(//etc/sudoers)", "Write(//etc/sudoers)",
  "Edit(//etc/sudoers.d/**)", "Write(//etc/sudoers.d/**)",
  "Read(//home/claude/.gnupg/private-keys-v1.d/**)"
]
```

The `Read` rule keeps the built-in Read tool and the recognised Bash file
commands off the secret key material (the key moves to the signer in phase
5). The rehearsal and live allowance forms (`/usr/bin/aptly -config=...
publish`) are not matched by the belt and stay the guard's.

### Part B - the ASK layer

`permissions.ask`. May sees the prompt in the desktop app; everything else
stays unasked.

**Trusted files** (built-in Edit and Write; the base checkout's paths. Task
worktrees under `~/work/*/` hold copies of the same files; an edit there is
ordinary task work, brought into effect only by C's merge and the phase-4
tool-blob check, so it is not asked):

```json
"Edit(//home/claude/.claude/settings.json)", "Write(//home/claude/.claude/settings.json)",
"Edit(//home/claude/.claude/settings.local.json)", "Write(//home/claude/.claude/settings.local.json)",
"Edit(//home/claude/.claude/settings.json.proposed)", "Write(//home/claude/.claude/settings.json.proposed)",
"Edit(//home/claude/.claude/settings.json.bak-UNITY-20260928-012)", "Write(//home/claude/.claude/settings.json.bak-UNITY-20260928-012)",
"Edit(//home/claude/.claude/plugins/**)", "Write(//home/claude/.claude/plugins/**)",
"Edit(//home/claude/.claude/skills/**)", "Write(//home/claude/.claude/skills/**)",
"Edit(//home/claude/.claude/agents/**)", "Write(//home/claude/.claude/agents/**)",
"Edit(//home/claude/.claude/commands/**)", "Write(//home/claude/.claude/commands/**)",
"Edit(//home/claude/.claude/shell-snapshots/**)", "Write(//home/claude/.claude/shell-snapshots/**)",
"Edit(//home/claude/.bashrc)", "Write(//home/claude/.bashrc)",
"Edit(//home/claude/.profile)", "Write(//home/claude/.profile)",
"Edit(//home/claude/.bash_profile)", "Write(//home/claude/.bash_profile)",
"Edit(//home/claude/.bash_aliases)", "Write(//home/claude/.bash_aliases)",
"Edit(//home/claude/.gitconfig)", "Write(//home/claude/.gitconfig)",
"Edit(//home/claude/.ssh/authorized_keys)", "Write(//home/claude/.ssh/authorized_keys)",
"Edit(//home/claude/.ssh/id_*)", "Write(//home/claude/.ssh/id_*)",
"Edit(//home/claude/.config/gh/**)", "Write(//home/claude/.config/gh/**)",
"Edit(//home/claude/.gnupg/**)", "Write(//home/claude/.gnupg/**)",
"Edit(//home/claude/.config/aptly-signer/**)", "Write(//home/claude/.config/aptly-signer/**)",
"Edit(//home/claude/.aptly.conf)", "Write(//home/claude/.aptly.conf)",
"Edit(//home/claude/unity-distro/.claude/**)", "Write(//home/claude/unity-distro/.claude/**)",
"Edit(//home/claude/unity-distro/signer/**)", "Write(//home/claude/unity-distro/signer/**)",
"Edit(//home/claude/unity-distro/docs/ENGINEERING-PROCESS.md)", "Write(//home/claude/unity-distro/docs/ENGINEERING-PROCESS.md)",
"Edit(//home/claude/unity-distro/scripts/publish_aptly.py)", "Write(//home/claude/unity-distro/scripts/publish_aptly.py)",
"Edit(//home/claude/unity-distro/scripts/approval_record.py)", "Write(//home/claude/unity-distro/scripts/approval_record.py)",
"Edit(//home/claude/unity-distro/scripts/taskctl.py)", "Write(//home/claude/unity-distro/scripts/taskctl.py)",
"Edit(//home/claude/unity-distro/scripts/safe_git.py)", "Write(//home/claude/unity-distro/scripts/safe_git.py)",
"Edit(//home/claude/unity-distro/scripts/install_command_guard.py)", "Write(//home/claude/unity-distro/scripts/install_command_guard.py)",
"Edit(//home/claude/unity-distro/scripts/create_release_gate.py)", "Write(//home/claude/unity-distro/scripts/create_release_gate.py)",
"Edit(//home/claude/unity-distro/scripts/signer_client.py)", "Write(//home/claude/unity-distro/scripts/signer_client.py)",
"Edit(//home/claude/unity-distro/scripts/gpg_standin.py)", "Write(//home/claude/unity-distro/scripts/gpg_standin.py)"
```

`~/.ssh/config` and `known_hosts` stay unasked (appending VM hosts is
ordinary work).

**The installer never writes the live user file** (structural
replacement, consolidated revision after round 11; it supersedes the
`--apply` gate and guard rule 2 of rounds 1-10). The live file
`~/.claude/settings.json` is written only by the built-in Write tool, and
that write is an `ask` rule above, so May's prompt is a property of the
tool, not the result of parsing a command line:

- `install_command_guard.py --propose` writes the complete intended
  settings (hook handler and permissions block, other keys kept) to
  `~/.claude/settings.json.proposed`, mode 0600, and prints the unified
  diff against the live file. It never touches the live file.
- `--apply` refuses whenever the resolved `--settings` path is the live
  user file ("write it with the Write tool from settings.json.proposed;
  the Write prompt is May's GO") and keeps working for any other path
  (the tests' temporary files). This is one `os.path.realpath` comparison,
  not an analysis of how the installer was invoked.
- `--check` compares the live file with what `--propose` would write and
  fails on any difference (so a live file that drifts from the constant
  is caught at every session start, as the hook handler is today).
- Rollback is the same path in reverse: `--propose --remove-permissions`
  writes the proposal without the block; the Write tool writes it on
  May's prompt.

Why this instead of rule 2: rounds 3-11 spent eight rounds closing shell
spellings that deliver the installer its argument (`--app`, `xargs`, a
variable, `${x:=}`, `for`, `git -c core.pager`, `sed 1e`, body-level
groups, `runpy`, unstripped wrappers). Each was real and each had a
sibling. The structural change removes the whole class: no shell command
can make the installer write the live file, so there is nothing left for
a text rule to judge, and the Write-tool prompt is honoured under
`bypassPermissions` (measured). A shell write into the live file by
redirection, `tee`, `cp`, `sed -i` or an interpreter is guard rule 1's
business, as before; a shell write by a form rule 1 does not list is the
stated residual (accident prevention, not a boundary).

The `settings.json.proposed` file is itself a trusted file (Edit/Write
ask; rule 1 denies shell writes into it), so the proposal cannot be
swapped between `--propose` and the Write without a prompt either.

**External writes** (write subcommands only, round 1 finding 4; reads such
as `gh repo view`, `gh issue view`, `gh pr diff`, `gh api` GET stay
unasked; the process rule "May reads the text first" is unchanged, this
makes it a prompt):

```json
"Bash(gh issue create *)", "Bash(gh issue comment *)", "Bash(gh issue close *)", "Bash(gh issue edit *)", "Bash(gh issue reopen *)", "Bash(gh issue transfer *)",
"Bash(gh pr create *)", "Bash(gh pr comment *)", "Bash(gh pr merge *)", "Bash(gh pr close *)", "Bash(gh pr edit *)", "Bash(gh pr review *)", "Bash(gh pr ready *)",
"Bash(gh release create *)", "Bash(gh release edit *)", "Bash(gh release delete *)", "Bash(gh release upload *)",
"Bash(gh repo create *)", "Bash(gh repo edit *)", "Bash(gh repo delete *)", "Bash(gh repo rename *)", "Bash(gh repo fork *)", "Bash(gh repo sync *)", "Bash(gh repo archive *)",
"Bash(gh api -X *)", "Bash(gh api --method *)", "Bash(gh api -F *)", "Bash(gh api -f *)", "Bash(gh api --field *)", "Bash(gh api --raw-field *)", "Bash(gh api --input *)",
"Bash(curl -X *)", "Bash(curl --request *)", "Bash(curl -d *)", "Bash(curl --data *)", "Bash(curl --data-binary *)", "Bash(curl --data-raw *)", "Bash(curl -F *)", "Bash(curl --form *)", "Bash(curl -T *)", "Bash(curl --upload-file *)",
"Bash(wget --post-data *)", "Bash(wget --post-file *)",
"Bash(dput *)", "Bash(debsign *)", "Bash(bzr push *)"
```

`git remote add` / `set-url` are not asked (they follow `gh repo create`,
which asks; a second prompt adds nothing). Corpus check (round 2): the
`sudo useradd/chpasswd/visudo` hits all run inside `ssh target '...'` and
prompt nobody; the prompts that will appear are `gh repo create/edit`
(May-confirmed work) and `gh api -X DELETE` for branch cleanup (two cases
in the corpus, both May's decisions).

**Privileged system changes** (the sudo forms that change trust state;
ordinary sudo for chroots, apt and services stays unasked; both the `sudo`
and the bare spelling are listed, since `sudo` is not a documented stripped
wrapper; `visudo` in any spelling and every shell write under `/etc/sudoers*`
are denied by guard rule 3 below, so they are not listed here - an asked
and denied command would show May a denial, never a prompt):

```json
"Bash(sudo usermod *)", "Bash(sudo useradd *)", "Bash(sudo passwd *)", "Bash(sudo chpasswd)", "Bash(sudo chpasswd *)",
"Bash(gpg --gen-key)", "Bash(gpg --gen-key *)", "Bash(gpg --full-generate-key)", "Bash(gpg --full-generate-key *)",
"Bash(gpg --quick-generate-key *)", "Bash(gpg --delete-secret-keys *)", "Bash(gpg --delete-secret-and-public-key *)",
"Bash(gpg --export-secret-keys)", "Bash(gpg --export-secret-keys *)", "Bash(gpg --import)", "Bash(gpg --import *)"
```

### Guard additions (`command_guard.py`, two rules)

1. **Shell writes into trusted files are denied** with "trusted file
   <path>: edit it with the Edit tool, which asks May". Deny rather than
   ask, because the Edit prompt shows May a diff and a redirect prompt would
   not. The trusted set lives once, in `install_command_guard.py`
   (`TRUSTED_FILES`, absolute paths and globs), imported by the guard. The
   rule covers these listed forms, not "every write": redirections `>`,
   `>>`, `>|`, `&>`, `n>` whose target resolves to a trusted path; `tee`
   and `tee -a` operands; the destination (last operand, or `-t`) of `cp`,
   `mv`, `install`, `rsync`, `ln -s`, `dd of=`; `sed -i*`/`--in-place`
   operands; `truncate` operands; `gzip`, `bzip2`, `xz` and `zstd`
   operands (they replace the original; round 9 remark); `curl -o`,
   `--output`, `-O` and `wget -O`, `-P` destinations; `rm` and `mv` with a
   trusted path as
   source (removing `~/.claude/settings.json` removes hook and block); and
   an interpreter heredoc or `-c` string that names a trusted literal
   together with `'w'`, `'a'`, `write_text` or `write_bytes`. Paths are
   resolved against the payload's `cwd`, a leading `cd`, `~` and `$HOME`.
   Reads (`cat`, `grep`, `diff`, `cp SRC`, `--check`) are untouched:
   `_redirect_targets` already excludes `<` and fd duplication.
   Round 2 findings 4-5: the interpreter form is narrowed to adjacency, an
   `open(` whose first argument is a trusted literal and whose mode
   argument in the same call is `'w'`, `'a'`, `'w+'` or `'a+'`,
   `Path(<trusted literal>).write_text/write_bytes`, or a trusted literal
   as an argument of `shutil.copy*`, `shutil.move`, `os.replace`,
   `os.rename`, `os.link` or `os.symlink` (final-round remark); a script that reads a
   trusted file and writes a report elsewhere is ordinary work and stays
   allowed. A destination that is the parent directory of a trusted path
   (`cp settings.json ~/.claude/`, `-t ~/.claude`, `mv x
   ~/unity-distro/.claude`) counts as a trusted write, and so does `rm -r`
   or `mv` of an ancestor directory of a trusted path (`~/.claude`,
   `~/unity-distro/.claude`, `~/unity-distro/scripts`, `~/.gnupg`,
   `~/.ssh`, `~/.config/gh`). A destination that is an existing directory
   (or `-t DIR`) is resolved as `DIR/basename(SRC)` for each source, so
   `cp settings.json ~/.claude/` is caught while `cp new.py
   ~/unity-distro/scripts/` or `cp key.pub ~/.ssh/` is not (round 3
   finding 7). A destination that is a variable other than `$HOME`/`~` is
   not resolved and not denied (a documented residual: denying it would
   refuse ordinary `cp x "$DEST"` work).
   Implementation notes (round 3 finding 6): `main()` passes the payload's
   `cwd` into `inspect()`; the heredoc and `-c` clause is its own pass over
   the scanner's bodies and `-c` tokens before `_levels` (which drops
   bodies and keeps only process-starting blobs); a `_redirect_targets`
   result of `None` (a `>` inside a token) is "no decision", not a denial;
   `TRUSTED_FILES` is imported from the installer by path with `importlib`,
   relative to the guard's own `__file__`, since the hook runs under
   `python3 -I`.
2. (Withdrawn in the consolidated revision: the installer no longer
   writes the live file, see Part B. The judging of installer invocations
   designed in rounds 1-10 is not implemented.)
3. **Shell writes under `/etc/sudoers`** (`/etc/sudoers`, `/etc/sudoers.d/`
   and anything below) by redirection, `tee`, `cp`/`mv`/`install`
   destination, `sed -i`, `visudo` or `rm`/`mv` of them, with or without
   `sudo` and its options, are denied with "sudoers is May's own change"
   (round 2 finding 7). Together with the belt's Edit/Write deny this
   closes every sudoers path to the sessions; decision 6 names the token
   and sudo arrangements as May's own actions.

### Allow rules

None. Under `bypassPermissions` they are inert; writing them would mislead
a reader into thinking prompts exist for the rest. If May later moves the
sessions to another mode, the corpus scan of 2026-10-09 (11131 unique
commands, `corpus_prefixes.py`) gives the candidate list.

### Installer

`install_command_guard.py`:

- `--propose [--remove-permissions]` writes `~/.claude/settings.json.proposed`
  (0600) and prints the diff; `--apply` refuses the live user file by
  `realpath` comparison and serves the tests' temporary files; `--check`
  fails when the live file differs from the proposal the constant yields
  (hook handler and block), when `disableAllHooks` is set in the user or
  the project file, when `permissions.allow` contains anything, when
  `defaultMode` or `disableBypassPermissionsMode` is present, or when
  `~/.claude/settings.local.json` exists; it reports (without failing)
  managed settings, `allowedTools` and user-site customisations;
- the block is a constant (`PERMISSIONS`) next to the handler, and the
  trusted set (`TRUSTED_FILES`, `TRUSTED_DIRS`, `TRUSTED_GLOBS`) next to
  it; the guard imports the trusted set from the installer by path,
  relative to its own `__file__` (so a worktree test copy imports its
  sibling), and `base_problems()` also requires the installer itself to be
  committed and unchanged (round 2 finding 6); the modes are `--check`,
  `--diff` (the change the proposal makes to the live file), `--propose`
  and `--apply` (temporary paths only); every write target of the
  installer, the proposal path included, is refused when its realpath is
  the live user file, and the proposal is written with `write_atomic`
  (final-round remark); `--check` fails when: the block is missing or
  differs; `disableAllHooks` is set in the user or the project file;
  `permissions.allow` contains anything; `defaultMode` or
  `disableBypassPermissionsMode` is present (May's decisions, not the
  installer's); `~/.claude/settings.local.json` exists (it is the project
  settings of every session rooted at `/home/claude` and could carry
  `disableAllHooks`, `allow` or `defaultMode` unseen; round 1 finding 2);
  it reports (without failing) `/etc/claude-code/managed-settings.json`,
  `allowedTools` in `~/.claude.json` and user-site customisations.
- there is no `apply_gate()`: the live file is never a target of the
  installer.
- `live_problems()` gains a trusted-write probe (a redirect into
  `~/.claude/settings.json` must be denied by the handler) next to the
  existing deny/allow probes.
- The repository's `.claude/settings.json` carries the byte-identical
  block, as it does for the hook.

## Not in this phase

No relaxation of any guard rule (phase 2, after phase 5). No change to the
sessions' mode. No allow rules. No change to what agents may do: only where
May is asked, plus the two denials above, which turn a bypass of the ask
layer into a refusal.

## Tests

- `test_install_command_guard.py`: `--propose` writes the proposal with
  mode 0600 and prints the diff, never touching the settings path;
  `--apply` refuses a `--settings` that resolves to the live user file (a
  symlink to it included) and writes a temporary one; `--check` on
  settings without the block, with a differing block, with an `allow`
  list, with `defaultMode`, with a `settings.local.json` present, with
  `disableAllHooks` in the project file; `--diff` shows exactly the
  block; the repository copy equals the proposal; `live_problems` includes
  the trusted-write probe.
- `test_command_guard.py`: shell writes into trusted paths in each listed
  form are denied with the new message (redirect, `tee`, `cp`/`mv`
  destination resolved as `DIR/basename(SRC)`, `sed -i`, `gzip`,
  `curl -o`, `rm` source, ancestor `rm -r`, a Python heredoc with
  `open(<trusted>, 'w')`); the same forms on other paths unchanged; reads
  of trusted paths unchanged (`cat`, `grep`, `diff`, `cp SRC elsewhere`,
  `--check`, a Python heredoc that reads a trusted file and writes a
  report elsewhere); the sudoers rule in every listed spelling; the
  trusted set imported from the installer (one source).
- A documentation test: every `Bash(...)` rule in the block is an exact
  command or a prefix ending in ` *`; every path rule starts with `//`.

## Rollout order

1. Merge the branch (installer, guard rules, tests, repository copy of the
   block). The user file is unchanged by the merge.
2. `python3 scripts/install_command_guard.py --diff` in the base checkout;
   the exact diff goes to May.
3. May's separate GO.
4. `python3 scripts/install_command_guard.py --propose` in the base
   checkout writes the proposal and prints the diff (the same diff May saw
   in step 2); the live file is written with the Write tool from the
   proposal. For this first write the ask rule is not yet in the user
   file, so May's GO in step 3 is the control of this step; from then on
   the Write tool prompts him. Then `--check`.
5. The fresh-session acceptance below.

## Acceptance (fresh A, B, C sessions, May's checklist)

- `install_command_guard.py --check` OK;
- `Edit` of `~/.claude/settings.json` prompts (May declines);
  `gh issue create --title probe --body probe --repo x/y` as a dry form
  prompts (May declines); `sudo usermod --help` prompts (May declines; an
  asked command that no guard rule denies, so this settles the `sudo`
  wrapper question, round 1 finding 5);
- `aptly publish list` typed by May himself in a session is denied by the
  permissions layer even with the hook pointed at `/bin/true` in a
  throwaway copy of the settings (proves the belt); the existing checklist
  denials and allows unchanged;
- a shell redirect into `~/.claude/settings.json` is denied by the guard;
  `python3 scripts/install_command_guard.py --apply` (the live file) is
  refused by the installer itself; a Write of the proposal over the live
  file prompts (May declines in the probe);
- `for i in 1; do gh issue create --title probe --repo x/y; done` still
  prompts after Claude Code splits the compound command (May declines).

## Rollback

`python3 scripts/install_command_guard.py --propose --remove-permissions`
in the base checkout, then the Write tool writes the proposal over the
live file (May's prompt), then revert the merge on `main` so the guard
rules, the constant and the tests go away; `--check` against the previous
expectation afterwards. Copying `baseline-20261009/user-settings.json`
back by shell is a trusted-file write that guard rule 1 denies; the Write
tool is the way, and it asks.

## Residual risks

**Other writers of the live file.** The desktop app's settings tool
(`mcp__ccd_settings__set_setting`) writes preference keys (notifications,
output style) without a prompt; its key set cannot reach `hooks` or
`permissions`, and `--propose` carries other keys forward, so `--check`
stays green. A symlink alias made in an earlier call and written through
the Write tool is the two-call residual; the acceptance adds one probe: a
Write through a non-canonical spelling of the path must prompt (final-round
remark).

**Shell writes the guard does not list** (rule 1 is accident prevention):
a write into the live settings file by a form rule 1 does not model (an
interpreter without the recognised idioms, a program outside the list, a
file moved over it two calls later) reaches the file with no prompt;
`--check` at the next session start detects the drift. This is the same
class the guard has always excluded ("files written earlier and run later
cannot be reliably secured", section 9); the accepted model is accident
prevention, not a boundary against a session that evades deliberately.

The guard imports the trusted set from the installer: a syntax error in
the installer makes the hook fail closed for every Bash call until it is
fixed (acceptable, and `--check` names it). `gh api -XDELETE` (no space)
is not matched by the ask rule and `curl -X GET` is matched although it
reads; both are small residuals of the prefix form.

A session can still edit the user settings through a form the guard does
not list (an interpreter without the recognised write idioms, a file moved
over it by a program outside the list); `--check` detects a changed block,
a missing hook, a local settings file and `disableAllHooks` at the next
session start. The prompt goes to whoever is at the desktop app; the project
has one operator.

## Design review round 1 (2026-10-09): REVISE, taken

1 every Bash rule in documented prefix form (bare and ` *` pairs), the
documentation test enforces it; 2 `settings.local.json` in the trusted set
and its presence a `--check` failure, managed settings reported; 3 the
installer's `--apply`: ask rules for the two canonical spellings, the guard
denies every other spelling, `--apply` refuses outside the base checkout; 4
`gh` narrowed to write subcommands, `git remote` dropped; 5 bare and `sudo`
spellings both listed, probe in acceptance; 6 trusted set widened (shell
profiles, shell snapshots, ssh keys and authorized_keys, gh identity,
gitconfig, the settings backup, plugins and skills); 7 the guard rule's
forms spelled out, deny rationale stated, Python write idioms covered,
reads untouched; 8 scope statements (xwd mirrors the guard, allowances
unaffected, Monitor is the guard's).

## Design review round 2 (2026-10-09): REVISE, taken

1 `python3 -m` and import forms denied by guard rule 2; 2 the installer
checks the unresolved `__file__`, `__spec__ is None`, `sys.argv[0]` and
refuses `-c`/stdin forms; 3 rule 2 compares the raw group; 4 the
interpreter write form narrowed to `open(<trusted>, 'w'|'a')` adjacency;
5 directory destinations and ancestor removal count, other-variable
destinations are a documented residual; 6 `base_problems()` covers the
installer and the import is `__file__`-relative; 7 sudoers shell writes in
every spelling are the guard's third rule; 8 `~/.claude/agents/**` and
`commands/**` in the trusted set. Non-blocking taken: the ordered rollout
(`--diff`, May's GO, `--apply`) and the loop-prompt acceptance probe.

## Design review round 3 (2026-10-09): REVISE, taken

1 `visudo` ask rules dropped (guard rule 3 denies every spelling); the
sudo-wrapper acceptance probe is `sudo usermod --help`; 2 the installer's
origin gate applies only to the real user file, the tests' temporary
settings are not gated; 3 rule 2 compares the whole raw command string
with the canonical strings (optionally after `cd /home/claude/unity-distro
&& `), so quoting, word splitting and subshells are denied; 4 tests for
rule 3 and for the `-m`, `exec`, `-c`, quoted and subshell forms; 5 one
wording (unresolved `__file__`); 6 implementation notes (payload `cwd`,
own body pass, `None` from `_redirect_targets`, `importlib` by path); 7
directory destinations resolved as `DIR/basename(SRC)`.

## Design review round 4 (2026-10-09): REVISE, taken

1 (blocking) argparse abbreviation: `allow_abbrev=False`, the real-file
gate requires `argv[1:] == ["--apply"]` exactly, rule 2 denies any `--a`-
prefixed token next to the installer's name, tests include `--app`; 2
confirmed; 3 the ` *` ask forms dropped; 4 the gate is a tested function
with an injected real path; 5 the first `--apply` has no prompt - May's GO
is its only control, stated in the rollout; 6 rollback stated as a revert
plus `--apply`, or May's own write. Non-blocking noted in Residual risks.

## Design review round 5 (2026-10-09): REVISE, taken

1 (blocking) indirection: rule 2 now allows the installer's name only in
the exact canonical strings and in explicit read forms, and denies every
visible indirection (expansion, `xargs`, `eval`, `find -exec`, `sh -c`,
pipes); the invisible rest (a file written earlier, encoded text) is stated
as a residual instead of "can never"; 2 (blocking) rollback through a new
`--remove-permissions` under the same gate and ask rule, since the
installer never rewrote `permissions`; 3 one gate signature and one list;
4 confirmed; 5 `--check` reports user-site customisations, the gate uses
no `assert`.

## Design review round 6 (2026-10-09): REVISE, taken

1 (blocking) rule 2 scoped to executing groups; naming the installer as a
git, cp, linter or commit-message operand is not its business, so the
phase-3 implementation can stage and describe its own change; 2 the `cd`
example spelled with the absolute path; 3 `argv[1:]` is one of the two
flags, the tests list `--remove-permissions`, the indirection denials and
the read-form acceptances; 4 the duplicated fragment removed; 5 `--base`
and `--settings` literal extras allowed in the read form.

## Design review round 7 (2026-10-09): REVISE, taken

1 confirmed; 2 (blocking) rule 2 inverted to a closed non-executing set
plus explicit read forms, so unstripped wrappers are judged and denied, a
test for an unlisted wrapper added; 3 interpreter matched by basename in
any directory; 4-6 confirmed. Remarks taken: `--help`/`-h`, `-I`,
redirections, pipes out and listed read-only wrappers accepted on the read
forms.

## Design review round 8 (2026-10-09): REVISE, taken

1 (blocking) the non-executing exemption is `_is_reader(group, None)`,
not a command-name set, excluding pure assignments and copier groups
whose installer-naming token is not a source; the four probe strings and
the assignment form are in the denied tests; 2 `find` (no `-exec`/`-ok`/
`-delete`), `awk` (no `system(`/`|`/`>`) and `python -m <linter>` join the
read forms; 3-4 confirmed. Remarks taken: a reader that names the
installer and writes a file is judged; the `--settings` exemption is for
in-process tests only.

## Design review round 9 (2026-10-09): REVISE, taken

1 (blocking) variable-binding readers judged like assignments; 2
(blocking) only unexposed readers exempt (substitution, pipe, file for a
runner); 3 (blocking) rule 2 uses the pre-`_levels` body pass (`runpy`
and friends). Placement fixed: after `_levels`, folded into `rest`, before
the rehearsal branch. Remarks taken: relative operands resolved against
the payload `cwd`, `--no-pager` documented, direct execution of the
installer judged, `gzip`/`xz`/`curl -o`/`wget -O` added to rule 1.

## Design review round 10 (2026-10-09): REVISE, taken

1 (blocking) rule 2 judges the groups of every level, body levels
included; 2 (blocking) an exempt reader must name the installer with
literal tokens and carry no `${name=}`/`${name:=}` default assignment; 3
(blocking) the pre-`_levels` body pass is limited to interpreter-owned
bodies and `-c`/`-e` strings, TEXT bodies excluded, so commit messages and
docs naming the installer stay accepted. Remarks taken: `os.chdir(cwd)` at
the top of `inspect()`, raw bodies from a separate `_collect`, `runners`
hoisted once, the worktree copy asymmetry in Residual risks, `--check`
fails versus reports spelled out.

## Design review round 11 (2026-10-09): APPROVE

Two non-blocking remarks: `sh -c '...'` naming the installer would have
been judged under rule 2 unlike a bare `grep`; `bash`/`sh` are not in
`_INTERPRETERS` and body-level judging, not the pre-pass, covered shell
heredocs. Both fall away with the consolidated revision below.

## Consolidated revision after round 11 (May's termination criteria)

### Remaining findings, all rounds

| # | Scenario | Reproducible | Property at stake | Severity | Covered by tests | Fix | Residual |
|---|---|---|---|---|---|---|---|
| 1 | Indirection delivers the installer its argument (`xargs`, `${x:=}`, `for`, `git -c core.pager`, `sed 1e`, body-level group, `runpy`, unstripped wrapper, `--app`) and the live file is written with no prompt | yes, probed on main (allowed today) | decision 7: global settings only with May's diff and confirmation | was blocking under the rule-2 design | would have needed ~40 denied strings | **structural**: the installer never writes the live file; the Write tool does, and it asks | a shell write by an unlisted form (rule 1 residual) |
| 2 | Two-call indirection (file written in one call, run in the next; encoded text) | yes (by construction) | same | theoretical under the accepted model | n/a | none: outside the model (section 9) | stated |
| 3 | `sh -c '...'` naming the installer denied unlike bare `grep` | yes | usability | non-blocking | n/a | falls away with rule 2 | none |
| 4 | `bash`/`sh` not in `_INTERPRETERS`; shell heredocs relied on body-level judging | documentation | clarity | non-blocking | n/a | falls away with rule 2 | none |
| 5 | Worktree `cp x scripts/install_command_guard.py` denied while `sed -i` exempt | yes | usability | non-blocking | n/a | falls away with rule 2 | none |
| 6 | `gh api -XDELETE` (no space) not asked; `curl -X GET` asked | yes | prompt precision | non-blocking | documentation test checks forms only | none (prefix form) | small |
| 7 | Guard imports `TRUSTED_FILES` from the installer: a syntax error there fails every Bash call closed | yes | availability | non-blocking | `--check` names it | accepted (fail closed) | stated |
| 8 | ASK measured in 2.1.278 non-interactive; sessions run 2.1.284 interactive | measured for A; B pending | the whole ASK layer | acceptance item | n/a | fresh-session acceptance before relying on it | until measured |
| 9 | `sudo` as a stripped wrapper would void `Bash(sudo ...)` ask rules | not documented either way | privileged-change prompts | acceptance item | n/a | probe `sudo usermod --help` in acceptance | until measured |
| 10 | Rule 1 does not resolve destinations that are variables other than `$HOME`/`~` | yes | accident prevention | non-blocking | listed | none (would deny ordinary `cp x "$DEST"`) | stated |
| 11 | The prompt reaches whoever is at the desktop app | n/a | authorisation | accepted | n/a | one operator | stated |
| 12 | The first write of the block has no ask rule yet (round 4 finding 5) | by construction | decision 7 | rollout item | n/a | May's GO in rollout step 3 is the control of step 4 | none after the first write |
| 13 | Row 8: measurement B (default mode) was run; what is pending is the repeat of measurement A in a real 2.1.284 desktop session | - | - | acceptance item | - | fresh-session acceptance | until measured |

Proven blocking defects after round 11: none. Finding 1 was the one class
that kept producing siblings; it is closed structurally rather than by
another text rule.

### Structural assessment (May's question)

Rule 2 tried to decide, from shell text, whether a program that writes the
settings file was invoked in the one blessed way. That is the wrong layer:
the decision "may the live settings change" belongs to the action that
changes them. Making the installer incapable of writing the live file and
leaving the write to the Write tool puts the prompt where the action is.
The same reasoning already shaped phases 4 and 5 (the approval record and
the signer policy decide about the publication, the guard does not).
Rule 1 (shell writes into trusted files) stays a text rule, and that is
right for its purpose: it prevents accidents by listed forms and claims
nothing more. Rule 3 (sudoers) is a plain deny of a path family.

### What changes in this revision

Rule 2 and `apply_gate()` are withdrawn; `--propose` is added; `--apply`
refuses the live file by `realpath`; the four canonical ask strings are
replaced by the Edit/Write ask on `settings.json.proposed`; rollout step
4, rollback, tests and acceptance follow. No allowed action is added, no
guard rule is relaxed. One final Design Challenger round checks this
revision only.

## Design review, final round (2026-10-09): APPROVE

On the consolidated structural revision. Findings: the replacement is
sound (Edit and Write ask rules on the live file and the proposal; rule 1
lists the copier and remover forms; a hard-linked `--settings` cannot reach
the live inode because `write_atomic` ends in `os.replace`); nothing
protective removed and no action added; the rollout order explicit; the
table correct. Non-blocking remarks taken into the implementation: the
header and installer text no longer describe rule 2; `--diff` is in the
mode list; rule 1 adds `ln` in every form, `shred`, `unlink`,
`chmod`/`chattr`, `tar -x -C`/`unzip -d`, and the interpreter idioms
`shutil.copy*`/`move`, `os.replace`/`rename`/`link`/`symlink`; every
installer write target is realpath-checked and the proposal is written
atomically; the desktop settings tool and the Write-through-alias probe are
in Residual risks and Acceptance; table rows 12-13 added.

## Implementation (branch `arch/permission-model-phase3`)

- `scripts/install_command_guard.py`: `TRUSTED_FILES`, `TRUSTED_DIRS`,
  `TRUSTED_GLOBS`, `SUDOERS_PATHS` and `PERMISSIONS` (17 deny, 124 ask
  rules, built from the trusted set; `rule_form_problems()` checks the
  documented forms); modes `--check`, `--diff`, `--propose
  [--remove-permissions]`, `--apply` (temporary paths only;
  `allow_abbrev=False`); `write_atomic` refuses every target whose
  realpath is the live user file; `--check` fails on a missing or
  differing block, `allow` rules, `defaultMode`,
  `disableBypassPermissionsMode`, `disableAllHooks`, a
  `settings.local.json`, and the three probes (`pgrep -f`, a redirect into
  the live settings, `true`); it reports managed settings, `allowedTools`
  and user-site customisations; `base_problems()` also covers the installer.
- `.claude/hooks/command_guard.py`: the trusted set imported from the
  installer by path (a failure fails the hook closed); `inspect()` takes
  the payload `cwd` and changes into it; rule 1 (`_write_targets`,
  `_interpreter_writes`, `_trusted_rules`) over every executed group of
  every level and over interpreter `-c` strings and heredoc bodies; rule 3
  (sudoers paths and `visudo`) through the same detector. Bytecode caches
  under a trusted directory are not trusted. `chmod`/`chattr` were
  dropped from rule 1 at implementation: no tool other than the shell can
  change a mode, and `--check` detects an unreadable settings file.
- `.claude/settings.json` (repository copy) carries the block.
- Tests: `test_install_command_guard.py` (10 new cases: forms, propose,
  live-file refusal in two spellings, temporary apply, abbreviation,
  block missing/altered, allow/modes, local settings, the trusted-write
  probe through a weakened guard), `test_command_guard.py`
  (`test_phase3_trusted_file_writes`: 28 denied and 16 allowed forms).
- Measured before the merge: transcript replay of 11283 commands against
  main: 0 deny->allow, 6 allow->deny, each a write into a trusted file
  (three shell writes of `~/.config/aptly-signer/standin.json` during the
  -021 rehearsal, one `chmod g-w ~/.aptly.conf` - since exempted -, one
  bytecode-cache removal under `.claude/` - since exempted -, and one
  scratchpad script whose heredoc body carried a write-idiom string as
  data, the form the project's own rule says to avoid).

## Verification round 1 (2026-10-09)

Independent Verifier on df364bc: **FAIL** (INDEPENDENTLY_REPRODUCED). The installer
held in 25 argument combinations against a fake home (the live file's inode and
bytes never changed; symlinks refused; `allow_abbrev=False` effective); 150 of
166 expected forms were right; 485 tests OK; 440 corpus commands unchanged.
Five classes of rule-1 forms were missed:

| # | Finding | Fix |
|---|---------|-----|
| 1 | `sh -c` / `bash -c` strings were one token, never lexed (`sudo sh -c 'echo x >> /etc/sudoers'` allowed) | the string is lexed as a nested command (quoted `>` restored) and rule 1 runs over it, depth-limited; `-ec` clusters count |
| 2 | a leading `cd` was not followed (`cd ~/.claude && echo x > settings.json`) | rule 1 tracks `cd`/`pushd` per level (literal targets; `cd -` or a variable makes relative paths unresolvable; a `)` ends a subshell's `cd`) |
| 3 | `>|` lexed as `>` plus a pipe | `>|` is one token and the first redirect operator tried |
| 4 | `curl -O` into the session directory | `-O`/`--remote-name`: the URL's basename in the working directory |
| 5 | `wget -P DIR`, `unzip -d DIR`, `tar xf … -C DIR`, `--directory=` classified the directory as a file | downloads: DIR/basename(URL); archives: the directory counts when it is trusted, inside a trusted directory or holds a trusted file; `tar` extraction is a single-dash cluster with `x`, `--extract`/`--get` or an old-style first operand, so `--exclude` no longer counts |

Remarks taken with the same change: the wrappers Claude Code strips before its
own rules (`timeout`, `nice`, `nohup`, `stdbuf`, `time`, `setsid`, `ionice`) are
unwrapped by rule 1 only; `sed` option clusters (`-Ei`, `-ri`, `-i.bak`); the
trusted set is executed from the installer's source text, never from a
bytecode cache; the set is loaded on every call, so a missing installer fails
even `true` closed (two tests). Declined: `rm -rf ~` and `/` stay with the
older rule; `~` as an extraction target is not denied; `perl -pi`, `sort -o`,
`gawk -i inplace`, `git config --global` and expanded literals in interpreter
code remain the documented residual class (`--check` detects, the Edit path
prevents).

One lexer defect found on the way is **not** fixed here: the inherited redirect
regex reads `2>&1` as `>` to a file named `&1`, which is what made the P4 merge
command (a commit message with the word "publish" and a `$(...)`) a rule-A
denial on main. Correcting the operator order allows that command, i.e.
relaxes the guard, which May reserved for phase 2; phase 3 stays additive and
rule 1 merely ignores `&N` targets. Recorded for P2.

Measured after the fix: the Verifier's 244 case strings 0 mismatches; 54 guard
and installer tests OK, full suite 485 OK (1 skipped); transcript replay of
11328 commands against main: 0 deny->allow, 5 allow->deny (the three -021
stand-in writes and the scratchpad heredoc as before, plus `cd ~/unity-distro
&& cat > .claude/skills/…/SKILL.md`, a write into the base `.claude/` that the
Write tool is for). Verification round 2 requested on the fixed commit.

## Verification round 2 (2026-10-09)

Verifier on cb21821: **FAIL (narrow)**. All five round-1 classes closed in
every listed spelling and near variants (round-1 strings 0 of 202 mismatched;
50 ordinary forms no new false positives; fail-closed and source-text import
hold against a renamed, broken, unreadable installer and hostile bytecode;
485 tests OK; 440 corpus commands unchanged against main). Three second-order
variants of the same forms remained:

| # | Finding | Fix |
|---|---------|-----|
| 1 | the directory of a leading `cd` did not reach heredoc bodies (`cd ~/.claude && bash <<EOF … > settings.json`) | bodies are walked once, each at the directory current at its owner; shell owners (`bash`, `sh`, …, also after `sudo`) are lexed as nested commands, interpreter owners through the write idioms |
| 2 | a leading shell word hid the `cd` or the writer (`{ cd ~/.claude; … }`, `if cp … ~/.claude/settings.json; then`) | `{ ! time if then elif else while until do` are stripped before rule 1 looks at the word |
| 3 | `su -c` was not a shell string (`sudo su -c 'echo x > /etc/sudoers.d/x'`) | `su` joins the `-c` shells |

Remarks taken: `pushd`/`popd` is a stack (`pushd … && popd && echo x >
settings.json` no longer over-denies); `~` and `/` are not directories one
extracts into (code now matches the round-1 text: `tar xf a.tar` in the home
root and `-C ~` are allowed, as `rm -rf ~` stays with the older rule);
`wget -qO-` is stdout and `-qO FILE` a target. Left as the stated residual:
`eval`, `xargs sh -c`, `find -exec sh -c`, `sh -c "$(…)"`, `bash script.sh`,
csh-style `>& file`, a `cd` in a pipeline or before `&` (over-approximated).

Measured after the fix: the Verifier's 372 case strings (rounds 1 and 2)
0 mismatches; full suite 485 OK (1 skipped; 132 phase-3 guard forms); transcript
replay of 11337 commands against main: 0 deny->allow, the same 5 allow->deny.
Verification round 3 requested.
