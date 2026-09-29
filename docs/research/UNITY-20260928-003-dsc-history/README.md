# UNITY-20260928-003: reconstructed history for 13 published packages

Follow-up of UNITY-20260927-046: 13 packages in our aptly had no git history
of ours, so `publish_aptly.py` had no remote to check `source_commit` against.
Agent A, 2026-09-28.

**Authorization.** In 046 May chose a separate task for these packages. After
the histories were prepared locally, May confirmed directly, in A's session:
create all 13 public repositories and push. May's conditions:
- the history is a **reconstructed history**, not a recovered original git
  history, and every repository says so with its provenance;
- xorg-server records separately that there is no source in aptly and that
  the source came from the local `.dsc`;
- no invented commits, authorship, dates or historical links;
- existing evidence and research stay.

## What each repository holds

Branch `unity/resolute`, exactly two commits, made by
`tools/import-dsc-history.sh`:

1. `<pkg> <archive version> (resolute archive)` - the target-series archive
   source as `dpkg-source -x` extracts it, unchanged.
2. `<pkg> <our version> (published in our aptly)` - our published source,
   extracted the same way, replacing the tree entirely. The diff between the
   two commits is our change.

- 3.0 (quilt) sources are extracted with `--skip-patches` (patches unapplied,
  no `.pc`), as git-ubuntu does.
- Both commit messages list the source files with their sha256.
- Both messages end with a `RECONSTRUCTED HISTORY` paragraph: made on
  2026-09-28 from source packages; author ("Ubuntu Unity Life Support") and
  date are those of the import, not of the release; the package's real
  history is in `debian/changelog`; provenance points here.
- Each repository's GitHub description says "RECONSTRUCTED history from
  source packages".
- No file was added to the trees.

## Checks (FACT, 2026-09-28)

- **Our sources**: taken from aptly's internal pool
  (`/srv/aptly/pool/<sha256 path>`; the published pool has only binaries).
  Every file's sha256 equals the `Checksums-Sha256` that `aptly package show`
  records.
- **Archive bases**: `pull-lp-source -d <pkg> <version>`. Each base equals the
  resolute archive version (`rmadison`) and is the base of our `+unityN`. All
  orig tarballs of ours are byte-identical to the archive's.
- **Tree check**: after each commit, `git archive HEAD` was compared with the
  extracted tree (`diff -r --no-dereference`): 26/26 equal. Empty directories
  cannot be held by git and were counted: hud 1, unity-scope-devhelp 1,
  -gnote 1, -tomboy 1, -zotero 1.
- **Debdiff cross-check**: the file list of commit 1 -> 2 equals B's debdiff
  in `docs/package-patches-b/debdiff/` for hud, ayatana-indicator-messages,
  overlay-scrollbar, ubuntu-unity-meta and unity-lens-files. The scopes have
  no debdiff there.
- **GitHub**: `git ls-remote` tip equals the local second commit for all 13;
  all are public with default branch `unity/resolute`
  (`repos-and-commits.txt`).

## Exceptions

- **unity-lens-files**: the source in aptly is **not** the source the
  published binaries were built from. That source was deleted after the build
  (2026-09-26 14:07Z); the aptly one was regenerated from the debdiff at
  16:26Z (`research/legacy-migration-20260927/B.md`, B-L27). Its orig is
  identical to the archive's and its content matches the debdiff, but byte
  identity with the built source cannot be checked. This is stated in the
  commit.
- **xorg-server**: there is **no xorg-server source in our aptly**, only
  binaries. The second commit is the local `.dsc` in `~/work/a/xorg/cl`
  (written 2026-09-26 14:22:01Z); the build log shows sbuild started from it
  at 14:22:08Z (`research/xorg-versioning/`). The base `1ubuntu1.3` exists
  only in resolute-proposed (release has `1ubuntu1`, updates `1ubuntu1.2`).
  The copy downloaded from Launchpad is byte-identical to the local one. The
  commit title says "(source of our published binaries)", not "published in
  our aptly", and the repository description repeats both facts.

## Repositories and commits

| Repository | archive commit | ours (branch tip) |
|---|---|---|
| hud | `c31857b029b7f88f895d7c3a88e9d11396fe6220` | `9e9e097bd4e1b6bb648a5cb4cb97131440a25806` |
| ayatana-indicator-messages | `1cf2fc4246771b53a723959b7366432d1da44768` | `3000bdb38506732ae33980531edefcfb6f0ba874` |
| unity-lens-files | `08993dc0afdd0192a357153b2a002063613e5e45` | `171235be102c3dc49be7a715acf022ed8147dbc8` |
| unity-scope-calculator | `2b6c36484e756b48c3e0c75383af159e0ca0fb00` | `9567cfa63bc90e0b26d7526efc336fa53506d61c` |
| unity-scope-devhelp | `215cbb4569752e92532d62ff2b498181aec093d0` | `fbc606c24bf9ca94e53fc254d51c14e5ca5a641d` |
| unity-scope-gnote | `d2d29d53190daf96c28a79354cb993e0289721fa` | `078ad7a15ecd0a1ecaf4b1e11b0b1c14705bf21a` |
| unity-scope-manpages | `156696b61c63b067009aba17712734cb0c98ab76` | `f8554cd0289a6be799dcce77defc28cacefdfd2b` |
| unity-scope-tomboy | `12f8143994046bdd0d03faba63560713b2346914` | `f8b1ab5f8a40739b5f9541c99d15f90a3414a7c1` |
| unity-scope-virtualbox | `dfb204f2e52750840252656156a56b5b4f4dff23` | `733c49d9e9b1b51810079017f6938ae0c9d69586` |
| unity-scope-zotero | `159a4d593cf6131380747c6889d7a59ba67c1299` | `87820f4a13fac826382edaa8eae8f046ad6d3587` |
| overlay-scrollbar | `801d7cff3778bedb70032084e51b78ea815cd303` | `6fc02048a705ef2e16e14e41cc93234a732478da` |
| ubuntu-unity-meta | `175959ad6813558edeabaf88949083ea13aede33` | `aa507637e01b03c4625f6f19888fdd2cb21440ed` |
| xorg-server | `82a69533a922d02a9837d429715eb03a3454e2d6` | `2ac6784be522445ffa0fd3dc3e3f6658e00809b7` |

Repositories: `https://github.com/Ubuntu-Unity-LifeSupport/<name>`. Local
clones: `~/work/a/003/repo/`. Sources used: `~/work/a/003/archive/`,
`~/work/a/003/ours/`.

With 046 the organisation now has a repository for all 38 sources in aptly.
