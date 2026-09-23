# Patch registry

Every patch we carry or intend to send gets a row here.

Status moves `draft` -> `ready` -> `sent` -> `merged` / `rejected`. A row is
`ready` only when its directory under `docs/upstream/` is complete and the
checklist in `CONTRIBUTING-UPSTREAM.md` section 9 passes. `sent` is set by
whoever sends it, which is always May.

| Package | Patch / change | What it does | Upstream | Where | Status |
|---|---|---|---|---|---|
| nux | `migrate-to-libpcre2.patch` (0ubuntu13) | Not ours. Adds the `nux.pc.in` and `configure.ac` hunks the 0ubuntu12 upload left out, so `nux-4.0` resolves again and unity can build. Asking for an SRU into resolute. | LP: #2103918, LP: #2147013 | [`upstream/nux-pcre2/`](upstream/nux-pcre2/) | **ready** |
| light-locker | `0003-Follow-the-user-s-display-session-outside-a-session-.patch`, `0004-Find-the-LightDM-session-when-XDG_SESSION_PATH-is-mi.patch` | Stops the abort on every login under Ubuntu Unity 26.04. light-locker runs under cinnamon-session, a systemd user service, so logind cannot map its PID to a session and `XDG_SESSION_PATH` is not inherited. Falls back to logind's display session and to LightDM's session list over D-Bus. Ours; 1.8.0-3ubuntu4+unity2. | LP: #2038808 | [`upstream/light-locker-session/`](upstream/light-locker-session/) | **ready** |
| nux | `Validator::Validate` discards its match result | On the Windows branch the function returns `Acceptable` from both sides of its `if`. Real, small, and deliberately kept out of the PCRE2 submission so it does not blur a first contact. | none yet | — | draft |

## Rules

- Patches live as quilt series in `debian/patches/`, managed with `gbp pq`.
- A patched Ubuntu package gets a `+unity1` version suffix. A package we build
  unmodified from upstream git keeps the upstream version, as `nux` 0ubuntu13
  does - we are not the author and should not claim to be.
- When Ubuntu ships a new version of a patched package, rebase the series onto
  it rather than carrying a fork.
- Anything that could plausibly land upstream goes upstream first. A `local`
  row sitting for a long time is a smell.
- Findings made in passing become their own row, never a passenger on someone
  else's patch.
