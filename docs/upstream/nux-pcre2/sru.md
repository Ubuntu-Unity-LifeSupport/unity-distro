# SRU: nux 4.0.8+18.10.20180623-0ubuntu13 for resolute

Text prepared for LP: #2147013. Not submitted. Do not send without May's
agreement on this exact wording.

Before sending, nominate the bug for the Resolute series - there is currently
no Resolute task at all, so the bug is invisible to the SRU team.

---

[Impact]

nux-4.0.pc in resolute lists libpcre in its Requires line, but libpcre3-dev was
removed from the series in favour of PCRE2. pkg-config resolves Requires
transitively, so nux-4.0 itself becomes unresolvable, and every package that
build-depends on libnux-4.0-dev fails at configure time. unity is one of them,
which means Unity 7 cannot be rebuilt from source in 26.04 at all.

26.04 is the release the Ubuntu Unity team has committed to supporting until
2031. For as long as this stands, no fix of any kind - security included - can
be built for unity or for any other reverse build-dependency of nux in this
series.

0ubuntu12, which is what resolute carries, already ports the C++ code to PCRE2
via debian/patches/migrate-to-libpcre2.patch. What it does not do is update the
packaging metadata: nux.pc.in and configure.ac still name libpcre. 0ubuntu13
extends the same patch with those two hunks, and nothing else.

[Test Plan]

The failure is visible without building anything.

On an up-to-date Ubuntu 26.04 (resolute) amd64 system:

  $ sudo apt install libnux-4.0-dev
  $ pkg-config --print-errors --exists nux-4.0 ; echo $?

With 4.0.8+18.10.20180623-0ubuntu12 from resolute this prints

  Package libpcre was not found in the pkg-config search path.
  Perhaps you should add the directory containing `libpcre.pc'
  to the PKG_CONFIG_PATH environment variable

and exits 1.

With 4.0.8+18.10.20180623-0ubuntu13 from resolute-proposed the same command
exits 0, and

  $ pkg-config --modversion nux-4.0

prints 4.0.8.

Fuller check, building a reverse dependency in a clean chroot:

  $ sbuild -d resolute unity

against 0ubuntu12 this stops at

  CMake Error: The following required packages were not found:
   - nux-4.0>=4.0.5

Against 0ubuntu13 the build completes and produces the seven unity binary
packages. Measured at 372 s on four cores.

Desktop check, since nux is a runtime library and not only a build-time one:
install libnux-4.0-0 and libnux-4.0-common from -proposed on an Ubuntu Unity
26.04 desktop, reboot, and log in. The session should start normally: panel,
launcher and wallpaper render, Dash opens on Super, the HUD opens on Alt, and
the session and sound indicators open. Confirming that libpcre2-8 and no PCRE1
is mapped:

  $ grep -oE 'lib(nux|pcre)[^ ]*\.so[^ ]*' /proc/$(pgrep -x compiz)/maps | sort -u

[Where problems could occur]

The patch changes real code, not only metadata, so the risk is not nil.

The C++ change is confined to Nux/Validator.{h,cpp} and replaces PCRE1 calls
with their PCRE2 equivalents. Two behavioural differences are worth naming:

- PCRE1 and PCRE2 are not bug-for-bug identical in pattern semantics. Nux ships
  three validators - IntegerValidator, DoubleValidator and HexRegExpValidator -
  and any application using them with an unusual pattern could see a different
  accept/reject outcome. The patterns in nux itself are simple numeric and
  hexadecimal forms, but a third-party consumer could pass its own.
- The old code set pcre_extra.match_limit_recursion to 2000 to bound stack use
  during matching. The new code does not set an equivalent depth limit, so a
  pathological pattern would now be bounded by PCRE2's defaults rather than by
  nux. For nux's own validators this cannot be reached; for a caller supplying
  its own pattern, resource use on a degenerate input could differ.

The destructor now calls pcre2_code_free, where the previous code freed
nothing. That fixes a leak, but it means a Validator subclass that copies the
object using the implicit copy constructor would double-free on the second
destruction. No such subclass exists in nux, and none of the three shipped
validators copies, but an out-of-tree consumer could.

The Requires change is the part that unblocks builds, and it is also the part
that could expose latent problems elsewhere: packages that failed to configure
against nux-4.0 will now get past that point and may fail later, for reasons
unrelated to this patch. unity is the only reverse build-dependency in the
archive and it has been built successfully, but anyone carrying local software
against libnux-4.0-dev will effectively be moving from "does not configure" to
"configures and then behaves as it will".

Regression scope beyond that is narrow. `reverse-depends -b libnux-4.0-dev`
reports exactly one package, unity; at runtime libnux-4.0-0 is used by unity
and libunity-core-6.0-9, both from the same source. If the upload were wrong, the visible effect would be a
broken Unity session for Ubuntu Unity 26.04 users, which is why the desktop
check above is part of the test plan rather than an afterthought.

The patch has been in the development series since April 2026 with no reported
regressions.

[Other Info]

This exact revision has been in resolute-proposed before. 0ubuntu13 was copied
there on 2026-04-24 and deleted on 2026-04-28 by Timo Aaltonen with the reason
"SRU cleanup". 26.04 released on 2026-04-23, so the upload arrived the day
after release and was most likely swept up as not following SRU process rather
than rejected on its merits. Nothing is currently sitting in -proposed to
verify, so this needs a fresh upload rather than a verification.

LP: #2147013 reads Fix Released, which is misleading in this context. The
Launchpad Janitor closed it when 0ubuntu13 published in the development series;
from the point of view of a 26.04 user nothing was fixed. The bug has only one
task, nux (Ubuntu), and no Resolute task at all.

The SRU entry condition is met: the fix is in the development series with
status Fix Released, in 0ubuntu13 and later.

Reproduction, both builds and the desktop check were carried out on Ubuntu
26.04 amd64 in a VirtualBox VM, using sbuild in a clean resolute chroot. Logs
and command output are attached.

Part of this investigation and the drafting of this report were done with AI
assistance. The reproduction, the builds and the desktop testing were run and
checked by hand.
