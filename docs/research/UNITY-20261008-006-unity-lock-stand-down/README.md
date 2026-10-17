# UNITY-20261008-006: one screen locker in the Unity session (light-locker +unity5, unity +unity14)

Agent A, target `target-desktop`. Published in two steps:
UNITY-20261008-006 (light-locker 1.8.0-3ubuntu4+unity5) and
UNITY-20261017-004 (unity 7.7.1+26.04.20260306-0ubuntu3+unity14), which
declares `Breaks: light-locker (<< 1.8.0-3ubuntu4+unity5)`.

## What was wrong

The Unity session ran two screen lockers: Unity's own lockscreen (in compiz)
and light-locker, which the Ubuntu Unity flavour installs and which owns
`org.gnome.ScreenSaver`. Which one locked depended on the trigger
(`dev/target-current/`, live stack of 2026-10-13):

| trigger | locked by |
|---|---|
| presence idle, Super+L, the indicator's Lock (`com.canonical.Unity.Session.Lock`) | Unity, on the session's own VT |
| Ctrl+Alt+L, `loginctl lock-session` | light-locker (greeter) |
| suspend | both: sleep started 30 s after the request (light-locker's delay inhibitor ran out), and after resume the greeter and Unity's lock were both up |
| screen reader or on-screen keyboard enabled: manual and logind locks | light-locker |
| the same, presence idle | nothing locked |

Unity also asks for `org.gnome.ScreenSaver` (queued behind light-locker), and
light-locker stopped at start when unity-settings-daemon's screensaver proxy
had taken `org.freedesktop.ScreenSaver` first (1 cold boot of 5,
`target/04-boot1-owner.txt`, `target/08-boot5-names.txt`); Unity was then the
only locker.

## What is fixed

The locker is the owner of `org.gnome.ScreenSaver`. Unity's lockscreen stands
down while another connection owns it, and takes over when that owner goes
away.

| package | version | change |
|---|---|---|
| light-locker | 1.8.0-3ubuntu4+unity5 | `debian/patches/0008`-`0011`, branch `a/UNITY-20261008-006` (on +unity4 `56582ba`) |
| unity | 7.7.1+26.04.20260306-0ubuntu3+unity14 | branch `a/UNITY-20261008-006` (on +unity13 `c5339fc6`): `dcff4096`, `0a0357bb` (tests), `356e2ae7`, `82b42131`, `a58ab24b`, `4a150770`, `1ad5bbff`, `7a3207fe` (Breaks), `a97045b1` |

light-locker, in a Unity session (`Unity` in `XDG_CURRENT_DESKTOP`):
- 0008: the timer that locks `lock-after-screensaver` seconds after the
  blank is not armed; Unity decides whether and when to lock. The setting is
  not changed (light-locker writes its settings back at start, so a
  different default would not reach existing users).
- 0010: `org.gnome.ScreenSaver` alone decides whether light-locker runs. It
  is requested first; `org.freedesktop.ScreenSaver` is taken only if free
  (the proxy forwards its calls to `org.gnome.ScreenSaver`). No name is taken
  from another owner. Other desktops are unchanged.
- 0009, 0011: tests in `make check`.

unity, while another connection owns `org.gnome.ScreenSaver` (and in legacy
mode, screen reader or on-screen keyboard enabled):
- manual locks (Super+L, the session dialog, `com.canonical.Unity.Session`
  Lock and PromptLock) and screensaver activation go to the owner;
- logind's Lock is left to the owner; Unity takes no lock and holds no
  inhibitor on suspend, and does not write logind's `LockedHint`;
- on presence idle Unity asks the owner to blank (`SetActive`) and, if
  `org.gnome.desktop.screensaver lock-enabled`, to lock after `lock-delay`;
  input, another presence status, or the owner's end of the blank cancels
  it. In legacy mode the session now locks on idle too.
- until Unity knows who owns the name, a lock request is kept and replayed;
  when the owner goes away Unity gets the name and locks again, keeping a lock
  that logind reports.
- `DBusServer::name_acquired` is emitted when the name is owned, not when the
  bus connection is made (it was emitted while Unity was only queued).

## Checks

- **Unit tests** (unity, built with tests enabled outside the package build):
  glib-dbus-server 23/23, gnome-session-manager 54/54,
  screensaver-dbus-manager 16/16, lockscreen-controller 30/30. On the base
  with the tests, 3, 5 and 19 of the new tests fail.
- **make check** (light-locker): test-lock-after and test-listener-inhibit
  pass; without 0008 the Unity cases of test-lock-after fail
  (`dev/ll-helper-test/`); without 0010 three of the new acquire cases fail.
- **Target** (`target-gate/`, both gated builds on the live stack of
  2026-10-17): five cold boots, light-locker owned `org.gnome.ScreenSaver`
  every time, also on the boot where the proxy had
  `org.freedesktop.ScreenSaver` first; the same with light-locker started 20 s
  late on purpose. Every trigger of the table locked through light-locker,
  with one greeter switch and Unity's lockscreen inactive; lock-delay and
  lock-enabled are followed; suspend began about 1 s after the request; a
  second light-locker and a light-locker restarted after the takeover stop
  without touching `LockedHint`; with light-locker gone, Super+L locks with
  Unity's lockscreen.

## Verification

- Design and code review (Design Challenger): unity part APPROVE in round 3;
  start-up order APPROVE in round 7 (light-locker 0010-0011).
- Verifiers: see the release records.

## Not changed / known limits

- light-locker restarted in a running session stops: Unity holds
  `org.gnome.ScreenSaver` from the moment light-locker exits, and stays the
  locker.
- While the proxy holds `org.freedesktop.ScreenSaver`, that name sends no
  ActiveChanged, and its Inhibit becomes a session-manager idle inhibitor.
- light-locker starts in the Unity session only because cinnamon-session
  compares `NotShowIn=GNOME;Unity;` with the whole string
  `Unity:Unity7:ubuntu`; if light-locker does not start, Unity is the locker.
- Not tested: DPMS (not in a VM), lid, guest account, switch-user from the
  indicator.
- Ctrl+Alt+L locks also when `org.gnome.desktop.lockdown disable-lock-screen`
  is set (unity-settings-daemon, unchanged).
