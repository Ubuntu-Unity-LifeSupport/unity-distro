# UNITY-20260929-005 - does +unity4 lose update_login_layout() on unchanged passes?

```yaml
task_id: UNITY-20260929-005
task_kind: package (a regression check of UNITY-20260928-014's +unity4, before publication)
package: indicator-keyboard
target_series: resolute
issue: follow-up from the UNITY-20260928-014 Verifier remark
status: NOT_REPRODUCED
source_version: 0.0.0+19.10.20240924-0ubuntu1+unity4 (b/UNITY-20260928-014 5d6a8c5) vs stock 0ubuntu1
binary_version: both installed in turn on target2 (Clean-2 + ~/.dirty)
existing_fix_result: not_applicable
```

## Question

+unity4 writes `sources` and `current` in `migrate_input_sources()` only when
they differ from the stored values. `update_login_layout()`, which moves the
greeter's X layout through `LightDM.set_layout()` and needs `DISPLAY`, runs
only from the `changed` handlers of those two keys (main.vala:1180-1195). If
dconf emitted `changed` for a same-value write, stock would have re-applied
the layout on every pass and +unity4 would not.

## Measured

- FACT (logs/01, `same-value.py`, GSettings with the dconf backend as the
  service uses it, 3 runs): a same-value write emits **no** `changed` for a key
  that already holds an explicit value (`sources` 3/3, `current` in runs 2-3,
  a repeated different value 3/3). The only same-value write that emitted
  was the first write of `current` equal to its schema default while the key
  was unset (run 1): writing it made the key explicit.
- FACT (logs/02 stock, logs/03 +unity4). lightdm-gtk-greeter, the image's
  default greeter, was used with autologin off. The greeter's service was
  started by hand with `DISPLAY=:0`, as in UNITY-20260927-024 logs/05,
  because lightdm-gtk-greeter does not load the keyboard indicator by
  default (`indicators=~host;~spacer;~session;~language;~a11y;~clock;~power;`).
  Two cases were run:
  - `fresh`: keys reset;
  - `cur1`: sources `[gb, us]` and current 1 explicit.

  Stock and +unity4 give identical results: X layout `gb` before and after,
  settings `[gb, us]` / 0.

## Why +unity4 cannot differ here

The unchanged-write skip applies in three situations:

1. Keys explicit and unchanged: dconf emitted nothing for stock either, so
   `update_login_layout()` did not run there.
2. Keys unset (first start): `sources` defaults to `[]`, so any non-empty
   union differs and is written, and `handle_changed_sources()` calls
   `update_login_layout()` in the same pass. Skipping the `current`
   materialisation only avoids a second, identical call.
3. The reload window: stock's `[]` / 4294967295 writes called
   `update_login_layout()` with `current >= n_sources`, which is a no-op.
   The recovery re-applied the same layout; +unity4 writes the recovery only
   when it differs, and then the handler runs.

`update_greeter_user()` still writes `current` unconditionally; +unity4 does
not change it.

Result: NOT_REPRODUCED - no regression. There is no change to
UNITY-20260928-014.

Limit: `set_layout` calls were not counted directly on stock (no stock
dbgsym on the builder); the conclusion rests on logs/01 and the code path.
