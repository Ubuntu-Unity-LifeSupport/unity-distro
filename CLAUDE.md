# Working notes for Claude Code

You do not remember previous sessions. This repository is your memory.

## Every session

0. Read `docs/TWO-AGENTS.md`, `docs/COORDINATOR.md`, and
   `docs/ENGINEERING-PROCESS.md`; use `scripts/taskctl.py` for task-board
   changes. Never edit task rows by hand. Confirm whether you are A, B, or C;
   never infer a role from a stale session name. If you are A or B, use only your
   assigned desktop and build directory.
1. Run `ListAgents` and `scripts/agent_registry.py list`; register your
   explicitly assigned role with `scripts/agent_registry.py register`, then
   read the private `~/coordinator/TASKS.md` board and the last 20 lines of
   `~/AGENTS-LOG.md`. If you are A or B, read only your own
   `docs/status/A.md` or `docs/status/B.md`; if you are C, read
   `~/coordinator/PENDING-MAY.md` and your coordinator inbox. `docs/STATUS.md`
   is a dated summary, not a live task board.
2. Do not start package work without an assigned task ID and owner entry on
   the board. Follow the evidence gates in `docs/ENGINEERING-PROCESS.md`.
   Replies, external comments, and questions for May go through the coordinator.
3. A/B update only their own status file; C updates private coordinator notes
   and assignment fields on the task board. Append activity to `AGENTS-LOG.md`,
   record decisions and patches in their project records, then commit and push
   repository changes. A task is not complete until its terminal state and
   evidence are recorded.

If a session is interrupted, the private task board gives the current owner
and state; the agent status file gives its assigned machine/workspace state.

## Conventions

- Stage explicit paths and push non-forced branches with `scripts/safe_git.py`;
  do not use force push.
- Task branches reach `main` only through the merge procedure in
  `docs/ENGINEERING-PROCESS.md` section 10.
- Commits are atomic and in English: `pkg: short summary` for package changes,
  `docs:` / `build:` / `repo:` for this meta-repository.
- Every patch gets an entry in `docs/PATCHES.md`: package, file name, what it
  does, link to the upstream MR or bug, status.
- Patches are quilt series in `debian/patches/`, managed with `gbp pq`. Never
  fork an upstream tree wholesale.
- Patched Ubuntu packages use a `+unityN` suffix on the exact target-series
  base version, e.g. `1.7.0-1ubuntu1+unity1`. Check Debian ordering and the
  actual apt candidate with `package-version-safety` before building and
  publishing. Rebase when Ubuntu ships a security update.
- Builds happen in a clean chroot via `sbuild`. Never build in the builder's
  own system.
- Long builds go in `tmux` with a log file, never an interactive command.
- Communicate with May in Russian; write code, commits and documentation in
  English so the project stays open to outside contributors.

## Environment

- You are on `builder` (192.168.56.10, user `claude`, passwordless sudo).
- There are **two** test desktops, one per agent. Agent A uses `ssh target`
  (192.168.56.20, VM `target-desktop`, clean snapshot `Clean-updated-2026-09-23`).
  Agent B uses `ssh target2` (192.168.56.30, VM `target-desktop-2`, clean
  snapshot `Clean-2`). Both are user `mike` with passwordless sudo. Use only the
  one that is yours - see `docs/TWO-AGENTS.md`.
- Your eyes on target (agent B substitutes `target2` everywhere below):
  `ssh target 'DISPLAY=:0 gnome-screenshot -f /tmp/shot.png'`, then `scp` it
  back. When the guest does not answer ssh - during boot, at the greeter, or
  when the session is wedged - use the MCP `screenshot` tool instead: it
  captures the machine's screen from outside and does not need the guest at
  all. No sudo needed. Never `xwd -root` for the desktop - it
  misses the wallpaper under Compiz and invents bugs. See docs/DECISIONS.md.
- Before installing anything on target: `ssh target 'touch ~/.dirty'`. After a
  rollback the marker must be gone - that is how you verify it happened.
- **You drive the virtual machines yourself, through the `vbox` MCP server.**
  It runs on May's Windows host and reaches VirtualBox there: list and inspect
  machines, start and shut them down, manage snapshots and ISO media, type or
  send keys, take screenshots, and change network settings. The installed
  schema also exposes linked cloning, VM creation, and snapshot deletion.
  These operations are available for test work; follow the ownership rule
  below. There is no project VBox hook; the MCP server itself limits
  `allowed_vms` to `target-desktop`, `target-desktop-2`, and `oem-test`, with
  `builder-server` in `never_allowed`. No tool deletes a VM or virtual disk.
  For a restore or a suspected shared VBox/VBoxSVC failure, use
  `$vbox-recovery`.
  Read the server's own instructions - they carry the three traps that cost us
  a day each: a restore is never confirmed by `current_snapshot`, a snapshot is
  only meaningful on a powered-off machine, and the ISO comes out *before* you
  press Enter at "remove the installation medium".
- `guest_shutdown_ssh`, or `sudo systemctl poweroff` over your own ssh, is how
  these machines shut down cleanly. The ACPI power button does nothing here: a
  session inhibitor opens a dialog and waits for a human forever. `power_off_vm`
  is a hard power-off, available for these disposable test machines.

## Sending anything upstream

Read `docs/CONTRIBUTING-UPSTREAM.md` before preparing a bug report, an SRU, a
merge request or a reply to review. The three rules that matter most:

- **Nothing leaves this machine without May reading it and agreeing.** Every
  contribution goes out under his name. **The coordinator writes what goes out
  and reads what comes back** (`docs/COORDINATOR.md`); you supply the technical
  facts and check the draft for them.
- **`Signed-off-by:` is his alone** - it signs the DCO, which is a legal
  statement. Mark AI involvement with `Assisted-by: LLM <model>` instead.
- **Prove the bug before writing code**: reproduce it in a clean environment,
  check it is not already fixed, check nobody filed it, and test the exact
  scenario from the description rather than one that resembles it.

**Pre-Implementation Gate: Existing-Fix Discovery.** Before implementation,
but after basic issue identification and exact reproduction, determine whether
the issue is already fixed. The assigned physical agent owns the investigation
and final decision. The owner checks the installed system and exact
reproduction directly; result-heavy history, archive, tracker, and web searches
are delegated as described below.

**Delegate broad searches to isolated subagents, not into the task owner's
context.** A sweep of bug trackers, changelogs or upstream repositories returns
pages of detail of which three lines matter. Give a subagent a bounded question
and source list; take back a concise finding with links, exact versions/commits,
and unresolved gaps - not raw pages or search dumps. Do the same for wide log
trawls, package-wide greps, and unfamiliar source trees. Run independent
sweeps in parallel when useful. The owner remains responsible for checking the
findings, recording them, and deciding the task. A skill is a procedure for
the current session; it does not launch a subagent by itself. Physical agents
A and B keep their assigned VMs, and coordinator C remains a separate
physical session; subagents do not receive persistent roles or VM ownership.
When direct network access is available, delegated subagents can query tracker
APIs or the web. If subagents are unavailable, keep result-heavy discovery
`BLOCKED` or `UNKNOWN`; do not move the broad search into the task owner's
context. The initial search budget is twenty minutes. Record sources and
results in the task evidence; if the search is incomplete, mark `UNKNOWN` and
stop before package code until May authorizes more investigation or defers it.

**The last step of the Pre-Implementation Gate, the one we keep missing: has a newer version already
fixed it?** A bug tracker says whether someone knows about it; a release says
whether someone fixed it. Check the next Ubuntu series (`rmadison <pkg>`),
Debian, and the upstream releases, not just the archive we build against.

If a fix exists in a newer version, the question is no longer "how do I patch
this" but **"what does it cost to carry that version instead"** - and that is
measured, not guessed:

1. Build the newer source in a clean 26.04 chroot (`sbuild -d resolute`).
2. It builds and its dependencies resolve from the 26.04 archive: carrying the
   version is normally cheaper than carrying a patch, and more honest - the fix
   is upstream's, not ours.
3. It fails: the failure names the price, usually a newer library 26.04 does
   not have. Then patching the archive version is the right answer, and you can
   say why.

Write which of the two you chose, and the measurement behind it, in
`docs/DECISIONS.md`. **Both answers are legitimate; skipping the question is
not.** We got this wrong on `gtk-nocsd`: two upstream commits were backported
onto a March snapshot while release 4.0 already contained them and 26.10
shipped 4.8.

There is a third outcome, and `cinnamon-session` is it: **a newer release
exists and builds, but does not contain our fix.** 6.6.4 builds in resolute in
46 s, yet none of our five fixes is in it - so taking it would add a whole
series of unrelated changes and still leave us carrying the patches. The patch
stays, for that reason and not for a dependency one.

That case also carries a trap worth naming. 6.6.4 first *looked* impossible:
it build-depends on `libcinnamon-desktop-dev (>= 6.6)`, which 26.04 does not
have. But that bound is the Debian packager's decision, not the code's -
upstream's `meson.build` asks for `>= 6.0.0`. **A versioned bound in
`debian/control` is a claim, not a measurement**; check what the build system
actually requires before believing the price.

**The same question one level up: does this belong in an existing component
rather than a new one of ours?** Before starting a library, a daemon or a
module, ask whether the function belongs inside something that already does
this job. Two preloaded libraries hooking the same symbols, two daemons
watching the same bus, two modules patching the same toolkit - each is a
maintenance burden we chose, and each duplicates edge cases the other has
already solved. Sometimes a new component really is right; then say against
which existing one you weighed it, and why it lost. This has caught us three times
in one day, and once the answer was a package already installed on the machine
we were working on.

Run the checklist in section 9 of that document in full before sending
anything. Any "no" stops the submission.

Use the fixed outcomes and evidence card in `docs/ENGINEERING-PROCESS.md` for
the Pre-Implementation Gate. The 20-minute search budget limits research time; an incomplete search
is `UNKNOWN`, not `NOT_FIXED`. If a newer release may contain the fix, measure
its target-series build/dependencies and unrelated changes before choosing it
over a backport. A versioned build dependency is a claim to check against the
build system, not a measurement by itself.

## Do not

- Rewrite history or force-push in repositories May maintains.
- Put repositories on VirtualBox shared folders - NTFS breaks permissions,
  symlinks and case sensitivity.
