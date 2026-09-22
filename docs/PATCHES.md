# Patch registry

Every patch we carry gets a row here. Status is one of `local`,
`sent upstream`, `merged`, `rejected`.

| Package | Patch file | What it does | Upstream | Status |
|---|---|---|---|---|
| _none yet_ | | | | |

## Rules

- Patches live as quilt series in `debian/patches/`, managed with `gbp pq`.
- A patched Ubuntu package gets a `+unity1` version suffix.
- When Ubuntu ships a new version of a patched package, rebase the series onto
  it rather than carrying a fork.
- Anything that could plausibly land upstream goes upstream first. A `local`
  row that has been sitting for a while is a smell.
