# indicator-keyboard: crash in g_variant_iter_new (LP #2166139)

Agent B, 2026-09-26, on `target2`: our indicator-keyboard `+unity2`,
accountsservice 23.13.9-8ubuntu5.2, GLib 2.88. target2 was rolled back to
`Clean-2` afterwards.

## Rule 0

- **LP #2166139** is an error-tracker bug (2026-09-02), with no comments and
  no fix. The error-tracker page needs a login, so only the title's
  signature was available:
  `g_bit_lock:g_variant_lock:g_variant_n_children:g_variant_iter_init:g_variant_iter_new`.
- **26.10.** `0ubuntu2` to `0ubuntu4` are only no-change rebuilds and a
  Build-Depends change; nothing is fixed there.
- **Ayatana.** ayatana-indicator-keyboard is a separate C implementation,
  not this Vala code.

## Cause

`g_variant_iter_new()`, `g_variant_iter_init()` and `g_variant_n_children()`
do not check for NULL. A NULL value crashes in `g_bit_lock` with exactly
this signature.

`act_user_get_input_sources()` is `(transfer none)` and returns the
`InputSources` property from AccountsService's D-Bus proxy cache. That cache
is empty while accounts-daemon is not on the bus, for instance while it
restarts, which is what a package upgrade does. During that time the user
object stays `is-loaded`, and the call returns NULL.

The service reads input sources only when it runs as the greeter's
indicator (`is_login_user()`: user `lightdm`), in two places:

- `migrate_input_sources()`;
- the greeter user's layout in `update_greeter_user()`.

Both iterate `user.input_sources` directly.

## Reproduced

`ik.sh` runs the service as `lightdm` on the greeter session's bus. On
target2 that is lightdm-gtk-greeter's bus: that greeter does not start the
indicator itself, and the service needs only the user name. It then
restarts accounts-daemon.

The service gets `notify::is-loaded` and runs
`migrate_input_sources()` → `g_variant_iter_new(NULL)`. The core dump,
symbolised with our dbgsym, shows:

```
#0 g_bit_lock_and_get   (GLib 2.88 name of g_bit_lock)
#1 g_variant_n_children
#2 g_variant_iter_init
#3 g_variant_iter_new
#4 indicator_keyboard_service_migrate_input_sources  main.c:2904
#5 ____lambda24_  (user.notify["is-loaded"] in migrate_keyboard_layouts)
```

It is preceded by `g_variant_ref: assertion 'value != NULL' failed`.

| | restart accounts-daemon, 3 runs |
|---|---|
| `+unity2` | SIGSEGV 3 of 3 (core dumps, kernel `segfault … libglib`) |
| `+unity3` | alive 3 of 3, no critical, no segfault; the service still owns its name and answers `org.gtk.Actions` |

A first `+unity3` build still logged
`lightdm_user_list_get_user_by_name: assertion 'username != NULL'`. The
user's name is NULL at that point too, so the final build also skips the
LightDM lookup for such a user.

## Fix: `+unity3`

In `packages/indicator-keyboard`, branch `unity/resolute`, commit `10eb95c`
(a git-ubuntu clone, no remote of ours):

- `lib/input-sources.vala`: `get_xkb_input_sources (Variant?)` returns the
  xkb layouts of an `aa{ss}` value in order, and nothing for NULL. Both
  places use it.
- `migrate_input_sources()` does not pass a NULL user name to LightDM.
- Test `xkb-input-sources`: NULL, an empty value, and a mixed value (xkb,
  ibus, xkb). It is listed in `tests/Makefile.am`.
  - The build in a clean `sbuild -d resolute` passes 10 of 10 tests.
  - Negative check: the same test against the function without the NULL
    check fails with `g_variant_ref: assertion 'value != NULL'` (built
    separately in the chroot).

`+unity3` is in aptly.
