# Working notes for Claude Code

You do not remember previous sessions. This repository is your memory.

## Every session

0. **You are not the only agent on this machine.** Read `docs/TWO-AGENTS.md`
   and confirm with May whether you are agent A or agent B before touching
   anything. Register yourself in `~/AGENTS.md` so the other agent can address
   you, run `ListAgents` to see who is around, and `tail -20 ~/AGENTS-LOG.md`
   to see what he is doing. **Before you take any task, message him and ask
   whether he has already taken it.**
1. Read `docs/STATUS.md` first - it says what is in flight and what is broken.
2. Do the work.
3. Update `docs/STATUS.md`, record any decision in `docs/DECISIONS.md`, and
   `git push`. **Nothing that is not pushed exists** - the builder VM is the
   most fragile part of this setup.

If a session is interrupted, `STATUS.md` must be enough to resume from.

## Conventions

- Commits are atomic and in English: `pkg: short summary` for package changes,
  `docs:` / `build:` / `repo:` for this meta-repository.
- Every patch gets an entry in `docs/PATCHES.md`: package, file name, what it
  does, link to the upstream MR or bug, status.
- Patches are quilt series in `debian/patches/`, managed with `gbp pq`. Never
  fork an upstream tree wholesale.
- Patched Ubuntu packages take a `+unity1` version suffix, e.g.
  `1.7.0-1ubuntu1+unity1`. Rebase them when Ubuntu ships a security update.
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
  `ssh target 'DISPLAY=:0 gnome-screenshot -f /tmp/shot.png'`,
  then `scp` it back. No sudo needed. Never `xwd -root` for the desktop - it
  misses the wallpaper under Compiz and invents bugs. See docs/DECISIONS.md.
- Before installing anything on target: `ssh target 'touch ~/.dirty'`. After a
  rollback the marker must be gone - that is how you verify it happened.
- Snapshot rollback goes through the host session. See `UNITY-DISTRO-HANDOFF.md`
  Appendix A.

## Sending anything upstream

Read `docs/CONTRIBUTING-UPSTREAM.md` before preparing a bug report, an SRU, a
merge request or a reply to review. The three rules that matter most:

- **Nothing leaves this machine without May reading it and agreeing.** Every
  contribution goes out under his name.
- **`Signed-off-by:` is his alone** - it signs the DCO, which is a legal
  statement. Mark AI involvement with `Assisted-by: LLM <model>` instead.
- **Prove the bug before writing code**: reproduce it in a clean environment,
  check it is not already fixed, check nobody filed it, and test the exact
  scenario from the description rather than one that resembles it.

**Rule 0, which fires before all of them: before writing a line of code for a
problem, find out whether it is already solved.** Search outward from where you
are - the installed system first (`apt-cache`, `dpkg -S`, `ldd`, and `Task:` in
the metadata), then the package's history, then bug trackers, then the web.
**You have direct internet access - use it yourself.** `curl` reaches
api.launchpad.net, gitlab.gnome.org, gitlab.com and api.github.com from this
machine (verified 2026-09-25), and `gh` is authenticated. Query the trackers'
APIs directly rather than asking the host session; a web search tool, if you
have one, is faster still. Ask the host only for something you genuinely
cannot reach.

**Run searches in subagents, not in your own context.** A sweep of bug
trackers, changelogs or upstream repositories returns pages of detail of which
three lines matter. Spawn a subagent, tell it exactly what to answer, and take
back the conclusion with its links - not the raw pages. The same applies to any
wide read: log trawls, package-wide greps, surveying a source tree you do not
yet know. Your own context is for the work; delegate the digging. Run
independent sweeps as several subagents at once rather than one after another. Twenty minutes, then record in `docs/DECISIONS.md`
where you looked - found or not - and carry on. This has caught us three times
in one day, and once the answer was a package already installed on the machine
we were working on.

Run the checklist in section 9 of that document in full before sending
anything. Any "no" stops the submission.

## Do not

- Rewrite history or force-push in repositories May maintains.
- Put repositories on VirtualBox shared folders - NTFS breaks permissions,
  symlinks and case sensitivity.
- Start Layer B or C before Layer A produces results.
