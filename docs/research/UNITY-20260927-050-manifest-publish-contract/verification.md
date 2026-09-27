# UNITY-20260927-050 independent verification

Verifier: ephemeral `adversarial-verifier` subagent (read-only; no VM, no
edits, no `aptly publish`), 2026-09-27, on `b/UNITY-20260927-050` at `2a31111`.

- verification_result: **PASS** (finding: PATCH_CORRECT)
- review_status: **INDEPENDENTLY_REPRODUCED** for the snapshot-expectation
  logic, old and new; no end-to-end `publish_aptly.py` run (needs 046-048).

What it ran: the script tests (8/8); `repro_old.py` (the unmodified block
misjudges 6 of 8 cases as recorded); its own packages - epoch `2:3.4-1` with
`Architecture: all`, a binNMU `.deb` and `.ddeb` with `Source: ep (2:3.4-1)`, a
`.udeb` without Package-Type, a corrupt `.deb` - through
`snapshot_expectations()` (correct names; udeb rejected by its suffix; corrupt
file rejected with dpkg-deb's error; a candidate without the epoch, a
`kind: None` artifact and a manifest without binaries rejected); a scratch
aptly 1.6.2 listing `ep_2:3.4-1_all`, `ep-bin_2:3.4-1+b2_amd64`,
`ep-bin-dbgsym_2:3.4-1+b2_amd64`, `ep-u_2:3.4-1_amd64` - epoch and `_all`
always present.

Evidence it cited: dpkg-gencontrol:361-367 (dpkg 1.23.7) writes `Source:
name` when the name differs and adds ` (version)` when the version differs,
so `binary_source()` follows dpkg; the real `-dbgsym.ddeb` of calamares parses
correctly; `/srv/aptly/public/dists/resolute` has only `main/binary-amd64`;
`main()` keeps the hash loop and uses the result at the snapshot check.

Nits, and what was done after the review:
1. dpkg-gencontrol:350-351 strips `Package-Type` from real udebs, so the
   fixture setting it was unrealistic - the fixture no longer sets it; the
   suffix check rejects it (tests 8/8, `logs/02b-old-publisher-realistic-udeb.txt`:
   the old block still accepts it).
2. `Source: ep(2:3.4-1)` without a space is misread but fails closed; dpkg
   never writes it - left as is.
3. ENGINEERING-PROCESS said Source must match the manifest record - reworded:
   Package/Version/Architecture match the record, Source decides the owning
   source.
4. A `.pyc` committed in d8ee10e and removed in 2a31111 stays in the branch
   history (no force push).

Remaining unknowns (for the coordinator): a binary for an architecture the
publication does not carry (not amd64/all) would reach the snapshot but not
the published index, like a udeb - no rule yet, and none of our builds makes
one (publication configuration, 047); `version_safety.py` still equates the
binary and source version (048); source-full `.changes` would list `.tar.*`
files, rejected loudly as an unknown kind (051).
