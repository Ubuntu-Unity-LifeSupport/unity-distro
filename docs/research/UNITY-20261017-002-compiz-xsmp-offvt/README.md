# compiz: no XSMP answer while the session is switched away (UNITY-20261017-002)

Owner: agent B (target2). Scope set by C on 2026-10-17: code reading and passive evidence only, report the finding
and stop, no fix.

```yaml
task: UNITY-20261017-002
title: compiz does not answer XSMP QueryEndSession while the session is switched away (inactive seat)
package: compiz (1:0.9.14.2+25.10.20250930-0ubuntu3+unity3 live)
target_series: resolute
status: mechanism located to "compiz's main thread is blocked in a single-fd poll with no timeout while the session
  is switched away"; the call that blocks is not identified (needs a stack, i.e. ptrace or uprobes, outside this
  scope)
```

## Code reading

- compiz answers XSMP synchronously, inside its Glib main loop. The path is in `src/session.cpp`:
  - `iceNewConnection` adds the ICE fd with `screen->addWatchFd`;
  - `iceProcessMessages` calls `IceProcessMessages`;
  - `saveYourselfCallback` emits `sessionEvent` and then calls `SmcSaveYourselfDone` at once.
- The only plugin that handles `sessionEvent` is `session`, which saves window state with X property reads. Unity's
  profile loads it (`dconf read /org/compiz/profiles/unity/plugins/core/active-plugins` on target2). The blocking
  below starts before any SaveYourself, so that handler is not what blocks.
- compiz core has no logind, VT or "session active" logic.
- So without an answer there are two possibilities: the main loop is not dispatching the ICE fd, or cinnamon-session
  did not send the SaveYourself. `do_save_yourself` in `csm-xsmp-client.c`:403-450 can queue one behind an
  outstanding one.

## Measured (2026-10-17, target2; `probe.sh`, passive: /proc and ss, no ptrace)

target2: Clean-2 → live (InRelease 2026-10-17 07:48:02 UTC), cold Unity session, compiz-core
1:0.9.14.2+25.10.20250930-0ubuntu3+unity3, cinnamon-session 6.4.2-1+unity8. GL renderer "SVGA3D; build: RELEASE;
LLVM", direct rendering.

| when | compiz main thread (tid = pid 2778) | CPU ticks | ICE socket (inode 24254, peer: cinnamon-session's `/tmp/.ICE-unix/2161` 24255) |
|---|---|---|---|
| active (logs/01) | `ppoll`, wchan `poll_schedule_timeout` (the Glib loop) | 691 → 694 | Recv-Q 0 |
| switched away (`dm-tool switch-to-greeter`), +10 … +60 s | **`poll`**, the same wchan | 695, unchanged | Recv-Q 0 |
| switched away, `Logout(1)` (logs/02), +5 … +45 s | `poll` | 695 → 697 | **Recv-Q 16**: the SaveYourself is delivered and never read |

- The blocking call's arguments (`/proc/2778/task/2778/syscall`) are `poll(fds, nfds=1, timeout=-1)`. The thread made
  no voluntary context switch in 3 s.
- One fd and no timeout is how libxcb waits for a reply or a special event on the X connection, including Mesa's
  DRI3/Present waits. compiz has two connections to Xorg (fd 5 and fd 15).
- Which fd it is, and which call is waiting, is not visible without reading the stack (ptrace or uprobes), which is
  outside this task's scope.
- Another of compiz's unix sockets (inode 25308) accumulated 120 → 240 → 360 → 685 unread bytes while switched
  away. Its peer closed when the session ended, so the owner was a session process that exited. It was not
  identified.
- After the logout, cinnamon-session ended (the +unity8 grace). compiz never read its Die. It ended with the X server
  when lightdm closed the session: later, compiz, the session and Xorg 1150 were all gone.

## Answer to C's question

**The ICE message is waiting in compiz's socket; compiz's main thread is not in its event loop.** While the seat is
switched away it sits in a single-fd, infinite `poll`, a nested wait rather than the Glib loop's `ppoll`, and no
callback runs. cinnamon-session sent the SaveYourself: its queue path is not involved.

Not established, and the next step if C wants it: which X wait blocks. The two candidates by shape are an
`xcb_wait_for_reply` and a DRI3/Present special-event wait in the GL swap path. Telling them apart takes either a
user-space stack (ptrace, a gdb attach, or `eu-stack`) or uprobes on `xcb_wait_for_reply` and
`xcb_wait_for_special_event` with bpftrace, which our tracing notes already use.

## Before any fix: is it the VM's driver?

C, 2026-10-17: target2 renders with vmwgfx (SVGA3D) inside VirtualBox. Before anything is designed on compiz's side, it
has to be established whether the block is specific to that driver. For example, a DRI3/Present swap could wait for a
vblank that never comes while the VT is away. May's real hardware may behave differently. No fix code until then.

Next step, allowed by C, after the unity-gtk4-menu 0.14 target tests and not before: bpftrace uprobes on
`xcb_wait_for_reply` and `xcb_wait_for_special_event` (with a ustack if bpftrace resolves one) during a switch-away.
Passive, as in our tracing notes: no `-p`, `-B line`, no ptrace or eu-stack.

## Files

- `probe.sh` (`snap`, `idle`, `logout`)
- `logs/01-idle-switch.txt`, `logs/02-switched-logout.txt`
