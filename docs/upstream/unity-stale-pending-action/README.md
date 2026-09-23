# Unity: stale pending end-session action - dead menu, and restart without a dialog

Status: **ready**, not sent. Third in the queue, after `nux-pcre2` and
`light-locker-session`.

## What this is

One cause, two symptoms, both on Ubuntu Unity 26.04 and both reachable from
the session menu. Mechanism in
[`../../research/shutdown-path/`](../../research/shutdown-path/README.md).

Confirming Unity's shutdown dialog makes `GnomeManager::Shutdown()` (or
`Reboot()`) record the action as pending and call
`org.gnome.SessionManager`. Unity expects the session manager to call
`EndSessionDialog.Open` back with the same action and then confirms it.
cinnamon-session never calls back - it shows its own dialog (issue #6). Cancel
that dialog and the action stays pending. Then:

1. **Known issue #2, the dead menu.** Pending `SHUTDOWN`: the indicator's
   `Open(2)` is neither `NONE` nor equal, the handler has no `else`, and every
   later request is dropped for the rest of the session.
2. **Restart on one click, no dialog - found while testing the fix for #2.**
   Pending `REBOOT` (the user chose "Перезагрузить" in Unity's dialog): the
   indicator's `Open(2)` matches it and is taken as the session manager's
   confirmation. Unity emits `ConfirmedReboot`, indicator-session calls
   logind's `Reboot` within milliseconds. Reproduced on the archive package
   (`08`). Not in the release notes; not filed anywhere we know of.

`Open(2)` for "Выключение..." is deliberate in indicator-session
(`my_power_off` uses `END_SESSION_TYPE_REBOOT`, "the latter adds lock & logout
options in Unity", `src/backend-dbus/actions.c:836`).

**The fix:** accept the confirmation only from the owner of
`org.gnome.SessionManager`, with the pending action. Anything else cancels the
stale action and is handled as a new request. Under gnome-session, which calls
back at once with the same action, nothing changes.

- `0001-GnomeSessionManager-only-the-session-manager-confirm.patch` - fix and
  two tests, one commit on `ubuntu/devel`, `Assisted-by` trailer, **no
  `Signed-off-by` yet** (May adds it). Branch `mr/stale-pending-action` in
  `packages/unity`, local only.
- Package: `unity 7.7.1+26.04.20260306-0ubuntu3+unity2`, in our aptly; branch
  `unity/resolute` at https://github.com/Ubuntu-Unity-LifeSupport/unity.
  `+unity1` carried a first version that fixed symptom 1 only - kept in the
  history as built, superseded.

## What it does not fix

The second dialog itself (#6). That needs cinnamon-session to fall back to
`org.gnome.Shell` (a feature request, not a regression - see research) or
Unity to call the no-dialog `RequestShutdown`. With #6 fixed the pending
action would never go stale; this fix is still right on its own, since
nothing guarantees a session manager calls back.

## Where it goes

**GitLab merge request** to https://gitlab.com/ubuntu-unity/unity/unity,
target branch **`ubuntu/devel`** (the active branch; `master` last moved
2023-02). The project has had two MRs ever (one merged, 2025-11); its
maintainers upload to the archive from `ubuntu/devel`.

**Severity.** Symptom 2 is probably the most serious of the 26.04 bugs we
know, and it is not on the release notes' list: a restart with no dialog,
losing unsaved work. For an SRU, `[Impact]` is one line. The queue order
(this after `light-locker-session`) was set before it was found - May to
decide whether it moves up.

Symptom 2 loses unsaved work. It may deserve its own Launchpad bug on
`unity` so it can be tracked for an SRU - May's call; draft that only if he
wants it.

Rule 0, done 2026-09-23:

- Launchpad (host session): nothing filed for #2. Nearest is LP #1521116, a
  different mechanism in `shutdown/SessionView.cpp`, Fix Released 2016.
- Symptom 2 on Launchpad (API search of unity, indicator-session and
  cinnamon-session for restart/shutdown titles with "without", "immediately",
  "no dialog" and similar, 2026-09-23): the only close match is LP #1414950,
  "Click on shutdown in the menu shuts down immediately" (14.10, 2015), closed
  Invalid by its reporter after a reinstall, no diagnosis. Same symptom, cause
  unknown, a different session manager - worth mentioning, not claiming.
  LP #1213220 is the power button, fixed in 2013.
- Symptom 2 on the web (host session, 2026-09-23): forums, Ask Ubuntu, Reddit,
  general search, by symptom, by version (23.10-26.04), by data loss and by
  the cancel-the-second-dialog sequence - **nothing**. Nearest: "Shutdown &
  Restart Not Working Properly" on the Ubuntu Unity forum (2020), about a
  ~30 s delay, unrelated. That forum could not be read in full:
  `foss.ubuntuunity.org` redirects to `www.`, which fails the TLS handshake -
  from builder too, so the site, not the host's environment.
- Context, not a duplicate: LP #1296814 (indicator-session, 2014, Fix
  Released) is where indicator-session learned to prefer Unity's own session
  API. The Unity-specific branches in `actions.c` are deliberate and old.
- GitLab issues (18) and MRs (2) of ubuntu-unity/unity: nothing on the
  session menu or end-session dialog. #13 and #18 checked, unrelated.
- `ubuntu/devel` HEAD is `6f01ccb7`, our base; the patch applies as is.

Draft MR text: [`merge-request.md`](merge-request.md).

## Re-check before sending

Written 2026-09-23. A deferred draft is re-verified, not re-read:

- [ ] Has `ubuntu/devel` moved? Does the patch still apply?
      `git fetch origin && git log 6f01ccb7..origin/ubuntu/devel`
- [ ] New MRs or issues about the session menu or shutdown dialog since?
- [ ] Web searched again for symptom 2 (last: 2026-09-23, nothing)?
- [ ] Has Ubuntu shipped a newer unity for resolute? `rmadison -u ubuntu unity`
- [ ] Do both symptoms still reproduce on the current `Clean-updated`
      snapshot with the archive package, and does the current `+unityN`
      still fix both?
- [ ] Does every evidence file still say which boot or run it came from?

## Evidence

| File | Shows |
|---|---|
| `01-unit-tests-unfixed.txt` | archive code: both new tests fail, 46 others pass |
| `02-unit-tests-first-fix.txt` | first fix (`+unity1`): the other-caller test still fails |
| `03-unit-tests-final-fix.txt` | final fix: 48/48 |
| `04-target-before-fix.png`, `05-...-dbus.txt` | archive unity, clean snapshot: symptom 1, no dialog at D and E; `Open` gets no answer |
| `06-target-first-fix.png`, `07-...-dbus.txt` | `+unity1`: symptom 1 fixed |
| `08-target-restart-archive.png`, `-dbus.txt` | archive unity: symptom 2, `ConfirmedReboot` then `login1.Reboot` 6 ms later |
| `09-target-restart-first-fix.png`, `-dbus.txt` | `+unity1`: symptom 2 still there - why the fix was revised |
| `10-target-final-fix.png`, `11-...-dbus.txt` | `+unity2`: symptom 1 fixed |
| `12-target-restart-final-fix.png`, `13-...-dbus.txt` | `+unity2`: symptom 2 fixed, dialog shown, no `login1.Reboot` |

All target runs are on snapshot `Clean-updated-2026-09-23`, rolled back by the
host at 22:26 and not rolled back again; between runs only the unity packages
changed (apt install/downgrade, reboot) and xdotool was added for all of
them. Each file names its boot.

Unit tests ran in a disposable chroot; Unity's suite does not build or run on
26.04 as shipped, for three reasons unrelated to this patch (C++17 for
googletest 1.17, GCC 15 in `tests/gmockvolume.c`, nux crashing under Xvfb for
want of VidMode). The workarounds are harness-only and listed in each evidence
header; scripts in `harness/`. `make-chroot.sh` is the recipe written down
after the fact - the run installed the X packages in a second step. See
DECISIONS 2026-09-23.
