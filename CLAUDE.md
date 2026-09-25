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
where you looked - found or not - and carry on.

**The last step of rule 0, the one we keep missing: has a newer version already
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
shipped 4.8. The reverse also happens - `cinnamon-session` 6.6 needs a
`libcinnamon-desktop` that 26.04 does not have, so there the patch is right.

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

## Do not

- Rewrite history or force-push in repositories May maintains.
- Put repositories on VirtualBox shared folders - NTFS breaks permissions,
  symlinks and case sensitivity.
- Start Layer B or C before Layer A produces results.
