# Comment for LP: #2147013

Post this first, before the SRU template in `sru.md`, and nominate the bug for
the Resolute series at the same time. Not submitted. Needs May's agreement on
the wording.

---

This is still broken in 26.04 (resolute).

The bug reads Fix Released because the Janitor closed it when
4.0.8+18.10.20180623-0ubuntu13 published in the development series. Resolute
still carries 0ubuntu12, which ports Validator to PCRE2 but leaves nux.pc.in
and configure.ac naming libpcre. Since libpcre3-dev is not in resolute and
pkg-config resolves Requires transitively, nux-4.0 is unresolvable there:

  $ pkg-config --print-errors --exists nux-4.0
  Package libpcre was not found in the pkg-config search path.

The practical effect is that unity cannot be rebuilt in 26.04. Verified in a
clean resolute chroot: unity 7.7.1+26.04.20260306-0ubuntu3 stops at configure
against 0ubuntu12, and builds in 372 s against 0ubuntu13.

0ubuntu13 was already copied to resolute-proposed on 2026-04-24 and deleted on
2026-04-28 as "SRU cleanup", so there is nothing in -proposed to verify now.

There is no Resolute task on this bug, which is presumably why the gap went
unnoticed. Nominating it so the series shows up.

Part of this investigation was done with AI assistance; the reproduction and
the builds were run and checked by hand.
