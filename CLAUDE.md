# Working notes for Claude Code

You do not remember previous sessions. This repository is your memory.

## Every session

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
- `ssh target` reaches the test desktop (192.168.56.20, user `mike`,
  passwordless sudo). Its snapshot is called `Clean`, capital C.
- Your eyes on target: `ssh target 'DISPLAY=:0 gnome-screenshot -f /tmp/shot.png'`,
  then `scp` it back. No sudo needed. Never `xwd -root` for the desktop - it
  misses the wallpaper under Compiz and invents bugs. See docs/DECISIONS.md.
- Before installing anything on target: `ssh target 'touch ~/.dirty'`. After a
  rollback the marker must be gone - that is how you verify it happened.
- Snapshot rollback goes through the host session. See `UNITY-DISTRO-HANDOFF.md`
  Appendix A.

## Do not

- Rewrite history or force-push in repositories May maintains.
- Put repositories on VirtualBox shared folders - NTFS breaks permissions,
  symlinks and case sensitivity.
- Start Layer B or C before Layer A produces results.
