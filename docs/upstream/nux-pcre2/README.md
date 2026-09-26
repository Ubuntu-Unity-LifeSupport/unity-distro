# nux: PCRE2 metadata fix for resolute

Status: **ready**, not sent.

## What this is

Not our patch. `debian/patches/migrate-to-libpcre2.patch` was written upstream
by Tomasz Jeruzalski and c4pp4. We are asking for an existing, already-released
revision to reach 26.04.

The half-fix is the whole story: 0ubuntu12, which resolute carries, ports the
C++ to PCRE2 but leaves `nux.pc.in` and `configure.ac` declaring `libpcre`.
0ubuntu13 adds those two hunks. Without it nothing that build-depends on
`libnux-4.0-dev` can configure in 26.04, which in practice means unity cannot
be rebuilt at all.

## Where it goes

- **Launchpad**, bug LP: #2147013, source package `nux`.
  1. Nominate the bug for the **Resolute** series. There is no Resolute task
     today, so the bug is invisible to the SRU team.
  2. Post `bug-report.md` as a comment.
  3. Post `sru.md` as the SRU template comment.
- Worth copying to **Tomasz Jeruzalski**, who is active in the nux changelog
  and authored the patch, and mentioning **Timo Aaltonen**, who removed
  0ubuntu13 from proposed, since he will know why.
- Nothing goes to `gitlab.com/ubuntu-unity` for this one. The fix is packaging,
  not upstream code.

## Re-check before sending

This draft was written on 2026-09-22. Run all four:

- [ ] Has resolute received a newer `nux` than 0ubuntu12? `apt-cache policy nux`
- [ ] Is 0ubuntu13 or later sitting in resolute-proposed now?
- [ ] Has anyone opened a Resolute task or a separate bug for this meanwhile?
- [ ] Does the reproducer still fail? Two commands, see
      `evidence/06-minimal-reproducer.txt`

If any of the first three has changed, the text needs rewriting before it goes
anywhere.

**Re-check 2026-09-26 (agent B), point 4.** The reproducer still fails:
- Where: a clean resolute chroot (sbuild's base tarball, Ubuntu archive
  only).
- What: `apt install libnux-4.0-dev` gives `0ubuntu12`; then
  `pkg-config --print-errors --exists nux-4.0` prints `Package 'libpcre',
  required by 'nux-4.0', not found`, exit 1.

Seen on the way, for points 1-2 (`rmadison`):
- resolute has only `0ubuntu12`, nothing in -updates or -proposed;
- 26.10 has `0ubuntu13`, and `0ubuntu15` is in its -proposed.

Point 3 was not re-checked.

## Evidence

| File | Shows |
|---|---|
| `01-unity-fails-against-0ubuntu12.txt` | configure failure in a clean chroot |
| `02-nux-0ubuntu13-builds.txt` | 0ubuntu13 builds from git, 478 s |
| `03-pc-requires-before-after.txt` | the Requires line, both versions, and that libpcre3-dev is gone |
| `04-unity-builds-against-0ubuntu13.txt` | unity builds, 372 s, seven binaries |
| `05-runtime-proof-on-target.txt` | compiz maps libpcre2-8 and no PCRE1 on a live 26.04 desktop |
| `06-minimal-reproducer.txt` | two-command reproduction, no build needed |
| `07-reverse-dependencies.txt` | unity is the only reverse build-dependency |
| `08-clean-end-to-end.txt` | installed with one apt command on a clean, fully updated desktop, session verified after reboot |

Desktop screenshots are in `../../screenshots/`. Crash dumps collected during
testing are in `~/evidence/` on builder; none of them belongs to this change,
see DECISIONS.md.

## The patch itself

Upstream commit `3c56e89` in `gitlab.com/ubuntu-unity/unity/nux`, branch
`ubuntu/devel`, which is revision 0ubuntu13. Our local build of it is what was
tested. No local modification.
