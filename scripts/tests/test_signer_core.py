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


POLICY = {"schema": 1, "auto_approve": True, "max_sources": 1, "max_binary_records": 40,
          "min_interval_seconds": 600, "max_per_utc_day": 6}
SCRIPTS_A = {"postinst": "1" * 64}


def stanza(name, version, sha, source=None, arch="amd64", size=1000):
    src = f"Source: {source}\n" if source else ""
    return (f"Package: {name}\nVersion: {version}\nArchitecture: {arch}\n{src}Maintainer: t <t@example.com>\n"
            f"Filename: pool/main/d/demo/{name}_{version}_{arch}.deb\nSize: {size}\nSHA256: {sha}\nDescription: {name}\n")


class MappedDebs:
    """A deb checker returning (text, map) per package name, like the service's scanner."""
    def __init__(self, maps):
        self.maps = maps

    def __call__(self, fields):
        found = self.maps.get(fields["Package"], {})
        return ("scripts: " + ",".join(sorted(found)) if found else "no scripts"), found


class RoutinePolicyTest(unittest.TestCase):
    """Permission model phase 5: May's decision 4 as code. The base is a live
    set of demo 1.0+unity1 (postinst) and libdemo1 1.0+unity1 (no scripts),
    both from source demo, whose script maps the signer recorded."""

    def setUp(self):
        self.state = core.new_state()
        self.backend = FakeBackend()
        self.base_text = stanza("demo", "1.0+unity1", "a" * 64, "demo") + "\n" + stanza("libdemo1", "1.0+unity1", "b" * 64, "demo")
        pid = core.propose(self.state, TEMPLATE, files_for(self.base_text), "UNITY-20260929-021",
                           MappedDebs({"demo": SCRIPTS_A}), T0)
        core.approve(self.state, pid)
        trio = core.sign(self.state, TEMPLATE, aptly_release(files_for(self.base_text)), files_for(self.base_text), self.backend, T0)
        core.live(self.state, trio["inrelease"])
        self.assertEqual(core.live_scripts(self.state)[("main/binary-amd64/Packages", "demo", "1.0+unity1", "amd64")], SCRIPTS_A)
        self.now = T0 + timedelta(hours=1)

    def upgrade(self, version="1.0+unity2", demo_sha="c" * 64, lib_sha="d" * 64, demo_scripts=SCRIPTS_A, lib_scripts=None,
                keep_old=True, extra="", task="UNITY-20261009-001", policy=POLICY, now=None, source="demo"):
        text = stanza("demo", version, demo_sha, source) + "\n" + stanza("libdemo1", version, lib_sha, source)
        if keep_old:
            text = self.base_text + "\n" + text
        text += extra
        maps = {"demo": demo_scripts or {}, "libdemo1": lib_scripts or {}}
        return core.propose(self.state, TEMPLATE, files_for(text), task, MappedDebs(maps), now or self.now, policy=policy)

    def assert_console(self, pid, *fragments):
        self.assertIn(pid, self.state["proposals"], "the proposal was approved although it is not routine")
        reasons = " | ".join(self.state["proposals"][pid]["policy"]["reasons"])
        for fragment in fragments:
            self.assertIn(fragment, reasons)
        return reasons

    def test_routine_upgrade_is_approved_by_policy(self):
        pid = self.upgrade()
        self.assertIn(pid, self.state["approvals"])
        self.assertEqual(self.state["approvals"][pid]["approved_by"], "policy")
        self.assertEqual(core.proposal_status(self.state, pid)["status"], "approved")
        self.assertEqual(len(self.state["auto_signed"]), 1)
        self.assertIn("auto-approved by policy", self.state["log"][-1])
        self.assertIn("UNITY-20261009-001 demo 1.0+unity2 (2 binaries)", self.state["log"][-1])
        lines = core.auto_approval_lines(self.state)
        self.assertTrue(any("auto-approved" in l and "UNITY-20261009-001" in l for l in lines))
        self.assertTrue(any("added    demo amd64" in l for l in lines))
        self.assertEqual(core.auto_approval_lines(self.state), [])  # shown once
        # the approval signs and goes live like May's; the new script maps are now on record
        files = files_for(self.base_text + "\n" + stanza("demo", "1.0+unity2", "c" * 64, "demo") + "\n" + stanza("libdemo1", "1.0+unity2", "d" * 64, "demo"))
        trio = core.sign(self.state, TEMPLATE, aptly_release(files, self.now), files, self.backend, self.now)
        core.live(self.state, trio["inrelease"])
        self.assertEqual(core.live_scripts(self.state)[("main/binary-amd64/Packages", "demo", "1.0+unity2", "amd64")], SCRIPTS_A)
        self.assertEqual(core.live_scripts(self.state)[("main/binary-amd64/Packages", "libdemo1", "1.0+unity2", "amd64")], {})

    def test_rule_1_empty_repository(self):
        state = core.new_state()
        pid = core.propose(state, TEMPLATE, files_for(self.base_text), "UNITY-20261009-001", MappedDebs({"demo": SCRIPTS_A}), T0, policy=POLICY)
        self.assertIn(pid, state["proposals"])
        self.assertIn("empty repository", " ".join(state["proposals"][pid]["policy"]["reasons"]))

    def test_rule_2_removal_and_change(self):
        pid = self.upgrade(keep_old=False)  # the old versions vanish
        self.assert_console(pid, "not only additions", "removed")
        changed = self.base_text.replace("a" * 64, "f" * 64)  # same name/version/arch, other bytes
        pid = core.propose(self.state, TEMPLATE, files_for(changed), "UNITY-20261009-002", MappedDebs({"demo": SCRIPTS_A}), self.now, policy=POLICY)
        self.assert_console(pid, "not only additions", "changed")

    def test_rule_3_new_source_and_two_sources(self):
        other = stanza("other", "2.0", "e" * 64, "other")
        pid = core.propose(self.state, TEMPLATE, files_for(self.base_text + "\n" + other), "UNITY-20261009-003",
                           MappedDebs({}), self.now, policy=POLICY)
        self.assert_console(pid, "source other is not in last-live")
        pid = self.upgrade(extra="\n" + other, task="UNITY-20261009-004")
        self.assert_console(pid, "more than 1 source package")
        pid = self.upgrade(source="unreadable source (x", task="UNITY-20261009-005")
        self.assert_console(pid, "cannot read")

    def test_rule_4_downgrade_equal_and_new_binary(self):
        pid = self.upgrade(version="1.0+unity0", task="UNITY-20261009-006")
        self.assert_console(pid, "not newer than every live version")
        core.reject(self.state, pid)
        # a new binary of a known source
        pid = self.upgrade(extra="\n" + stanza("demo-extra", "1.0+unity2", "e" * 64, "demo"), task="UNITY-20261009-008")
        self.assert_console(pid, "demo-extra amd64 is not in last-live under that name and architecture")
        # arch all vs amd64 is another binary
        pid = self.upgrade(extra="\n" + stanza("demo", "1.0+unity2", "e" * 64, "demo", arch="all"), task="UNITY-20261009-009")
        self.assert_console(pid, "demo all is not in last-live")

    def test_rule_5_source_versions_agree(self):
        text = self.base_text + "\n" + stanza("demo", "1.0+unity2", "c" * 64, "demo (1.0+unity2)") + "\n" + stanza("libdemo1", "1.0+unity2", "d" * 64, "demo (1.0+unity3)")
        pid = core.propose(self.state, TEMPLATE, files_for(text), "UNITY-20261009-010", MappedDebs({"demo": SCRIPTS_A}), self.now, policy=POLICY)
        self.assert_console(pid, "several versions")

    def test_rule_6_binary_limit(self):
        policy = dict(POLICY, max_binary_records=1)
        pid = self.upgrade(policy=policy)
        self.assert_console(pid, "2 binary records exceed the limit of 1")

    def test_rule_7_maintainer_scripts(self):
        pid = self.upgrade(demo_scripts={"postinst": "2" * 64}, task="UNITY-20261009-011")  # changed hash
        self.assert_console(pid, "maintainer scripts of demo amd64 differ from 1.0+unity1")
        pid = self.upgrade(demo_scripts={}, demo_sha="5" * 64, task="UNITY-20261009-012")  # script removed
        self.assert_console(pid, "differ")
        pid = self.upgrade(lib_scripts={"preinst": "3" * 64}, lib_sha="6" * 64, task="UNITY-20261009-013")  # script added
        self.assert_console(pid, "maintainer scripts of libdemo1 amd64 differ")
        # a live entry without a recorded map (content from before this phase) is never routine
        del self.state["last_live"]["scripts"][json.dumps(["main/binary-amd64/Packages", "demo", "1.0+unity1", "amd64"])]
        pid = self.upgrade(demo_sha="7" * 64, task="UNITY-20261009-014")
        self.assert_console(pid, "not on record")
        # a checker without maps (an older service) gives no map: not routine
        text = self.base_text + "\n" + stanza("demo", "1.0+unity2", "8" * 64, "demo") + "\n" + stanza("libdemo1", "1.0+unity2", "9" * 64, "demo")
        pid = core.propose(self.state, TEMPLATE, files_for(text), "UNITY-20261009-015", deb_ok, self.now, policy=POLICY)
        self.assert_console(pid, "were not read")

    def test_rule_4b_binary_moved_between_sources(self):
        """A binary that last-live lists under another source (a name takeover)."""
        other = stanza("other", "1.0", "e" * 64, "other")  # a second known source goes live first
        pid = core.propose(self.state, TEMPLATE, files_for(self.base_text + "\n" + other), "UNITY-20261009-040",
                           MappedDebs({}), self.now, policy=None)
        core.approve(self.state, pid)
        files = files_for(self.base_text + "\n" + other)
        core.live(self.state, core.sign(self.state, TEMPLATE, aptly_release(files, self.now), files, self.backend, self.now)["inrelease"])
        pid = self.upgrade(source="other", version="1.0+unity2", demo_sha="e" * 64, lib_sha="f" * 64,
                           demo_scripts={}, task="UNITY-20261009-041", now=self.now + timedelta(hours=1))
        self.assert_console(pid, "built from another source")

    def test_rule_11_nothing_signed_yet(self):
        """Decision 8: after adopt-live, nothing is automatic until the signer has
        signed content that went live (the first publication or the re-sign of
        the adopted set is May's)."""
        state = core.new_state()
        files = files_for(self.base_text)
        core.adopt_live(state, TEMPLATE, files, aptly_release(files), MappedDebs({"demo": SCRIPTS_A}), T0)
        self.state = state
        pid = self.upgrade()
        self.assert_console(pid, "nothing signed by this signer has gone live yet")
        core.reject(self.state, pid)
        core.resign(state, TEMPLATE, self.backend, self.now)  # May's cut-over: the adopted set re-signed under the new key
        self.assertTrue(state["current"])
        pid = self.upgrade(now=self.now + timedelta(minutes=1))
        self.assertIn(pid, state["approvals"])

    def test_rule_8_interval_and_day_limit(self):
        first = self.upgrade()
        self.assertIn(first, self.state["approvals"])
        pid = self.upgrade(version="1.0+unity3", demo_sha="e" * 64, lib_sha="f" * 64, task="UNITY-20261009-016",
                           now=self.now + timedelta(seconds=599))
        self.assert_console(pid, "less than 600 s since the last automatic approval")
        core.reject(self.state, pid)
        self.state["auto_signed"] = [{"at": (self.now + timedelta(minutes=i)).isoformat(), "task_id": f"UNITY-20261009-9{i:02d}",
                                      "pid": "x", "set_id": "s", "shown": True} for i in range(6)]
        pid = self.upgrade(version="1.0+unity3", demo_sha="e" * 64, lib_sha="f" * 64, task="UNITY-20261009-017",
                           now=self.now + timedelta(minutes=30))
        self.assert_console(pid, "6 automatic approvals today reach the limit of 6")
        core.reject(self.state, pid)
        # the day boundary (UTC): the same history the next day is no longer counted
        next_day = datetime(T0.year, T0.month, T0.day, tzinfo=timezone.utc) + timedelta(days=1, hours=1)
        pid = self.upgrade(version="1.0+unity3", demo_sha="e" * 64, lib_sha="f" * 64, task="UNITY-20261009-018", now=next_day)
        self.assertIn(pid, self.state["approvals"])

    def test_rule_9_task_id(self):
        pid = self.upgrade(task="not-a-task")
        self.assert_console(pid, "no valid task id")
        core.reject(self.state, pid)
        first = self.upgrade(task="UNITY-20261009-020")
        self.assertIn(first, self.state["approvals"])
        pid = self.upgrade(version="1.0+unity3", demo_sha="e" * 64, lib_sha="f" * 64, task="UNITY-20261009-020",
                           now=self.now + timedelta(hours=1))
        self.assert_console(pid, "UNITY-20261009-020 was already signed automatically once")

    def test_rule_10_policy_missing_malformed_or_off(self):
        for label, policy in (("off", dict(POLICY, auto_approve=False)), ("no schema", dict(POLICY, schema=2)),
                              ("max_sources 2", dict(POLICY, max_sources=2)), ("bool number", dict(POLICY, max_per_utc_day=True)),
                              ("unreadable", {"schema": 1, "auto_approve": False, "_problem": "policy: cannot read policy.json"}),
                              ("not an object", [1])):
            with self.subTest(policy=label):
                pid = self.upgrade(policy=policy, task=f"UNITY-20261009-0{30 + len(label) % 10}")
                self.assert_console(pid, "policy")
                core.reject(self.state, pid)
        # no policy at all (the service of phase 4): nothing automatic, no verdict stored
        pid = self.upgrade(policy=None)
        self.assertIn(pid, self.state["proposals"])
        self.assertNotIn("policy", self.state["proposals"][pid])

    def test_proposals_are_idempotent(self):
        pid = self.upgrade(policy=dict(POLICY, auto_approve=False))
        again = self.upgrade(policy=dict(POLICY, auto_approve=False), now=self.now + timedelta(minutes=1))
        self.assertEqual(pid, again)
        self.assertEqual(len(self.state["proposals"]), 1)
        core.approve(self.state, pid)
        self.assertEqual(self.upgrade(now=self.now + timedelta(minutes=2)), pid)  # the approval is returned
        self.assertEqual(core.proposal_status(self.state, pid), {"status": "approved", "approved_by": "May", "reasons": []})

    def test_deb_control_must_describe_its_row(self):
        """Verifier R1: a .deb whose own control names another package, version,
        architecture or source refuses the proposal (and adopt-live)."""
        def checker_with(control):
            def check(fields):
                found = SCRIPTS_A if fields["Package"] == "demo" else {}
                return ("scripts: postinst" if found else "no scripts"), found, dict(
                    {"Package": fields["Package"], "Version": fields["Version"], "Architecture": fields["Architecture"]}, **control)
            return check
        text = self.base_text + "\n" + stanza("demo", "1.0+unity2", "c" * 64, "demo") + "\n" + stanza("libdemo1", "1.0+unity2", "d" * 64, "demo")
        for label, control in (("package", {"Package": "evil"}), ("version", {"Version": "9"}),
                               ("architecture", {"Architecture": "all"}), ("source", {"Source": "other"})):
            with self.subTest(case=label):
                with self.assertRaises(core.Refused):
                    core.propose(self.state, TEMPLATE, files_for(text), "UNITY-20261009-050",
                                 checker_with(control), self.now, policy=POLICY)
        pid = core.propose(self.state, TEMPLATE, files_for(text), "UNITY-20261009-051", checker_with({"Source": "demo"}), self.now, policy=POLICY)
        self.assertIn(pid, self.state["approvals"])
        state = core.new_state()
        with self.assertRaises(core.Refused):
            core.adopt_live(state, TEMPLATE, files_for(self.base_text), aptly_release(files_for(self.base_text)),
                            checker_with({"Package": "evil"}), T0)

    def test_auto_signed_history_is_pruned_after_two_days(self):
        self.state["auto_signed"] = [{"at": (self.now - timedelta(days=3)).isoformat(), "task_id": "UNITY-20261001-001",
                                      "pid": "x", "set_id": "s", "shown": True}]
        pid = self.upgrade(task="UNITY-20261001-001")  # the same id, three days later: history pruned, routine
        self.assertIn(pid, self.state["approvals"])
        self.assertEqual([h["task_id"] for h in self.state["auto_signed"]], ["UNITY-20261001-001"])

    def test_version_compare_against_dpkg(self):
        table = json.loads((ROOT / "scripts" / "tests" / "data" / "dpkg_version_order.json").read_text())
        self.assertGreater(len(table["pairs"]), 3000)
        for a, b, verdict in table["pairs"]:
            r = core.version_compare(a, b)
            self.assertEqual("lt" if r < 0 else "eq" if r == 0 else "gt", verdict, f"{a} vs {b}")

    def test_adopt_live(self):
        state = core.new_state()
        files = files_for(self.base_text)
        served = aptly_release(files)
        with self.assertRaises(core.Refused):  # a .deb reader without maps
            core.adopt_live(state, TEMPLATE, files, served, deb_ok, T0)
        with self.assertRaises(core.Refused):  # a Release the signer would not build
            core.adopt_live(state, TEMPLATE, files, served.replace(b"Suite: resolute", b"Suite: other"), MappedDebs({}), T0)
        summary = core.adopt_live(state, TEMPLATE, files, served, MappedDebs({"demo": SCRIPTS_A}), T0)
        self.assertEqual((summary["entries"], summary["with_scripts"], summary["sources"]), (2, 1, ["demo"]))
        self.assertEqual(core.live_scripts(state)[("main/binary-amd64/Packages", "demo", "1.0+unity1", "amd64")], SCRIPTS_A)
        with self.assertRaises(core.Refused):  # once
            core.adopt_live(state, TEMPLATE, files, served, MappedDebs({"demo": SCRIPTS_A}), T0)
        with self.assertRaises(core.Refused):  # nothing signed yet
            core.current_trio(state)
        # the re-sign of the adopted set works (May's cut-over under the new key); until it, nothing is automatic
        self.state = state
        pid = self.upgrade()
        self.assert_console(pid, "nothing signed by this signer has gone live yet")
        core.reject(state, pid)
        trio = core.resign(state, TEMPLATE, self.backend, self.now)
        self.assertIsNone(core.compare_release(served, trio["release"]))
        self.assertEqual(core.current_trio(state), trio)
        pid = self.upgrade(now=self.now + timedelta(minutes=1))
        self.assertIn(pid, state["approvals"])


if __name__ == "__main__":
    unittest.main()
