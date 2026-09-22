# Patch registry

Every patch we carry gets a row here. Status is one of `local`,
`sent upstream`, `merged`, `rejected`.

| Package | Patch file | What it does | Upstream | Status |
|---|---|---|---|---|
| nux | `migrate-to-libpcre2.patch` | Ports `Validator` from PCRE1 to PCRE2 and updates `nux.pc.in` and `configure.ac` to require `libpcre2-8`. Not ours - written upstream, complete in `-0ubuntu13`, never uploaded to resolute. | LP: #2103918, LP: #2147013 | upstream, unreleased in resolute |

## Rules

- Patches live as quilt series in `debian/patches/`, managed with `gbp pq`.
- A patched Ubuntu package gets a `+unity1` version suffix.
- When Ubuntu ships a new version of a patched package, rebase the series onto
  it rather than carrying a fork.
- Anything that could plausibly land upstream goes upstream first. A `local`
  row that has been sitting for a while is a smell.
