# lightdm: session-child's SIGTERM handler calls exit() (LP #2168421)

Third-party report ([LP #2168421](https://bugs.launchpad.net/bugs/2168421),
[canonical/lightdm#484](https://github.com/canonical/lightdm/issues/484),
Markus Kuhn, 2026-09-24, Xubuntu 24.04), found by the stack-health survey.
Upstream: issue open, no reply, no fix; resolute's 1.32.0 has the same code.
Fixed here in lightdm `1.32.0-6ubuntu4+unity1` (in aptly,
https://github.com/Ubuntu-Unity-LifeSupport/lightdm), one quilt patch:
`_exit()` instead of `exit()` in `signal_cb()` of `src/session-child.c`.

## The bug

`signal_cb()` passes SIGTERM to the session's child, or when there is none
calls `exit()`. `exit()` is not async-signal-safe: it runs the ELF
destructors, and some free memory. If the signal lands while the thread
holds the malloc arena lock, `free()` waits on that lock forever; logind's
stop of the greeter scope then waits out systemd's 90 s stop timeout and the
user's session waits with it. The reporter captured the stuck process:
`signal_cb` → `exit` → `_dl_fini` → libtasn1/libgnutls → `free` → lock wait
on `main_arena`, interrupting `malloc_consolidate`.

## Does it hit Ubuntu Unity 26.04 as installed?

**Not as measured on target.** The greeter's session-child there loads no
library whose destructors free memory through the arena: its maps have
libpam, libaudit, libsystemd, libnss_systemd - no libgnutls, no libtasn1 (the
reporter's PAM stack pulled those in). A deterministic model on the real
binary (`runs/ld-sigterm.sh`: log out, attach to the greeter's session-child,
set `child_pid` to 0 so the handler takes the `exit()` branch, take
`main_arena.mutex`, send SIGTERM) exited in 0.05 s (`runs/stock3.txt`), and
still did with tcache disabled (`GLIBC_TUNABLES=glibc.malloc.tcache_count=0`,
`runs/stock4.txt`). It becomes real as soon as a PAM module or NSS plugin
brings in such a library (sssd, krb5, fingerprint and smartcard stacks are
candidates, not checked).

## Reproduced and fixed, with the reporter's conditions

The same model with libgnutls loaded into lightdm (`LD_PRELOAD`, tcache off,
temporary drop-in on lightdm.service, removed afterwards):

- stock `1.32.0-6ubuntu4`: session-child **still alive 10 s after SIGTERM**,
  stuck in `__lll_lock_wait_private (main_arena)` ← `_int_free_chunk` ←
  libgnutls ← `_dl_call_fini` ← `_dl_fini` ← `__run_exit_handlers` ← `exit` ←
  `signal_cb` (`session-child.c:168`) - the reporter's stack
  (`runs/stock5.txt`, `runs/stock5-stuck-backtrace.txt`);
- `+unity1`: session-child exited 0.034 s after SIGTERM (`runs/fixed5.txt`).

`child_pid` is a static gdb would not take the address of; the script reads
its offset from the disassembly of session-child's `signal_cb` (it moves
between builds). A normal logout/login cycle with `+unity1` and no drop-in:
clean.

Also seen: target's greeter is lightdm-gtk-greeter, not unity-greeter.
