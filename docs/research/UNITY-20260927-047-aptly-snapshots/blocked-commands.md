# UNITY-20260927-047: the exact commands the guard blocks

`.claude/hooks/command_guard.py` refuses any `aptly` command whose first
argument is `publish`. These are the only such commands the plan needs. Every
other step (snapshot create, backups, comparisons, client captures) is not
blocked.

Scratch configuration for Phase R: `S=/tmp/claude-1000/-home-claude/fa14e5f5-9fa9-405c-8373-3873520d3c73/scratchpad/aptly047`,
`$S/aptly.conf` = the live config values (`aptly config show`) with
`rootDir: $S/root`; nothing under `/srv/aptly` is written.

## Phase R (scratch, `-config=$S/aptly.conf`)

```sh
aptly -config=$S/aptly.conf publish repo -distribution=resolute -architectures=amd64 -gpg-key=7BF3F77FC27B152C -batch unity-resolute    # R2
aptly -config=$S/aptly.conf publish show resolute                                                                                      # R2/R6/R7 checks
aptly -config=$S/aptly.conf publish show resolute candidate                                                                            # R5 check
aptly -config=$S/aptly.conf publish list                                                                                               # R8b step 5 (read-only)
aptly -config=$S/aptly.conf publish switch resolute unity-resolute-20260927-047                                                        # R3 (expected to be refused)
aptly -config=$S/aptly.conf publish snapshot -distribution=resolute -architectures=amd64 -gpg-key=7BF3F77FC27B152C -batch unity-resolute-20260927-047 candidate   # R5
aptly -config=$S/aptly.conf publish drop resolute                                                                                      # R6
aptly -config=$S/aptly.conf publish snapshot -distribution=resolute -architectures=amd64 -origin=". resolute" -label=". resolute" -gpg-key=7BF3F77FC27B152C -batch unity-resolute-20260927-047   # R6
aptly -config=$S/aptly.conf publish switch resolute unity-resolute-20260927-047b                                                       # R7 (as publish_aptly.py runs it)
aptly -config=$S/aptly.conf publish drop resolute                                                                                      # R8a
aptly -config=$S/aptly.conf publish repo -distribution=resolute -architectures=amd64 -gpg-key=7BF3F77FC27B152C -batch unity-resolute    # R8a
aptly -config=$S/aptly.conf publish drop resolute candidate                                                                            # R9
```

## Phase L (live `/srv/aptly`, only after Phase R passed and the go)

```sh
aptly publish snapshot -distribution=resolute -architectures=amd64 -gpg-key=7BF3F77FC27B152C -batch unity-resolute-20260927-047 candidate   # L2
aptly publish show resolute candidate                                                                                                  # L2 check
aptly publish drop resolute                                                                                                            # L3 (outage starts)
aptly publish snapshot -distribution=resolute -architectures=amd64 -origin=". resolute" -label=". resolute" -gpg-key=7BF3F77FC27B152C -batch unity-resolute-20260927-047   # L3 (outage ends)
aptly publish show resolute                                                                                                            # L4 check
aptly publish drop resolute candidate                                                                                                  # L6
# rollback (L5a), only on a failed check:
aptly publish drop resolute
aptly publish repo -distribution=resolute -architectures=amd64 -gpg-key=7BF3F77FC27B152C -batch unity-resolute
```

Rollback L5b (restore procedure in README.md: move `db/` and `public/` aside,
`cp -a` the backup into empty paths, sha256 compare) uses no aptly command
except the read-only checks:

```sh
aptly repo show unity-resolute        # not blocked
aptly publish list                    # blocked (read-only); needed for R8b/L5b step 5
```
