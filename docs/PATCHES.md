# Patch registry

Every patch we carry or intend to send gets a row here.

Status moves `draft` -> `ready` -> `sent` -> `merged` / `rejected`. A row is
`ready` only when its directory under `docs/upstream/` is complete and the
checklist in `CONTRIBUTING-UPSTREAM.md` section 9 passes. `sent` is set by
whoever sends it, which is always May.

| Package | Patch / change | What it does | Upstream | Where | Status |
|---|---|---|---|---|---|
| nux | `migrate-to-libpcre2.patch` (0ubuntu13) | Not ours. Adds the `nux.pc.in` and `configure.ac` hunks the 0ubuntu12 upload left out, so `nux-4.0` resolves again and unity can build. Asking for an SRU into resolute. | LP: #2103918, LP: #2147013 | [`upstream/nux-pcre2/`](upstream/nux-pcre2/) | **ready** |
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
