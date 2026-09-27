# UNITY-20260927-056: apt_view.py sometimes does not recognise its model Release

Owner: agent B (builder; the board lists `target-desktop-2`). Reported by the
coordinator: `AptViewIntegrationTest.test_full_view_selects_snapshot_binaries`
(UNITY-20260927-048) fails now and then with `[] != ['<model>_Release']` (1 of
9 discover runs before 051, 2 of 7 after). If the cause is in apt_view.py,
publish_aptly.py's switch would sometimes refuse falsely (fail closed).

```yaml
task_id: UNITY-20260927-056
package: unity-distro scripts/apt_view.py
target_series: resolute
issue: local - flaky model-Release detection in apt_view.py
status: REPRODUCED
issue_search_result: NOT_FOUND  # project-local script
source_version: origin/main e9f3dfc
binary_version: n/a
source_commit: e9f3dfc
observed: >
  logs/01-reproduction.txt: the test fails 20 of 20 with TMPDIR set to a
  directory whose name contains "_", and 4 of 20 with a plain TMPDIR.
  logs/02-apt-escaping.txt: for a file: repository at .../a_b/model/ apt names
  the list files ..._a%5fb_model_._Release; apt_view.py compared them with
  ..._a_b_model.
expected: >
  The model repository's Release is recognised on every run, whatever the
  temporary directory is called.
reproduction: logs/01, logs/02
root_cause: >
  apt_view.py marks a Release as the model's when its list file name starts
  with the model directory's path with "/" replaced by "_". apt's list file
  names escape more than "/": "_" becomes "%5f" (URItoFileName quoting). The
  model directory is under tempfile.TemporaryDirectory(), whose random
  8-character suffix is drawn from [a-z0-9_] (37 characters), so it contains
  "_" with probability 1-(36/37)^8 = 0.197; a TMPDIR containing "_" makes it
  certain.
root_cause_mechanism: >
  the tool re-derives apt's private list-file naming and gets it wrong for
  "_"; the unmarked model Release then keeps its per-run file name and date,
  so compare_views() in publish_aptly.py reports it missing from the other
  view and refuses the switch.
root_cause_evidence: docs/research/UNITY-20260927-056-model-release/logs/02-apt-escaping.txt
invariant: >
  apt_view.py identifies its own model repository's Release independently of
  how apt names list files and of the temporary path.
existing_fix_result: NOT_FIXED
candidate_approaches:
  - mark the model Release by content the tool controls: apt-ftparchive
    writes a Description field with a per-run nonce ("apt_view model
    <nonce>"); a Release in the lists dir is the model's iff it carries that
    exact Description - chosen
  - ask apt for the mapping (`apt-get indextargets`, REPO_URI -> FILENAME of
    the Packages target, then swap "Packages" for "Release") - rejected: still
    relies on apt's list naming convention between index and Release files
  - reimplement apt's URItoFileName quoting - rejected: duplicates apt
    internals that can change between apt versions
  - create the temporary directory without "_" (hex name) - rejected: hides
    the symptom; TMPDIR itself or any other quoted character (~, =, @, ...)
    would break it again
chosen_approach: content marker (Description with a per-run nonce)
why_chosen: >
  the tool generates the model Release, so it can recognise it by content
  without any assumption about apt's file naming; Description is a standard
  Release field that apt ignores for pinning (Origin, Label, Suite, Codename
  and the per-run file name are unaffected).
code_risks:
  ownership_lifetime: not_applicable
  callbacks_cancellation: not_applicable
  threading_reentrancy: not_applicable
  ABI_API_file_list: checked  # view JSON unchanged: the model entry is still {"file": "<model>_Release", "model": true}
design_challenger_required: false
design_review_result: NOT_REQUIRED
architectural_task: false
correct_layer: >
  apt_view.py creates the model repository and must recognise it; the test
  was right to fail, the bug is in the tool.
defensive_workaround_rejected: >
  Making compare_views() ignore missing Releases, or the test tolerant of an
  unmarked model entry, would hide the misclassification.
unknowns: []
```

## Reproduction

`logs/01-reproduction.txt`: the integration test 20 times with `TMPDIR` set to
a directory named `with_underscore` (20 of 20 fail) and to `plain` (4 of 20
fail, the expected ~20%). `logs/02-apt-escaping.txt`: a `file:` repository at
`…/a_b/model/`; apt's list files are `…_a%5fb_model_._Packages` and
`…_a%5fb_model_._Release`, the tool's prefix was `…_a_b_model`.

Deterministic regression test (`test_model_release_recognised_whatever_the_temp_path`):
runs the full view with `TMPDIR` named `tmp_with_underscore` and
`tmp~tilde=equals@at`; against the unmodified tool both fail with
`[] != ['<model>_Release']` (`logs/03-test-before-fix.txt`) - the other
characters apt quotes break it the same way as `_`.

## Implementation

`scripts/apt_view.py`: write the model Release with
`APT::FTPArchive::Release::Description=apt_view model <nonce>` (a random
hex nonce per run) and mark a Release in the lists directory as the model's
iff its Description is exactly that; the file-name comparison goes.

## Result

- `scripts/apt_view.py` (+12/-5): the model Release carries
  `Description: apt_view model <32 hex nonce>`; a Release is the model's iff
  its Description equals this run's marker; the Description is not copied into
  the view. The view format is unchanged.
- The new test first had one wrong assertion of its own: it required no `%`
  in any Release file name, but the fixture archive also lives under the
  test's temporary directory, whose name can contain `_` (quoted `%5f`) - the
  same ~20% flakiness, in the test. It now checks what matters: no Release of
  the model repository is left unmarked.
- `logs/04-after-fix.txt`: the original test 20 of 20 with a `TMPDIR`
  containing `_` and 20 of 20 with a plain one; `logs/05-after-test-fix.txt`:
  the full suite 20 of 20 (default TMPDIR) and 10 of 10 (TMPDIR with `_`),
  36 tests each.
- `logs/06-real-archive.txt`: two full views against the real archive with a
  `TMPDIR` containing `_`: the model Release is marked, `compare_views()`
  between them is OK.

No retries, timeouts or tolerated failures were added; the cause is the
file-name matching, removed.
