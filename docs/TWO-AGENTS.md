# Two agents on one builder

Since 2026-09-24 the builder hosts **two Claude Code sessions at once**, each
driving its own test desktop. This file says what is yours, what is shared, and
how not to destroy the other agent's work. Read it before your first command.

## Which agent am I?

May tells you at the start of the session: **"ты агент A"** or **"ты агент B"**.

If he did not say, **ask him**. Do not guess and do not assume you are alone -
both sessions run as user `claude` in the same home directory, so nothing in
your environment distinguishes you. Guessing wrong means two agents writing to
one test machine and to one build directory.

Announce yourself in `~/AGENTS-LOG.md` as soon as you know (see below).

## What is yours alone

| | Agent A | Agent B |
|---|---|---|
| Test desktop | `ssh target` - 192.168.56.20 | `ssh target2` - 192.168.56.30 |
| VM name for rollback | `target-desktop` | `target-desktop-2` |
| Clean snapshot | `Clean-updated-2026-09-23` | `Clean-2` |
| Build directory | `~/work/a` | `~/work/b` |
| Status file | `docs/status/A.md` | `docs/status/B.md` |

**Never touch the other agent's test desktop.** A rollback there destroys an
experiment that is running right now, and the other agent will report the
resulting nonsense as a measurement.

The two desktops are the same image. `target` still answers to the hostname
`mike-virtualbox`; `target2` answers `target2`. When a command's output confuses
you, check `hostname` before believing it.

`target2` also has a spare way in, for when host-only networking breaks:
`ssh -p 2222 mike@192.168.56.1` from the builder reaches it through NAT.

## What is shared

- `~/unity-distro` - **one git working tree, used by both of you.** There is no
  isolation here: if you rewrite a file the other agent edited a minute ago,
  his work is gone and git will not notice, because it only sees your version.
- `/srv/aptly` - one package repository. aptly locks its database, so a
  concurrent call fails loudly rather than corrupting anything. On a lock
  error, wait and retry - do not work around it.
- `~/.cache/sbuild/resolute-amd64.tar.zst` - the chroot tarball. sbuild runs in
  unshare mode and unpacks its own copy per build, so parallel builds are safe.
  Read-only for you: never rebuild the tarball while the other agent is building.
- `~/HOST-INBOX.md` - the channel from the host session. Messages are addressed
  `To: A`, `To: B` or `To: both`. Read the ones addressed to you; the rest are
  context, not instructions.

## The rule that prevents lost work

For any file under `~/unity-distro` that is not yours alone:

```
git pull --rebase   →   edit   →   git commit   →   git push
```

Run those four steps back to back, without doing anything else in between. The
window in which you can silently overwrite the other agent shrinks to seconds.

Two more habits that matter:

- **Append, do not rewrite.** Adding an entry to `docs/DECISIONS.md` or
  `docs/PATCHES.md` is safe. Regenerating the whole file destroys entries you
  never read.
- **If `git push` is rejected**, the other agent pushed first. `git pull
  --rebase` and push again. Never `--force`.

`docs/STATUS.md` stays the shared overview, but write your own running state to
`docs/status/A.md` or `docs/status/B.md`. Nobody edits the other's status file.

## The busy log

`~/AGENTS-LOG.md` is outside git and answers one question: *what is the other
agent doing right now?* git shows finished work; this shows work in flight.

Append one line - never open the file in an editor, never rewrite it:

```
echo "$(date +%F\ %H:%M) A START build cinnamon-session 6.4.2 on target" >> ~/AGENTS-LOG.md
echo "$(date +%F\ %H:%M) A DONE  build ok, 48/48 tests" >> ~/AGENTS-LOG.md
```

Log before you start a package build, before a snapshot rollback, before an
aptly publish, and when you finish. Read the tail of it before you pick up work:

```
tail -20 ~/AGENTS-LOG.md
```

**Before starting work on a package, check that the other agent has not already
claimed it.** Two agents patching one source package produce two versions of the
truth and a merge conflict in `debian/patches`.

## When you and the other agent disagree

You will sometimes read a measurement or a conclusion from the other agent that
contradicts yours. Do not quietly overwrite it and do not assume he is wrong.
Write your measurement, say plainly which of the two is which, and let May
decide. The one thing that must never happen is a document that silently
contains one agent's conclusion and the other agent's evidence.

## Host resources

The builder has 4 vCPU and 7.3 GB RAM, of which under 1 GB was in use during a
real build. Memory is not the constraint. Builds currently run single-threaded -
if `parallel=` is set in `DEB_BUILD_OPTIONS`, expect both of you to feel it when
you build at the same time. That is acceptable; it is not a reason to serialise.
