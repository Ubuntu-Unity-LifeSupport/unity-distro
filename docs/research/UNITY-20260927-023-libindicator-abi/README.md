# UNITY-20260927-023: libindicator +unity2 exports an internal type

Owner: agent B (target2). This comes from the legacy review (B-L21). The
coordinator's question is about libindicator +unity2, whose Ayatana wrapper
adds an exported symbol, `indicator_ng_ayatana_menu_get_type` (40 -> 41
exports). Is this a legitimate ABI extension, to be declared in symbols and
shlibs, or should it be removed or hidden? A fix will stop at publication,
which is expected. libindicator is B's package (`package-patches-b`).

```yaml
task_id: UNITY-20260927-023
package: libindicator (libindicator3-7)
target_series: resolute
issue: local - unintended export in our +unity2
status: REPRODUCED
issue_search_result: NOT_FOUND  # our own change; upstream is dead (DECISIONS 2026-09-25)
source_version: 16.10.0+18.04.20180321.1-0ubuntu8+unity2 (our aptly; archive 0ubuntu8)
binary_version: libindicator3-7 0ubuntu8+unity2
observed: >
  logs/01: libindicator3.so.7 exports 40 symbols in the archive's 0ubuntu8 and
  in +unity1 (identical lists), and 41 in +unity2. The extra one is
  indicator_ng_ayatana_menu_get_type. The GTK2 flavour (libindicator.so.7) is
  unchanged at 34 because indicator-ng is built for GTK3 only.
  libindicator3-dev +unity2 declares the symbol in no header. The package has
  no symbols file, and its shlibs is static:
  `libindicator3 7 libindicator3-7 (>= 0.4.90)`.
expected: >
  The library's exported ABI is exactly its public API. An internal helper
  type of indicator-ng.c is not exported.
reproduction: logs/01-exported-symbols.txt
root_cause: >
  67bfe16 defines the wrapper type with G_DEFINE_TYPE, which emits a
  non-static <name>_get_type() function (gtype.h
  _G_DEFINE_TYPE_EXTENDED_BEGIN_PRE: no storage class, no attributes).
  libindicator/Makefile.am:78 exports with -export-symbols-regex "^[^_].*",
  so every external name without a leading underscore is exported. The
  type's other functions are static.
root_cause_mechanism: G_DEFINE_TYPE's get_type has external linkage and matches the library's export regex
root_cause_evidence: libindicator/indicator-ng.c:367 at 67bfe16 (371 after the fix); libindicator/Makefile.am:78; logs/01
invariant: >
  libindicator3-7's exported symbols equal its public headers' API: the 40 of
  the archive package
existing_fix_result: NOT_FIXED
candidate_approaches:
  - (A) a static prior declaration `static GType
    indicator_ng_ayatana_menu_get_type (void);` before G_DEFINE_TYPE in
    indicator-ng.c, +unity3. The definition inherits internal linkage (C11
    6.2.2). Design review measured it with GCC 15.2: the function is not in
    `nm -D`, and no global symbol is left in the static .a either - chosen
  - (A') G_GNUC_INTERNAL on the declaration - hides it from the shared
    library, but leaves a global hidden symbol in the shipped
    libindicator3.a and does not say that the type is private
  - (B) keep it and make it a legitimate ABI extension: a public header, a
    symbols file, and a shlibs bump to (>= 0ubuntu8+unity2)
  - (C) leave it as is
  - (D) restrict the whole library's exports (a version script or
    -export-symbols-regex)
chosen_approach: A
why_chosen: >
  The type is a private detail of indicator-ng.c (a GMenuModel wrapper used
  only by indicator_ng_menu_changed). Nothing can use it, since no header
  declares it. Hiding it restores the archive's ABI exactly, with one
  static declaration in the file that owns the type, which also states that
  the type is private.
alternatives_rejected:
  - B would make an implementation detail permanent public ABI of a library
    upstream no longer maintains. Every later change to the wrapper would
    then be an ABI question, and our packages would diverge from the
    archive's ABI for no consumer.
  - C leaves an export that the static shlibs does not track. Any binary that
    linked it would get a dependency of `libindicator3-7 (>= 0.4.90)`, which
    older versions without the symbol satisfy; DPKG_GENSYMBOLS_CHECK_LEVEL
    does not help without a symbols file.
  - D (narrowing the existing -export-symbols-regex, or a version script)
    would touch every exported name to fix one. The risk of dropping a real
    API symbol is not worth it when the defect is one declaration.
  - a symbols file that lists the archive's 40 symbols would make
    DPKG_GENSYMBOLS_CHECK_LEVEL=4 (already set in debian/rules) fail the
    build on any future accidental export. That is a guard for the
    invariant and worth having, but it changes how reverse dependencies get
    their versioned dependencies. Recommended as a separate follow-up, not
    part of +unity3
design_challenger_required: true
design_review_result: APPROVE  # round 1 REVISE: mechanism static instead of G_GNUC_INTERNAL, card facts; adopted
architectural_task: false
correct_layer: >
  indicator-ng.c, the file that defines the type and is its only user
defensive_workaround_rejected: >
  a symbols file listing the symbol would record the mistake as ABI instead
  of fixing it
code_risks:
  ownership_lifetime: checked  # wrapper lifetime unchanged (review of 67bfe16 below)
  callbacks_cancellation: checked  # items-changed handler disconnected in finalize
  threading_reentrancy: not_applicable
  ABI_API_file_list: checked  # goal: 40 exports, as the archive
unknowns:
  - removing an exported symbol is formally an ABI break. It was published
    in +unity2 only (since 2026-09-26), with no header. logs/02 and the
    design review scanned all 270 .debs in our pool (read-only). The string
    occurs only in libindicator3-7 +unity2 itself and in the static
    libindicator3.a of libindicator3-dev +unity2. None of the 22 packages
    depending on libindicator3-7 imports it or contains it (unity,
    unity-services, libindicator3-tools, unity-greeter, indicator-printers,
    ...). The only residual exposure is a third-party dlsym by name, which
    is implausible for an undocumented internal type
acceptance: >
  After the +unity3 build, nm -D --defined-only of libindicator3.so.7 must
  equal the archive's 40 symbols exactly, and libindicator.so.7 (GTK2) must
  stay at 34. The messaging menu must still work in the Unity session on
  target2.
```

## Review of the +unity2 wrapper (design)

The layer was decided in DECISIONS 2026-09-26 ("Messaging menu under Unity:
show Ayatana's"). Reading 67bfe16 again:

- **Attributes.** Each value from `g_menu_attribute_iter_get_next` is a new
  reference. It is owned by the table, and the table frees it with
  `g_variant_unref`. The added x-canonical-type is ref-sunk.
- **Links.** Each linked model is wrapped. The iterator's reference is
  dropped after wrapping, and the table owns the wrapper.
- **Signals.** `items-changed` is forwarded with the same positions. The
  handler holds a plain pointer to the wrapper and is disconnected in
  finalize before the base is unreffed.
- **Existing types.** An existing x-canonical-type is not overwritten, and
  an unknown Ayatana type gets no x-canonical-type. Without this guard GTK
  would drop such an item.
- **Cost.** Links are wrapped anew on every `get_item_links` call. GTK's
  menu tracker asks once per item and after `items-changed`, so the cost is
  one small object per submenu per change.

- **Both attributes on one item.** If an item carries both x-canonical-type
  and x-ayatana-type, the base's own x-canonical-type wins in either order,
  because a later g_hash_table_insert replaces the earlier value. This is
  harmless and arguably correct.

No defect found besides the export.

## Design review

Round 1: REVISE. The mechanism is a static declaration rather than
G_GNUC_INTERNAL (measured by the challenger). The card's claim that there
was no export list was wrong: the export regex exists. The pool scan is now
evidence, and the symbols-file guard is kept as a separate follow-up. All
points were adopted and the approach is unchanged, so the result is
APPROVE.

## Result

- **Package** (`packages/libindicator`, branch b/UNITY-20260927-023, commit
  f8fa299; `patches/`): +unity3 adds `static GType
  indicator_ng_ayatana_menu_get_type (void);` before G_DEFINE_TYPE, with a
  comment. The changelog trailer comes from `date -u`.
- **Build.** `scripts/build_sbuild.py` in a clean resolute sbuild
  (`logs/03-build.txt`, `build/…-build-manifest.json`).
- **Acceptance** (`logs/04-exports-unity3.txt`):
  - libindicator3.so.7 exports 40 symbols, identical to the archive's
    0ubuntu8;
  - libindicator.so.7 (GTK2) exports 34, unchanged;
  - in libindicator3.a every wrapper symbol is local (`t`/`b`), and get_type
    is inlined (only `get_type_once` is left, local);
  - shlibs is unchanged.
- **target2** (Clean-2, then our repository and +unity3 from a local file
  repository, no aptly; `logs/05`, `logs/06`, `target.sh`):
  - libindicator3-7 +unity3 is installed and unity-panel-service maps it;
  - the installed library exports 40 symbols, none of them Ayatana's;
  - the panel lists org.ayatana.indicator.messages;
  - with the messaging-menu test client registered, the envelope turns
    "new";
  - its menu shows the application, "Inbox" with the IDO count bubble
    (which needs the wrapper's type mapping) and Clear.
- **Crash report on the guest.** A light-locker crash report is dated
  11:35 guest time. It was written during the first boot of the restored
  Clean-2, before the install, so it is unrelated.
- **Not done: the gate.** The version check and the release gate need the
  package in an aptly snapshot, and publication is stopped (047). Nothing
  was written to aptly.

## Verification

Independent verifier (read-only; no aptly, sudo or VMs): **PASS**, finding
PATCH_CORRECT, review status REVIEWED. It re-measured every package and ABI
claim itself:

- the archive's 0ubuntu8, +unity1 and +unity3 export the same 40 symbols;
- GTK2 exports 34 in all three versions;
- no wrapper global is left in libindicator3.a;
- between +unity2 and +unity3 only the dropped export differs: the 198
  imports, NEEDED, Depends, shlibs and the file lists of all six packages
  are identical;
- the version order holds and the changelog trailer is UTC;
- the pool scan was re-run with the same result.

A test program compiled with `-Wall -Wextra -Wpedantic` gives no warning
for the pattern.

**Limit stated by the verifier.** The Unity-session claims rest on B's
target run. Not every observation of it is in the saved logs:

- logs/06's scripted phase shows the installed +unity3 (40 exports, none
  Ayatana's) mapped by unity-panel-service;
- its panel-entry grep printed nothing, because the script queried the
  wrong bus name;
- the Sync output listing `org.ayatana.indicator.messages` (before and
  with the client) came from interactive commands, quoted in logs/06's
  note;
- the envelope and menu screenshots are on the Windows host.

The change alters only symbol linkage, so this does not affect the verdict.
The build runs no test suite: the build shows only that it compiles.

## Status

BLOCKED at the publication gate: the version check and gate need the
package in an aptly snapshot (047). Follow-up proposed: a symbols file for
libindicator3-7 with the archive's 40 symbols, so that any future
accidental export fails the build.

## Gated rebuild and target test of this build (2026-10-02)

- **Source.** `f8fa299` on `Ubuntu-Unity-LifeSupport/libindicator`, branch
  `b/UNITY-20260927-023` (on top of the published +unity2, 67bfe16), pushed.
- **Gated build** on the pinned chroot 20260929T201245Z (UNITY-20260929-016):
  `build-gated/UNITY-20260927-023-libindicator-build-manifest.json`, PASS,
  with the archive's `libindicator_16.10.0+18.04.20180321.1.orig.tar.gz`
  (sha256 0029ac3a…, as the resolute Sources index).
- **Payload against the tested build** (logs/08): the six .debs have the same
  control fields, file lists and exported symbols, and every file inside is
  byte-identical (0 of 34 differ); libindicator3.so.7.0.0 is the tested
  library, byte for byte.
- **Target test, mode this_build** (logs/07), on the UNITY-20260927-029/-028
  session of target2 (Clean-2, our repository, gated hud): the gated .debs
  installed from a file repository; libindicator3-7 +unity3 is the manifest's
  .deb (sha256 caac08af…); indicator-common came with it. libindicator7
  (GTK2), the -dev packages and -tools are not installed in the session
  (nothing depends on them), so the release record's `target_test.debs`
  names the two installed .debs; the other four are covered by the payload
  comparison. After a reboot into the auto-login Unity session,
  no drop-in, no test environment:
  - the installed library (f07e26fa…, the gated .deb's file) exports 40
    symbols, none Ayatana's: the acceptance;
  - unity-panel-service maps it, no "(deleted)" mapping, and Sync on
    `com.canonical.Unity.Panel.Service.Desktop` lists
    org.ayatana.indicator.messages with the other indicators;
  - with `mmclient.py` registered, the entry's icon is
    indicator-messages-new and the panel shows the envelope with the "new"
    dot (screenshot target-desktop-2-20261002-192510.png on the host).
- **Clock:** NTPSynchronized=yes on both phases (UNITY-20260929-022; the
  before/after is in the -029 card).

## Known gaps before the gate

| gap | state |
|---|---|
| a symbols file, so that an accidental export fails the build | task UNITY-20260928-006 |
| removing the +unity2 export is formally an ABI break | closed with a reason: the pool scan (logs/02, 270 .debs) found no consumer; +unity2 was published 2026-09-26 only, with no header; a third-party dlsym by name of an undocumented type is not plausible |
| the Verifier's limit: panel entry grep printed nothing (wrong bus name), interactive observations not in the logs | measured before the gate on this build, logs/07: the right bus name, the entry listed, the client and the "new" icon recorded |
| the build runs no test suite | closed with a reason: the acceptance is measured on the built binaries (exports), and the session check runs the library in unity-panel-service |
| wrapper cost: links wrapped anew on each `get_item_links` | closed with a reason: one small object per submenu per change (design review); not a defect of this task |

## Verifier round on the gated build (2026-10-02): PASS

The independent Verifier re-measured the manifest against the chroot
sidecar and the tarball itself, the source tree (f8fa299, tree 26b45002…),
the sbuild log, all 14 artifacts (orig tarball 0029ac3a…), the ABI on the
gated .debs (libindicator3.so.7.0.0: 40 exports, 0 Ayatana; libindicator.so.7:
34), the payload comparison (identical to logs/08), the target record
(library f07e26fa… is the .deb's file, panel entry listed, NTP
synchronised) and the gaps table against the unknowns and the earlier
verifier's limits, and the evidence (PASS, REVIEWED, APPROVE).

Remarks, applied: the "no test suite" limit now has a row in the table.
The panel Sync listing and the client's icon in logs/07 are transcribed
notes; the raw gdbus output is not stored, and the screenshot is on the
host. The script's path for the indicator-datetime binary is corrected.

## Publication (2026-10-02)

- db backup `~/backups/repo-023-20261002T175914Z`; repo add of the gated
  build, 10 records (387 to 397); snapshot `unity-resolute-20260927-023` =
  the live `unity-resolute-20260927-028` (hud +unity3) + those 10 (logs/09);
  full apt view SAFE (gate/); peer notice ACK; release gate
  (gate/release-gate.json, tested_build this_build on libindicator3-7 and
  indicator-common). C checked the gate; May confirmed the switch in B's
  session.
- `publish_aptly.py` switched `./resolute` to `unity-resolute-20260927-023`
  at 18:02:44 UTC; write-once record
  `~/coordinator/publish-records/UNITY-20260927-023.json`.

## Target verification of the publication (2026-10-02)

Result: **PASS** (logs/10). target2 was rolled back to Clean-2 (checked
inside: no `~/.dirty`, no `~/b029`, libindicator3-7 0ubuntu8; NTP
synchronised) and upgraded from our repository by the normal path, no file
repository (unattended-upgrades was let finish first).

- apt's candidate for libindicator3-7 is +unity3 from 8080; the .debs apt
  fetched are the gated ones (caac08af…, 08384eb2…); `dpkg -V` is clean.
- After a reboot into the auto-login session: libindicator3.so.7.0.0 is the
  gated .deb's file (f07e26fa…), exports 40 symbols, none Ayatana's;
  unity-panel-service maps it with no deleted library.
- The panel lists org.ayatana.indicator.messages with the other indicators;
  with `mmclient.py` registered the entry's icon is indicator-messages-new.
- target2 is left on this state (dirty); the UNITY-20260927-026 check rolls
  it back.
