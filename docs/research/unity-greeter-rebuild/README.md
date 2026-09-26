# unity-greeter: rebuildable in resolute again (A-5, 2026-09-26, agent A)

Found by agent B's rebuild survey (`../rebuild-loss/`, B-7): the archive's
`25.04.1-0ubuntu1` (built 2025) cannot be rebuilt in resolute -
`unsat-dependency: liblightdm-gobject-1-dev (>= 1.4.0)`.

**Rule 0.** 26.10 carries the same `25.04.1-0ubuntu1` (no rebuild there, so it
would fail the same way); Debian has no unity-greeter. The same lightdm split
was fixed for indicator-keyboard in 26.10's 0ubuntu3 and in our `+unity1` by
build-depending on `lightdm-vala`. Nothing newer to take.

**Cause.** lightdm `1.32.0-6ubuntu4` ships the headers as
`liblightdm-gobject-dev` with an **unversioned** `Provides:
liblightdm-gobject-1-dev` - a versioned build-dependency cannot be satisfied
by it - and moved `liblightdm-gobject-1.vapi` to `lightdm-vala`.

**`25.04.1-0ubuntu1+unity1`** (branch `unity/resolute`,
https://github.com/Ubuntu-Unity-LifeSupport/unity-greeter):
- `Build-depend on liblightdm-gobject-dev and lightdm-vala` - the fix.
- `tests: take Gdk.Key values as uint` - the test program no longer compiled
  with current Vala (31 errors, one signature).
- `debian/rules: run the tests without make parallelism` - the test's Vala
  stamp rule raced with itself under `-j4`.
The tests now build and run, and fail under valgrind (150 errors in 8
contexts in one test process); `debian/rules` has ignored test failures since
before us (`-dh_auto_test`) and still does. Not investigated further.

**Build** in a clean resolute chroot: 53-95 s, `build-unity1.log.gz`.
**Against the archive .deb:** identical file list, plus the translations
(`/usr/share/locale/*/LC_MESSAGES/unity-greeter.mo`, 119 languages) that
Launchpad strips into language packs and our builds keep - no path conflict
with `language-pack-*` (those use `/usr/share/locale-langpack`). Depends differ
only in automatic version floors (libc6 2.38, liblightdm-gobject-1-0 1.16.0).

**Live on target** (clean snapshot + our aptly, lightdm `1.32.0-6ubuntu4+unity1`,
greeter switched from the stock `lightdm-gtk-greeter` to `unity-greeter` for the
test, two test users with a password, removed afterwards): the greeter comes
up with its own settings daemon and indicators (screenshot checked); password
login of `utest`: session up, greeter gone; switch user from that session:
second greeter on `:1`, `utest` marked as logged in, `utest2` logs in, both
sessions alive; switch back to `utest` through a third greeter: the existing
session becomes active again. No warnings or crashes from unity-greeter in the
journal. The stock configuration uses `lightdm-gtk-greeter`
(`/etc/lightdm/lightdm.conf`, alternatives), so this package matters for users
who pick unity-greeter; restored afterwards. Published to aptly; target = aptly.
