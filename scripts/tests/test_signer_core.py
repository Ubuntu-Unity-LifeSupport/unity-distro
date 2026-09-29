#!/usr/bin/env python3
"""Refusal tests for signer/signer_core.py (UNITY-20260929-021; the list in
UNITY-20260929-019, May's invariant and design reviews 3-4, and the -021
reviews). Each case starts from an approved Release and index set and changes
exactly one thing; the signer must refuse. A fake signing backend stands in for
gpg here (the real one is tested end to end with a throwaway key).
Run: python3 -m unittest discover -s scripts/tests
"""

import bz2
import copy
from datetime import datetime, timedelta, timezone
import gzip
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "signer"))
import signer_core as core  # noqa: E402

TEMPLATE = json.loads((ROOT / "signer" / "release-template.json").read_text())
T0 = datetime(2026, 9, 29, 22, 0, 0, tzinfo=timezone.utc)
PKGS = """Package: demo
Version: 1.0+unity1
Architecture: amd64
Maintainer: t <t@example.com>
Filename: pool/main/d/demo/demo_1.0+unity1_amd64.deb
Size: 1000
SHA256: {a}
Description: demo

Package: libdemo1
Version: 1.0+unity1
Architecture: amd64
Maintainer: t <t@example.com>
Filename: pool/main/d/demo/libdemo1_1.0+unity1_amd64.deb
Size: 2000
SHA256: {b}
Description: library
""".format(a="a" * 64, b="b" * 64)


class FakeBackend:
    """Signs with sha256; counts calls; can be told to misbehave."""
    def __init__(self, clear_over_other=False):
        self.calls = 0
        self.clear_over_other = clear_over_other

    def sign_detached(self, data):
        self.calls += 1
        return b"SIG " + hashlib.sha256(data).hexdigest().encode()

    def sign_clear(self, data):
        body = data + b"x" if self.clear_over_other else data
        return b"CLEAR\n" + body + b"SIG " + hashlib.sha256(body).hexdigest().encode()

    def verify_detached(self, sig, data):
        return sig == b"SIG " + hashlib.sha256(data).hexdigest().encode()

    def verify_clear(self, clear):
        if not clear.startswith(b"CLEAR\n"):
            return None
        body, _, sig = clear[6:].rpartition(b"SIG ")
        return body if sig == hashlib.sha256(body).hexdigest().encode() else None


def files_for(packages=PKGS):
    raw = packages.encode()
    return {"main/binary-amd64/Packages": raw,
            "main/binary-amd64/Packages.gz": gzip.compress(raw, mtime=0),
            "main/binary-amd64/Packages.bz2": bz2.compress(raw),
            "main/binary-amd64/Release": core.component_release(TEMPLATE, "main", "amd64")}


def aptly_release(files, date=T0):
    """What aptly writes: the signer's format, without Valid-Until."""
    own = core.build_release(TEMPLATE, files, date)
    return b"\n".join(l for l in own.split(b"\n") if not l.startswith(b"Valid-Until:"))


def deb_ok(fields):
    return "no scripts"


class SignerCoreTest(unittest.TestCase):
    def setUp(self):
        self.state = core.new_state()
        self.files = files_for()
        self.backend = FakeBackend()

    def approved(self, files=None, now=T0):
        files = files or self.files
        pid = core.propose(self.state, TEMPLATE, files, "UNITY-20260929-021", deb_ok, now)
        core.approve(self.state, pid)
        return pid

    def sign(self, release=None, files=None, now=T0 + timedelta(minutes=1)):
        files = files or self.files
        return core.sign(self.state, TEMPLATE, release if release is not None else aptly_release(files),
                         files, self.backend, now)

    def go_live(self, trio):
        return core.live(self.state, trio["inrelease"])

    # -- the positive case ----------------------------------------------------

    def test_only_date_and_valid_until_differ_and_it_signs(self):
        self.approved()
        trio = self.sign()
        own = trio["release"].decode()
        self.assertIn("Valid-Until:", own)
        date, valid = core.release_date(own), core.release_date(own, "Valid-Until")
        self.assertEqual(valid - date, timedelta(days=3))
        # backdated by the template (slow client clocks), whole seconds
        self.assertEqual(date, (T0 + timedelta(minutes=1) - timedelta(seconds=300)).replace(microsecond=0))
        self.assertIsNone(core.compare_release(aptly_release(self.files), trio["release"]))
        self.assertEqual(self.backend.verify_clear(trio["inrelease"]), trio["release"])
        self.assertEqual(self.go_live(trio), core.set_id(core.check_index_set(TEMPLATE, self.files)))

    # -- Release fields ---------------------------------------------------------

    def release_lines(self):
        return aptly_release(self.files).decode().split("\n")

    def test_release_field_changed_added_removed(self):
        self.approved()
        base = self.release_lines()
        fields = [l.split(":", 1)[0] for l in base if l and not l.startswith(" ") and ":" in l]
        cases = {}
        for field in fields:
            i = next(n for n, l in enumerate(base) if l.startswith(field + ":"))
            if field != "Date":
                changed = list(base); changed[i] = base[i] + "x"
                cases[f"{field} changed"] = changed
            removed = list(base); del removed[i]
            cases[f"{field} removed"] = removed
        for added in ("NotAutomatic: yes", "ButAutomaticUpgrades: yes", "Acquire-By-Hash: yes", "Signed-By: x",
                      "Valid-Until: Fri, 02 Oct 2026 22:00:00 UTC"):
            cases[f"{added.split(':')[0]} added"] = base[:5] + [added] + base[5:]
        for label, lines in cases.items():
            with self.subTest(case=label):
                with self.assertRaises(core.Refused):
                    self.sign(release="\n".join(lines).encode())

    def test_checksum_lines_in_each_section(self):
        self.approved()
        base = self.release_lines()
        for section, _ in core.SECTIONS:
            start = base.index(section + ":") + 1
            line = base[start]
            digest, size, path = line.split()
            for label, lines in {
                "size changed": base[:start] + [line.replace(f" {size} ", f" {int(size) + 1:8d} ")] + base[start + 1:],
                "hash changed": base[:start] + [line.replace(digest, "0" * len(digest))] + base[start + 1:],
                "file added": base[:start] + [f" {digest} {int(size):8d} main/binary-amd64/Packages.xz"] + base[start:],
                "file removed": base[:start] + base[start + 1:],
            }.items():
                with self.subTest(section=section, case=label):
                    with self.assertRaises(core.Refused):
                        self.sign(release="\n".join(lines).encode())

    # -- index content ------------------------------------------------------------

    def test_compressed_variant_differs(self):
        self.approved()
        other = PKGS.replace("Description: demo", "Description: demo!").encode()
        for variant, data in (("main/binary-amd64/Packages.gz", gzip.compress(other, mtime=0)),
                              ("main/binary-amd64/Packages.bz2", bz2.compress(other))):
            with self.subTest(variant=variant):
                files = dict(self.files, **{variant: data})
                with self.assertRaises(core.Refused):
                    self.sign(files=files)

    def test_packages_entry_changes(self):
        self.approved()
        cases = {
            "version": PKGS.replace("Version: 1.0+unity1\nArchitecture: amd64\nMaintainer: t <t@example.com>\nFilename: pool/main/d/demo/demo",
                                    "Version: 1.0+unity2\nArchitecture: amd64\nMaintainer: t <t@example.com>\nFilename: pool/main/d/demo/demo", 1),
            "architecture": PKGS.replace("Architecture: amd64", "Architecture: all", 1),
            "sha256": PKGS.replace("a" * 64, "c" * 64),
            "size": PKGS.replace("Size: 1000", "Size: 1001"),
            "filename": PKGS.replace("pool/main/d/demo/demo_1.0", "pool/main/d/demo/demo-evil_1.0"),
            "another control field": PKGS.replace("Description: demo\n", "Description: demo\nPre-Depends: evil\n"),
            "entry added": PKGS + "\nPackage: extra\nVersion: 1\nArchitecture: amd64\nFilename: pool/main/e/extra/extra_1_amd64.deb\nSize: 1\nSHA256: " + "d" * 64 + "\n",
            "entry removed": PKGS.split("\n\n")[0] + "\n",
        }
        for label, text in cases.items():
            with self.subTest(case=label):
                self.assertNotEqual(text, PKGS)
                with self.assertRaises(core.Refused):
                    self.sign(files=files_for(text))

    def test_distribution_component_prefix(self):
        self.approved()
        base = self.release_lines()
        for label, old, new in (("distribution", "Suite: resolute", "Suite: noble"),
                                ("codename", "Codename: resolute", "Codename: noble"),
                                ("prefix (in Origin/Label)", "Origin: . resolute", "Origin: other resolute"),
                                ("component", "Components: main", "Components: main contrib")):
            with self.subTest(case=label):
                with self.assertRaises(core.Refused):
                    self.sign(release="\n".join(l.replace(old, new) for l in base).encode())
        with self.assertRaises(core.Refused):  # a file of another component
            core.check_index_set(TEMPLATE, dict(self.files, **{"contrib/binary-amd64/Packages": PKGS.encode()}))

    def test_component_release_fields(self):
        base = core.component_release(TEMPLATE, "main", "amd64").decode().split("\n")
        for i, line in enumerate(l for l in base if l):
            for label, lines in (("changed", base[:i] + [line + "x"] + base[i + 1:]),
                                 ("removed", base[:i] + base[i + 1:]),
                                 ("added", base[:i] + ["NotAutomatic: yes"] + base[i:])):
                with self.subTest(field=line.split(":")[0], case=label):
                    files = dict(self.files, **{"main/binary-amd64/Release": "\n".join(lines).encode()})
                    with self.assertRaises(core.Refused):
                        core.check_index_set(TEMPLATE, files)

    def test_paths_and_contents_refused(self):
        for path in ("Contents-amd64.gz", "main/Contents-amd64", "main/binary-amd64/../binary-amd64/Packages",
                     "/main/binary-amd64/Packages", "main/binary-amd64/Packages%2e", "main/binary-amd64/by-hash/SHA256/" + "a" * 64,
                     "main/i18n/Translation-en"):
            with self.subTest(path=path):
                with self.assertRaises(core.Refused):
                    core.check_index_set(TEMPLATE, dict(self.files, **{path: b"x"}))

    def test_duplicates_and_malformed_entries(self):
        for label, text in {
            "field twice": PKGS.replace("Size: 1000\n", "Size: 1000\nSize: 1000\n"),
            "entry twice": PKGS + "\n" + PKGS.split("\n\n")[0] + "\n",
            "invalid name": PKGS.replace("Package: demo\n", "Package: Demo_X\n"),
            "invalid version": PKGS.replace("Version: 1.0+unity1", "Version: \x1b[2Jx", 1),
            "sha256 not hex": PKGS.replace("a" * 64, "z" * 64),
            "filename with ..": PKGS.replace("pool/main/d/demo/demo_1.0", "pool/../etc/demo_1.0"),
        }.items():
            with self.subTest(case=label):
                with self.assertRaises(core.Refused):
                    core.propose(core.new_state(), TEMPLATE, files_for(text), None, deb_ok, T0)

    def test_several_versions_of_one_package(self):
        """Rehearsal deviation 6: a repository lists several versions of a package."""
        v2 = PKGS.split("\n\n")[0].replace("1.0+unity1", "1.0+unity2").replace("a" * 64, "e" * 64)
        text = PKGS + "\n" + v2 + "\n"
        found = core.entries(core.check_index_set(TEMPLATE, files_for(text)))
        self.assertEqual(len([k for k in found if k[1] == "demo"]), 2)
        self.approved()
        self.go_live(self.sign())
        pid = core.propose(self.state, TEMPLATE, files_for(text), None, deb_ok, T0 + timedelta(minutes=5))
        rows = self.state["proposals"][pid]["diff"]
        self.assertEqual([(r["change"], r["package"], r["version"]) for r in rows], [("added", "demo", "1.0+unity2")])
        self.assertEqual(rows[0]["other_versions_before"], ["1.0+unity1"])
        self.assertIn("other versions before: 1.0+unity1", "\n".join(core.console_lines(self.state, pid)))
        with self.assertRaises(core.Refused):  # the same version twice is still a duplicate
            core.entries(core.check_index_set(TEMPLATE, files_for(PKGS + "\n" + PKGS.split("\n\n")[0] + "\n")))

    def test_live_packages_fragment_with_nine_unity_versions(self):
        """The 9 unity entries of the live Packages (2026-09-29): all accepted."""
        text = (ROOT / "scripts" / "tests" / "fixtures" / "live-packages-unity.txt").read_text()
        found = core.entries(core.check_index_set(TEMPLATE, files_for(text)))
        versions = sorted(k[2] for k in found if k[1] == "unity")
        self.assertEqual(len(versions), 9)
        self.assertEqual(len(set(versions)), 9)

    def test_index_streams_exactly_one(self):
        """Verifier round 1: a second stream or trailing bytes in a bz2/xz index."""
        import lzma
        raw = PKGS.encode()
        for variant, data in (("main/binary-amd64/Packages.bz2", bz2.compress(raw) + bz2.compress(b"x")),
                              ("main/binary-amd64/Packages.bz2", bz2.compress(raw) + b"trailing"),
                              ("main/binary-amd64/Packages.xz", lzma.compress(raw) + lzma.compress(b"x")),
                              ("main/binary-amd64/Packages.xz", lzma.compress(raw)[:-10])):
            with self.subTest(variant=variant, size=len(data)):
                with self.assertRaises(core.Refused):
                    core.check_index_set(TEMPLATE, dict(self.files, **{variant: data}))
        self.assertTrue(core.check_index_set(TEMPLATE, dict(self.files, **{"main/binary-amd64/Packages.xz": lzma.compress(raw)})))

    def test_ascii_digits_only(self):
        with self.assertRaises(core.Refused):
            core.entries(core.check_index_set(TEMPLATE, files_for(PKGS.replace("Size: 1000", "Size: \u00b2\u0661"))))
        state = core.new_state()
        pid = core.propose(state, TEMPLATE, self.files, "UNITY-2026092\u0669-021", deb_ok, T0)
        self.assertIsNone(state["proposals"][pid]["task_id"])

    def test_decompression_limit(self):
        saved = core.MAX_INDEX
        core.MAX_INDEX = 100
        try:
            with self.assertRaises(core.Refused):
                core.check_index_set(TEMPLATE, self.files)
        finally:
            core.MAX_INDEX = saved

    # -- approvals, last-live, dates -------------------------------------------------

    def test_approval_used_twice_and_two_calls(self):
        self.approved()
        first = self.sign()
        calls = self.backend.calls
        again = self.sign()  # the second of aptly's two calls: the same bytes
        self.assertEqual(first, again)
        self.assertEqual(self.backend.calls, calls)  # stored pair, no new signing
        with self.assertRaises(core.Refused):  # other bytes (a new Date) under the same approval
            self.sign(release=aptly_release(self.files, T0 + timedelta(hours=1)))

    def test_approval_after_last_live_moved(self):
        self.approved()
        other = files_for(PKGS.replace("Size: 2000", "Size: 2001"))
        self.approved(other)  # a second approval, same base
        self.go_live(self.sign())
        with self.assertRaises(core.Refused):  # revoked when last-live moved
            self.sign(files=other, now=T0 + timedelta(minutes=5))

    def test_stale_proposal_cannot_be_approved(self):
        pid_a = core.propose(self.state, TEMPLATE, self.files, None, deb_ok, T0)
        other = files_for(PKGS.replace("Size: 2000", "Size: 2001"))
        pid_b = core.propose(self.state, TEMPLATE, other, None, deb_ok, T0)
        core.approve(self.state, pid_a)
        self.go_live(self.sign())
        self.assertNotIn(pid_b, self.state["proposals"])  # based on the old last-live: dropped
        self.state["proposals"]["x"] = {"base": "old", "set_id": "s", "entries": {}, "diff": [], "task_id": None, "received": ""}
        with self.assertRaises(core.Refused):
            core.approve(self.state, "x")

    def test_live_refusals(self):
        self.approved()
        trio = self.sign()
        for label, served in (("foreign", b"CLEAR\nsomething else"),
                              ("extra data after the signature", trio["inrelease"] + b"\nextra"),
                              ("Release.gpg instead", trio["release_gpg"])):
            with self.subTest(case=label):
                with self.assertRaises(core.Refused):
                    core.live(self.state, served)
        self.go_live(trio)
        old = trio
        self.approved(files_for(PKGS.replace("Size: 2000", "Size: 2001")), now=T0 + timedelta(minutes=2))
        new = self.sign(files=files_for(PKGS.replace("Size: 2000", "Size: 2001")), now=T0 + timedelta(minutes=3))
        self.go_live(new)
        with self.assertRaises(core.Refused):  # an older signed Release must not move last-live back
            core.live(self.state, old["inrelease"])

    def test_not_approved(self):
        with self.assertRaises(core.Refused):
            self.sign()

    def test_dates_strictly_increase(self):
        self.approved()
        trio = self.sign(now=T0 + timedelta(hours=2))
        self.go_live(trio)
        last = core.release_date(trio["release"].decode())
        for now in (T0, T0 + timedelta(hours=2)):  # a clock behind, or equal
            with self.subTest(now=now):
                again = core.resign(self.state, TEMPLATE, self.backend, now)
                date = core.release_date(again["release"].decode())
                self.assertGreater(date, last)
                last = date

    def test_inrelease_and_release_gpg_over_different_bytes(self):
        self.approved()
        self.backend = FakeBackend(clear_over_other=True)
        with self.assertRaises(core.Refused):
            self.sign()

    def test_resign_only_last_live_and_from_stored_files(self):
        with self.assertRaises(core.Refused):  # nothing live yet
            core.resign(self.state, TEMPLATE, self.backend, T0)
        self.approved()
        self.go_live(self.sign())
        trio = core.resign(self.state, TEMPLATE, self.backend, T0 + timedelta(days=1))
        self.assertEqual(core.current_trio(self.state), trio)
        self.assertIsNone(core.compare_release(aptly_release(self.files), trio["release"]))
        # a signed but not yet live approval does not change what is re-signed
        other = files_for(PKGS.replace("Size: 2000", "Size: 2001"))
        self.approved(other, now=T0 + timedelta(days=1, minutes=1))
        self.sign(files=other, now=T0 + timedelta(days=1, minutes=2))
        again = core.resign(self.state, TEMPLATE, self.backend, T0 + timedelta(days=1, minutes=3))
        self.assertIsNone(core.compare_release(aptly_release(self.files), again["release"]))
        self.assertIsNotNone(core.compare_release(aptly_release(other), again["release"]))
        self.state["signed"][self.state["last_live"]["signed_key"]]["files"]["main/binary-amd64/Packages"] = b"x".hex()
        with self.assertRaises(core.Refused):  # stored files no longer match the approved content
            core.resign(self.state, TEMPLATE, self.backend, T0 + timedelta(days=2))

    def test_corrupt_state_refuses(self):
        for state in (None, {}, {"schema": 2}):
            with self.subTest(state=state):
                with self.assertRaises(core.Refused):
                    core.propose(state, TEMPLATE, self.files, None, deb_ok, T0)

    # -- the console ---------------------------------------------------------------

    def test_console_shows_only_validated_text(self):
        pid = core.propose(self.state, TEMPLATE, self.files, "UNITY-20260929-021\x1b[2J", deb_ok, T0)
        lines = core.console_lines(self.state, pid)
        self.assertIn("task: (not shown)", lines)
        self.assertTrue(all(all(32 <= ord(c) < 127 for c in l) for l in lines))
        pid2 = core.propose(core.new_state(), TEMPLATE, self.files, "UNITY-20260929-021", deb_ok, T0)
        # "claimed by builder"
        state = core.new_state()
        pid2 = core.propose(state, TEMPLATE, self.files, "UNITY-20260929-021", deb_ok, T0)
        self.assertIn("task (claimed by builder): UNITY-20260929-021", core.console_lines(state, pid2))
        # a changed control field shows by name and hashes, never its text
        self.approved()
        self.go_live(self.sign())
        changed = files_for(PKGS.replace("Description: demo\n", "Description: \x1b]0;approve me\x07\n"))
        pid3 = core.propose(self.state, TEMPLATE, changed, None, deb_ok, T0 + timedelta(minutes=9))
        text = "\n".join(core.console_lines(self.state, pid3))
        self.assertIn("field Description changed", text)
        self.assertNotIn("approve me", text)

    def test_deb_checker_failure_refuses_the_proposal(self):
        def failing(fields):
            raise core.Refused("404")
        with self.assertRaises(core.Refused):
            core.propose(self.state, TEMPLATE, self.files, None, failing, T0)
        self.assertEqual(self.state["proposals"], {})


if __name__ == "__main__":
    unittest.main()
