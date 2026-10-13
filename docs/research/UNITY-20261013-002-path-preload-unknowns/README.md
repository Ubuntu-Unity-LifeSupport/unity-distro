# The path-form preload: 32-bit processes, sandboxes, and tools that rebuild the environment (UNITY-20261013-002)

Owner: agent B (target2). Observation and documentation record; no package change.

```yaml
task: UNITY-20261013-002
from: UNITY-20261012-005 known gaps ("biarch lib32, Steam pressure-vessel and tools that re-source the environment
      unquoted are UNKNOWN")
value: LD_PRELOAD=/usr/$LIB/libunity-gtk4-menu.so.0:/usr/$LIB/libgtk-nocsd.so.0 (literal $LIB), from gtk-nocsd
       4.8-1+unity4 and unity-gtk4-menu 0.10; the earlier releases used the bare names
       libunity-gtk4-menu.so.0:libgtk-nocsd.so.0
result: no case where the path form is worse for the user than the bare names; no task needed (details below)
```

## Where it ran

**Stand:** target2, restored to Clean-2, then the live archive (Release Date 2026-10-13 01:41:51 UTC) and a
full-upgrade (logs/01; logs/01a is the first attempt, refused by an unattended-upgrades lock). Packages:
- libgtk-nocsd0 4.8-1+unity4, libunity-gtk4-menu0 0.10;
- gcc-multilib, which brings libc6-i386 (the biarch lib32 C library);
- for part 1, libc6:i386 (multiarch). i386 is already a foreign architecture in Clean-2.

**The runs:**
- **Part 1** ran in the first boot after the upgrade. Its Unity session failed at start, which is
  UNITY-20261013-007. The 32-bit measurements run over ssh and do not need the session.
- **Part 3 and the snap check** ran in the next cold boot, after the UNITY-20261013-007 recurrence check. That
  session was up, and its starting value was the path form in the user manager and in compiz (logs/04, first
  lines).
- **The packages there:** the stand still carried the packages above, plus the dbgsym packages of
  cinnamon-session and light-locker, so it was not a clean live.

**The earlier run:** logs/04a is an earlier envtools run in the failed session. It is invalid: no compiz was
running, so the starting value was empty. It is kept for the record.

**Afterwards:** target2 was restored to Clean-2 and confirmed inside (logs/07).

## What the user sees

| case | with the path form | with the bare names | log |
|---|---|---|---|
| 64-bit process | both libraries load, no message | the same | logs/02 |
| 32-bit process, biarch loader (`/usr/lib32/ld-linux.so.2`, `$LIB` = `lib32`) | 2 lines per exec image: `ERROR: ld.so: object '/usr/$LIB/libgtk-nocsd.so.0' from LD_PRELOAD cannot be preloaded (cannot open shared object file): ignored.`, and the same for libunity-gtk4-menu. `$LIB` is printed unexpanded. The program runs. | the same count; the line names `'libgtk-nocsd.so.0'` | logs/02, logs/03 |
| 32-bit process, multiarch loader (`/lib/ld-linux.so.2` from libc6:i386, `$LIB` = `lib/i386-linux-gnu`) | the same 2 lines per exec image | the same count | logs/03 |
| strict snap (`hello-world.env`, snapd 2.76.3) | `LD_PRELOAD` is not set inside, no message | the same: not set, no message | logs/06 |
| classic snap | passed through (`SNAP_SAVED_LD_PRELOAD`); a 64-bit app loads both | the same | sources |
| flatpak | cleared unconditionally (`default_exports` `{"LD_PRELOAD", NULL}`) | the same | sources |
| Steam client (32-bit `steam`) | the two 32-bit lines above, for steam and every 32-bit child | the same count; with a 64-bit directory on the search path the reason can read `wrong ELF class: ELFCLASS64` | sources + logs/02-03 |
| Steam Linux Runtime / pressure-vessel | rewritten: `$LIB` resolved per architecture on the host; 64-bit games get the host library; for i386 an info message only in verbose mode | the same outcome | sources |
| a unit of the user manager (`systemd-run --user`), also after `dbus-update-activation-environment --systemd` and `systemctl --user import-environment` | the path form, both libraries load | (not measured) | logs/04 + its correction |
| `systemctl --user show-environment --output=json` | the path form | - | logs/04 |
| `env $(systemctl --user show-environment)` | the value keeps systemctl's quoting `$'…'`: 2 ld.so lines, nothing loads | the same with a bare value: the quoting is the fault, not the form | logs/04 |
| `eval "export <show-environment line>"` in bash | the path form, both load | - | logs/04 |
| the same in dash (no `$'…'` in dash) | `$/usr/$LIB/…`: 1 ld.so line, the first library is lost | the same fault | logs/04 |
| a script that splices the value into code unquoted (`sh -c "X=$LD_PRELOAD …"`) | **`/usr//libunity-gtk4-menu.so.0:/usr//libgtk-nocsd.so.0`: 2 ld.so lines, nothing loads** | a bare value has no `$`, so it survives this | logs/04 |
| `sudo -E`, `sudo --preserve-env=LD_PRELOAD`, `su`, `su -` (from root) | not set: sudo and su drop it | the same | logs/04 |
| tmux (server started with the value) | the path form inside, both load | - | logs/04 |
| an ssh session | not set (sshd does not pass the session's environment) | the same | logs/04 |

### Sources for the rows not measured here (read-only subagent, 2026-10-13)

- **Steam client:** steam.sh (steam-launcher 1:1.0.0.87) clears `LD_PRELOAD` only for its own `ldd` calls and the
  debugger mode (:475-480, :921-926). glibc prints the message from `elf/rtld.c:804`.
- **pressure-vessel** (steam-runtime-tools v0.20261007.0):
  - `_v2-entry-point` saves and unsets `LD_PRELOAD` (:21-22) and passes it on as `--ld-preloads` (:284-285);
  - `pressure-vessel/wrap-preload.c` resolves `$LIB` per architecture (:446-462), maps `/usr` to `/run/host/usr`
    (:74-83), and logs the i386 skip at info level (:316, shown only when verbose).
  - pressure-vessel also drops any entry whose path contains `gtk3-nocsd` (:415-420, steam-runtime#286, a crash
    through a `g_object_get` hook). `libgtk-nocsd.so.0` does not match that filter. gtk-nocsd 4.8 interposes
    `g_object_new`, not `g_object_get` (`debian/libgtk-nocsd0.symbols`). Whether it causes trouble inside 64-bit
    games was not tested.
- **flatpak** 1.16.1: `common/flatpak-run.c:548`.
- **snapd** 2.72:
  - strict snaps: snap-confine runs with file capabilities, so glibc's secure mode drops the preload
    (`cmd/snap/cmd_run.go:1510-1515`, glibc `elf/rtld.c:2541-2564`);
  - classic snaps: `cmd/snap-exec/main.go:197`.
  - The measurement on snapd 2.76.3 shows no message even for the bare names, although the sources suggested
    snap-confine might print one.

## Reading

- **32-bit processes:** they print the same number of loader lines with the path form as with the bare names, one
  per library per exec image. Only the name in the line differs. That is the normal case, because no i386 copies of
  the libraries exist. A stand-in 32-bit library placed in `lib32` or `lib/i386-linux-gnu` was found by the
  matching loader, which confirms the `$LIB` expansion.
- **Sandboxes:** none of them makes the path form worse. Flatpak and strict snaps clear the preload, and
  pressure-vessel rewrites it.
- **Rebuilding the environment:**
  - Two cases break both forms the same way: systemctl's `$'…'` quoting fed to `env`, and `eval` in dash.
  - One case breaks only the path form: a script that splices the value unquoted into code that a shell then
    expands. `$LIB` becomes empty and the paths read `/usr//…`. The libraries are then not loaded in what that
    script starts, and the loader prints 2 lines.
  - None of the system's own paths does this: lightdm-session, `/etc/X11/Xsession` (UNITY-20261013-001), the user
    manager, D-Bus activation, tmux, sudo and su.

## Is a task needed?

No package task. The one case where the path form is worse (a third-party script splicing the value into shell
code unquoted) is a fault of that script, and its only effect is that the two libraries are missing in what it
starts, with two loader lines. It belongs in the release note of gtk-nocsd 4.8-1+unity4 as a sentence, if anywhere.
C decides.
