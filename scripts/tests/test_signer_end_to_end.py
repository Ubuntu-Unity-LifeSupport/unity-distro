#!/usr/bin/env python3
"""End-to-end test of the aptly-signer (UNITY-20260929-021): the real service
(signer/aptly_signer.py) with a real gpg key, the real gpg stand-in called as
aptly 1.6.2 calls gpg, and the real client, against a fake repository server
on localhost. No aptly is run.

The key is a throwaway key in a temporary GNUPGHOME (coordinator, 2026-09-29):
mkdtemp with mode 0700, an explicit --homedir for gpg and gpgconf,
`gpgconf --homedir X --kill all` and removal in teardown, and a check that
~/.gnupg (file list and mtimes) is untouched.
Run: python3 -m unittest discover -s scripts/tests
"""

import base64
import bz2
import contextlib
from datetime import datetime, timedelta, timezone
import functools
import gzip
import hashlib
import http.server
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "signer"))
sys.path.insert(0, str(ROOT / "scripts"))
import signer_core as core  # noqa: E402
import aptly_signer  # noqa: E402
import signer_client  # noqa: E402

STANDIN = ROOT / "scripts" / "gpg_standin.py"
TEMPLATE_FILE = ROOT / "signer" / "release-template.json"
TEMPLATE = json.loads(TEMPLATE_FILE.read_text())
TASK = "UNITY-20260929-021"


def snapshot(path):
    """File list and mtimes of a directory, without running gpg on it."""
    path = Path(path)
    if not path.exists():
        return None
    return sorted((str(p.relative_to(path)), p.lstat().st_mtime_ns) for p in path.rglob("*"))


def serve(server):
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return thread


class SignerEndToEndTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gnupg_before = snapshot(Path.home() / ".gnupg")
        cls.home = Path(tempfile.mkdtemp(prefix="signer-test-gnupg-"))
        os.chmod(cls.home, 0o700)
        gpg = ["gpg", "--homedir", str(cls.home), "--batch", "--pinentry-mode", "loopback", "--passphrase", ""]
        env = dict(os.environ, GNUPGHOME=str(cls.home))
        subprocess.run(gpg + ["--quick-gen-key", "aptly-signer test <test@example.invalid>", "ed25519", "sign", "0"],
                       check=True, capture_output=True, env=env)
        listing = subprocess.run(["gpg", "--homedir", str(cls.home), "--with-colons", "--list-secret-keys"],
                                 check=True, capture_output=True, text=True, env=env).stdout
        cls.fpr = next(l.split(":")[9] for l in listing.splitlines() if l.startswith("fpr:"))
        cls.keyring = cls.home / "signer-pub.gpg"
        cls.keyring.write_bytes(subprocess.run(["gpg", "--homedir", str(cls.home), "--export", cls.fpr],
                                               check=True, capture_output=True, env=env).stdout)

    @classmethod
    def tearDownClass(cls):
        subprocess.run(["gpgconf", "--homedir", str(cls.home), "--kill", "all"], capture_output=True)
        shutil.rmtree(cls.home)

    def test_zz_user_gnupg_untouched(self):
        self.assertEqual(snapshot(Path.home() / ".gnupg"), self.gnupg_before)

    # -- fixture ------------------------------------------------------------------

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.public = self.base / "public"
        self.dist = self.public / "dists" / "resolute"
        self.dist.mkdir(parents=True)
        self.debs = {"demo": self.make_deb("demo", postinst=True), "libdemo1": self.make_deb("libdemo1")}
        # the fake :8080 serves the public root
        handler = functools.partial(QuietHandler, directory=str(self.public))
        self.repo = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        serve(self.repo)
        self.config = {"bind": "127.0.0.1", "port": 0, "state": str(self.base / "state.json"),
                       "template": str(TEMPLATE_FILE), "gnupghome": str(self.home), "fingerprint": self.fpr,
                       "keyring": str(self.keyring), "repo_base": f"http://127.0.0.1:{self.repo.server_port}",
                       "timeout": 10, "max_body": 16 * 1024 * 1024, "max_deb": 1024 * 1024, "distribution": "resolute"}
        self.assertEqual(aptly_signer.console(self.config, ["init"], out=io.StringIO()), 0)
        self.signer = aptly_signer.make_server(self.config)
        serve(self.signer)
        url = f"http://127.0.0.1:{self.signer.server_port}"
        (self.base / "standin.json").write_text(json.dumps({"url": url, "timeout": 20,
                                                            "store": str(self.base / "switch")}))
        self.client = {"url": url, "timeout": 20, "public_root": str(self.public), "distribution": "resolute",
                       "keyring": str(self.keyring), "store": str(self.base / "switch"),
                       "marker_dir": str(self.base / "publish-records"), "log": str(self.base / "AGENTS-LOG.md")}
        self.env = dict(os.environ, APTLY_SIGNER_STANDIN_CONFIG=str(self.base / "standin.json"))

    def tearDown(self):
        self.signer.shutdown()
        self.signer.server_close()
        self.repo.shutdown()
        self.repo.server_close()
        self.tmp.cleanup()

    def make_deb(self, name, postinst=False):
        root = self.base / f".deb-{name}"
        (root / "DEBIAN").mkdir(parents=True)
        (root / "DEBIAN" / "control").write_text(
            f"Package: {name}\nVersion: 1.0+unity1\nArchitecture: amd64\nMaintainer: t <t@example.com>\nDescription: t\n")
        if postinst:
            (root / "DEBIAN" / "postinst").write_text("#!/bin/sh\nexit 0\n")
            os.chmod(root / "DEBIAN" / "postinst", 0o755)
        rel = f"pool/main/d/demo/{name}_1.0+unity1_amd64.deb"
        path = self.public / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["dpkg-deb", "--root-owner-group", "--build", str(root), str(path)], check=True, capture_output=True)
        return rel

    def packages(self, extra=""):
        stanzas = []
        for name, rel in sorted(self.debs.items()):
            data = (self.public / rel).read_bytes()
            stanzas.append(f"Package: {name}\nVersion: 1.0+unity1\nArchitecture: amd64\nMaintainer: t <t@example.com>\n"
                           f"Filename: {rel}\nSize: {len(data)}\nSHA256: {hashlib.sha256(data).hexdigest()}\n"
                           f"Description: t{extra}\n")
        return ("\n".join(stanzas)).encode()

    def index_set(self, raw, gzip_mtime=0):
        return {"main/binary-amd64/Packages": raw,
                "main/binary-amd64/Packages.gz": gzip.compress(raw, mtime=gzip_mtime),
                "main/binary-amd64/Packages.bz2": bz2.compress(raw),
                "main/binary-amd64/Release": core.component_release(TEMPLATE, "main", "amd64")}

    def write_tree(self, top, files):
        for rel, data in files.items():
            path = top / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

    def rehearsal(self, raw):
        """A rehearsal (proposal) publication: its dists and its pool."""
        top = self.base / f"rehearsal-{hashlib.sha256(raw).hexdigest()[:8]}"
        self.write_tree(top / "dists" / "resolute", self.index_set(raw, gzip_mtime=1))
        shutil.copytree(self.public / "pool", top / "pool", dirs_exist_ok=True)
        return top

    def propose_and_approve(self, raw):
        pid = signer_client.propose(self.client, self.rehearsal(raw), TASK)
        out = io.StringIO()
        self.assertEqual(aptly_signer.console(self.config, ["approve", pid], out=out, confirm=lambda _: "approve"), 0)
        return pid, out.getvalue()

    def aptly_switch(self, raw, date=None, standin_ok=True):
        """What aptly 1.6.2 does at a switch (deb/index_files.go Finalize): index
        and Release temporary files in one directory, Release put into storage,
        gpg called for Release.gpg then InRelease, those put into storage."""
        files = self.index_set(raw, gzip_mtime=2)  # the live gzip bytes differ from the rehearsal's
        own = core.build_release(TEMPLATE, files, date or datetime.now(timezone.utc))
        release = b"\n".join(l for l in own.split(b"\n") if not l.startswith(b"Valid-Until:"))
        tmp = self.base / f"aptly-tmp-{hashlib.sha256(release).hexdigest()[:8]}"
        tmp.mkdir()
        for rel, data in files.items():
            (tmp / rel.replace("/", "_")).write_bytes(data)
        (tmp / "Release").write_bytes(release)
        results = [self.standin(tmp, "--detach-sign", tmp / "Release.gpg"), self.standin(tmp, "--clearsign", tmp / "InRelease")]
        if standin_ok:
            for r in results:
                self.assertEqual(r.returncode, 0, r.stderr)
            self.write_tree(self.dist, files)
            (self.dist / "Release").write_bytes(release)
            (self.dist / "Release.gpg").write_bytes((tmp / "Release.gpg").read_bytes())
            (self.dist / "InRelease").write_bytes((tmp / "InRelease").read_bytes())
        return release, tmp, results

    def standin(self, tmp, mode, dest, extra=()):
        argv = ["-o", str(dest), "--digest-algo", "SHA256"] + (["--armor"] if mode == "--detach-sign" else []) + [
            "--yes", "--no-auto-check-trustdb", "--no-default-keyring", "--keyring", "/nonexistent/trustedkeys.gpg",
            "-u", "0x0000", "--pinentry-mode", "loopback", "--passphrase", "secret-not-forwarded",
            "--no-tty", "--batch", *extra, mode, str(tmp / "Release")]
        return subprocess.run([sys.executable, str(STANDIN), *argv], capture_output=True, text=True, env=self.env, timeout=60)

    def gpgv(self, *args):
        return subprocess.run(["gpgv", "--keyring", str(self.keyring), *map(str, args)], capture_output=True).returncode == 0

    # -- the flow -------------------------------------------------------------------

    def test_full_cycle(self):
        raw = self.packages()
        pid, shown = self.propose_and_approve(raw)
        self.assertIn("scripts: postinst", shown)          # read from the .deb sent in /propose
        self.assertIn("no scripts", shown)
        self.assertIn("task (claimed by builder): UNITY-20260929-021", shown)
        release, tmp, _ = self.aptly_switch(raw)
        stored = list((self.base / "switch").glob("*.json"))
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0].stat().st_mode & 0o777, 0o600)
        # right after the switch: InRelease valid, carries Valid-Until; the detached pair fails closed
        out = self.base / "inrelease.out"
        self.assertTrue(self.gpgv("--output", out, self.dist / "InRelease"))
        self.assertIn(b"Valid-Until:", out.read_bytes())
        self.assertFalse(self.gpgv(self.dist / "Release.gpg", self.dist / "Release"))
        # the refresh closes the window
        self.assertEqual(signer_client.refresh(self.client, TASK, switch=True), 0)
        self.assertTrue(self.gpgv(self.dist / "Release.gpg", self.dist / "Release"))
        self.assertEqual(list((self.base / "switch").glob("*.json")), [])  # deleted after install
        # live: the signer fetches InRelease itself
        answer = signer_client.call(self.client, "POST", "/live", {})
        self.assertTrue(answer["ok"])
        # the scheduled re-sign and the cadence refresh
        before = core.release_date((self.dist / "Release").read_text())
        aptly_signer.resign_command(self.config, now=datetime.now(timezone.utc) + timedelta(days=1))
        self.assertEqual(signer_client.refresh(self.client, TASK, switch=False), 0)
        self.assertGreater(core.release_date((self.dist / "Release").read_text()), before)
        self.assertTrue(self.gpgv(self.dist / "Release.gpg", self.dist / "Release"))

    def test_standin_passphrase_not_forwarded_and_version(self):
        r = subprocess.run([sys.executable, str(STANDIN), "--version"], capture_output=True, text=True)
        self.assertRegex(r.stdout, r"\(GnuPG.*\) (2).(\d)")   # aptly's detection regex
        # aptly's GpgSigner.Init(): non-empty output, exit 0, no config and no signer needed
        env = dict(self.env, APTLY_SIGNER_STANDIN_CONFIG=str(self.base / "no-such-config.json"))
        r = subprocess.run([sys.executable, str(STANDIN), "--list-keys", "--dry-run", "--no-auto-check-trustdb"],
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0)
        self.assertTrue(r.stdout.strip())
        r = subprocess.run([sys.executable, str(STANDIN), "--list-keys"], capture_output=True, text=True, env=env)
        self.assertNotEqual(r.returncode, 0)  # only the exact probe
        (self.base / "keyed.json").write_text(json.dumps({"url": "http://127.0.0.1:9", "key_id": self.fpr}))
        env = dict(self.env, APTLY_SIGNER_STANDIN_CONFIG=str(self.base / "keyed.json"))
        r = subprocess.run([sys.executable, str(STANDIN), "--list-keys", "--dry-run", "--no-auto-check-trustdb"],
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0)
        self.assertIn(self.fpr, r.stdout)  # the key id from the config
        raw = self.packages()
        self.propose_and_approve(raw)
        _, _, results = self.aptly_switch(raw)
        self.assertNotIn("secret-not-forwarded", "".join(r.stderr for r in results))
        with open(self.config["state"]) as state:
            self.assertNotIn("secret-not-forwarded", state.read())

    def test_standin_trace_for_the_rehearsal(self):
        trace = self.base / "trace.jsonl"
        (self.base / "standin.json").write_text(json.dumps({"url": "http://127.0.0.1:9", "timeout": 2,
                                                            "store": str(self.base / "switch"), "trace": str(trace)}))
        _, tmp, _ = self.aptly_switch(self.packages(), standin_ok=False)
        lines = [json.loads(l) for l in trace.read_text().splitlines()]
        self.assertEqual(len(lines), 2)
        self.assertIn("--detach-sign", lines[0]["argv"])
        self.assertIn("***", lines[0]["argv"])
        self.assertNotIn("secret-not-forwarded", trace.read_text())
        self.assertIn("main_binary-amd64_Packages.gz", [entry[0] for entry in lines[0]["listing"]])

    def test_standin_refusals_write_nothing(self):
        raw = self.packages()
        release, tmp, results = self.aptly_switch(raw, standin_ok=False)  # not approved
        self.assertTrue(all(r.returncode != 0 for r in results))
        self.assertFalse((tmp / "Release.gpg").exists() or (tmp / "InRelease").exists())
        self.assertEqual(list((self.base / "switch").glob("*.json")) if (self.base / "switch").exists() else [], [])
        self.propose_and_approve(raw)
        cases = {"unknown option": ["--sign-with-anything"], "two files": [str(tmp / "Release")]}
        for label, extra in cases.items():
            with self.subTest(case=label):
                r = self.standin(tmp, "--clearsign", tmp / "InRelease", extra=extra)
                self.assertNotEqual(r.returncode, 0)
                self.assertFalse((tmp / "InRelease").exists())
        victim = tmp / "main_binary-amd64_Packages.gz"
        data = victim.read_bytes()
        victim.unlink()
        r = self.standin(tmp, "--clearsign", tmp / "InRelease")  # a listed file missing
        self.assertNotEqual(r.returncode, 0)
        (self.base / "elsewhere.gz").write_bytes(data)
        victim.symlink_to(self.base / "elsewhere.gz")
        r = self.standin(tmp, "--clearsign", tmp / "InRelease")  # a symlink
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse((tmp / "InRelease").exists())

    def test_signer_unreachable(self):
        (self.base / "standin.json").write_text(json.dumps({"url": "http://127.0.0.1:9", "timeout": 2,
                                                            "store": str(self.base / "switch")}))
        raw = self.packages()
        _, tmp, results = self.aptly_switch(raw, standin_ok=False)
        self.assertTrue(all(r.returncode != 0 for r in results))
        self.assertFalse((tmp / "InRelease").exists())

    def test_refresh_failure_marks_and_writes_nothing(self):
        raw = self.packages()
        self.propose_and_approve(raw)
        self.aptly_switch(raw)
        (self.dist / "main/binary-amd64/Packages.bz2").write_bytes(b"not the index")  # served index changed
        served = {n: (self.dist / n).read_bytes() for n in ("Release", "Release.gpg", "InRelease")}
        with self.assertRaises(core.Refused):
            signer_client.refresh(self.client, TASK, switch=True)
        self.assertEqual({n: (self.dist / n).read_bytes() for n in served}, served)
        self.assertTrue((self.base / "publish-records" / f"{TASK}.refresh-failed").exists())
        self.assertIn(f"REFRESH-FAILED {TASK}", (self.base / "AGENTS-LOG.md").read_text())

    def test_stale_and_wrong_set_trios_refused(self):
        raw1 = self.packages()
        self.propose_and_approve(raw1)
        self.aptly_switch(raw1)
        stored1 = next((self.base / "switch").glob("*.json")).read_text()
        signer_client.refresh(self.client, TASK, switch=True)
        signer_client.call(self.client, "POST", "/live", {})
        raw2 = self.packages(extra=" v2")
        self.propose_and_approve(raw2)
        release2, _, _ = self.aptly_switch(raw2, date=datetime.now(timezone.utc) + timedelta(minutes=1))
        # before /live, the cadence refresh would bring the old set's trio: refused (R2), nothing written
        with self.assertRaises(core.Refused):
            signer_client.refresh(self.client, TASK, switch=False)
        # a trio stored at an earlier switch, put under the served Release's key: refused
        key = hashlib.sha256(release2).hexdigest()
        (self.base / "switch" / f"{key}.json").write_text(stored1)
        with self.assertRaises(core.Refused):
            signer_client.refresh(self.client, TASK, switch=True)

    def test_gpg_by_absolute_path_only(self):
        with self.assertRaises(core.Refused):
            aptly_signer.GpgBackend(self.home, self.fpr, self.keyring, gpg="gpg")
        with self.assertRaises(core.Refused):
            aptly_signer.GpgBackend(self.home, self.fpr, self.keyring, gpgv="gpgv")
        # a stand-in first on PATH does not reach the signer's signing
        fake = self.base / "bin"
        fake.mkdir()
        (fake / "gpg").write_text("#!/bin/sh\nexit 99\n")
        os.chmod(fake / "gpg", 0o755)
        saved = os.environ["PATH"]
        os.environ["PATH"] = f"{fake}:{saved}"
        try:
            backend = aptly_signer.GpgBackend(self.home, self.fpr, self.keyring)
            self.assertTrue(backend.verify_detached(backend.sign_detached(b"x"), b"x"))
        finally:
            os.environ["PATH"] = saved

    def post_propose(self, raw, debs):
        files = {k: base64.b64encode(v).decode() for k, v in self.index_set(raw).items()}
        return signer_client.call(self.client, "POST", "/propose",
                                  {"task_id": TASK, "files": files,
                                   "debs": {k: base64.b64encode(v).decode() for k, v in debs.items()}})

    def test_proposal_debs_missing_extra_mismatched(self):
        """Amendment (b): the .debs travel in /propose; the signer checks them
        against the Packages it validated itself."""
        raw = self.packages()
        all_debs = {rel: (self.public / rel).read_bytes() for rel in self.debs.values()}
        demo = self.debs["demo"]
        cases = {
            "missing": {k: v for k, v in all_debs.items() if k != demo},
            "extra": dict(all_debs, **{"pool/main/e/extra/extra_1_all.deb": b"x"}),
            "mismatched": dict(all_debs, **{demo: all_debs[demo] + b"x"}),
        }
        for label, debs in cases.items():
            with self.subTest(case=label):
                with self.assertRaises(core.Refused):
                    self.post_propose(raw, debs)
        self.assertTrue(self.post_propose(raw, all_debs)["ok"])

    def test_changed_entry_same_key_needs_its_deb(self):
        """An entry changed under the same name, version and arch (other bytes)
        is new content: its .deb is required."""
        raw = self.packages()
        self.propose_and_approve(raw)
        self.aptly_switch(raw)
        signer_client.refresh(self.client, TASK, switch=True)
        signer_client.call(self.client, "POST", "/live", {})
        rel = self.debs["libdemo1"]
        (self.public / rel).unlink()
        shutil.rmtree(self.base / ".deb-libdemo1")
        self.debs["libdemo1"] = self.make_deb("libdemo1", postinst=True)  # same name/version/arch, new bytes
        raw2 = self.packages()
        with self.assertRaises(core.Refused):  # without the new .deb
            self.post_propose(raw2, {})
        answer = self.post_propose(raw2, {rel: (self.public / rel).read_bytes()})
        self.assertTrue(answer["ok"])
        out = io.StringIO()
        aptly_signer.console(self.config, ["show", answer["proposal"]], out=out)
        self.assertIn("changed  libdemo1", out.getvalue())
        self.assertIn("scripts: postinst", out.getvalue())

    def crafted_deb(self, compress, split=True, end_blocks=True):
        """A .deb whose control archive hides a postinst from a one-stream reader:
        control in one compressed stream, postinst in a second (dpkg reads both
        for gzip). split=False: one stream; end_blocks=False: a tar without its
        end-of-archive marker."""
        import tarfile as tf
        def tar_of(members, end):
            buf = io.BytesIO()
            with tf.open(fileobj=buf, mode="w", format=tf.USTAR_FORMAT) as t:
                for name, data, mode in members:
                    info = tf.TarInfo(name); info.size = len(data); info.mode = mode
                    t.addfile(info, io.BytesIO(data))
            raw = buf.getvalue()
            return raw if end else raw.rstrip(b"\0")[:((len(raw.rstrip(b"\0")) + 511) // 512) * 512]
        control = ("./control", b"Package: demo\nVersion: 1\nArchitecture: amd64\nMaintainer: t <t@e>\nDescription: t\n", 0o644)
        postinst = ("./postinst", b"#!/bin/sh\nexit 0\n", 0o755)
        if split:
            body = compress(tar_of([control], False)) + compress(tar_of([postinst], True))
        else:
            body = compress(tar_of([control, postinst] if end_blocks else [control], end_blocks))
        name = {gzip.compress: b"control.tar.gz", }.get(compress, b"control.tar.xz")
        def member(n, data):
            header = n.ljust(16) + b"0".ljust(12) + b"0".ljust(6) + b"0".ljust(6) + b"100644".ljust(8) + str(len(data)).encode().ljust(10) + b"`\n"
            return header + data + (b"\n" if len(data) % 2 else b"")
        return b"!<arch>\n" + member(b"debian-binary", b"2.0\n") + member(name, body) + member(b"data.tar.gz", gzip.compress(b""))

    def test_hidden_postinst_in_a_second_stream_is_refused(self):
        import lzma
        for label, compress in (("gz", functools.partial(gzip.compress, mtime=0)), ("xz", lzma.compress)):
            with self.subTest(compression=label):
                deb = self.crafted_deb(compress if label == "xz" else gzip.compress)
                with self.assertRaises(core.Refused):
                    aptly_signer.control_members(deb)
        honest = self.crafted_deb(gzip.compress, split=False)
        self.assertIn("postinst", aptly_signer.control_members(honest))
        with self.assertRaises(core.Refused):  # a tar without its end-of-archive marker
            aptly_signer.control_members(self.crafted_deb(gzip.compress, split=False, end_blocks=False))

    def control_tar(self, members):
        """A terminated control tar from (name, type, data, linkname) tuples."""
        import tarfile as tf
        buf = io.BytesIO()
        with tf.open(fileobj=buf, mode="w", format=tf.USTAR_FORMAT) as t:
            for name, kind, data, link in members:
                info = tf.TarInfo(name)
                info.type, info.linkname, info.mode = kind, link, 0o755
                info.size = len(data) if kind == tf.REGTYPE else 0
                t.addfile(info, io.BytesIO(data) if kind == tf.REGTYPE else None)
        return buf.getvalue()

    def deb_with_control(self, control_tar):
        def member(n, data):
            header = n.ljust(16) + b"0".ljust(12) + b"0".ljust(6) + b"0".ljust(6) + b"100644".ljust(8) + str(len(data)).encode().ljust(10) + b"`\n"
            return header + data + (b"\n" if len(data) % 2 else b"")
        return (b"!<arch>\n" + member(b"debian-binary", b"2.0\n") + member(b"control.tar.gz", gzip.compress(control_tar))
                + member(b"data.tar.gz", gzip.compress(b"")))

    def test_control_members_only_top_level_regular_files(self):
        """Verifier round 2: ./x -> . then ./x/preinst hid a preinst that GNU tar
        writes through the symlink. Only regular files at the top level pass."""
        import tarfile as tf
        control = ("./control", tf.REGTYPE, b"Package: demo\n", "")
        cases = {
            "symlink dir then script through it": [control, ("./x", tf.SYMTYPE, b"", "."), ("./x/preinst", tf.REGTYPE, b"echo pwned\n", "")],
            "symlink named postinst": [control, ("./postinst", tf.SYMTYPE, b"", "control")],
            "hardlink named postinst": [control, ("./postinst", tf.LNKTYPE, b"", "./control")],
            "subdirectory": [control, ("./sub", tf.DIRTYPE, b"", ""), ("./sub/postinst", tf.REGTYPE, b"x", "")],
            "dot-dot name": [control, ("./x/../postinst", tf.REGTYPE, b"x", "")],
            "device": [control, ("./null", tf.CHRTYPE, b"", "")],
            "trailing space": [control, ("./postinst ", tf.REGTYPE, b"x", "")],
        }
        for label, members in cases.items():
            with self.subTest(case=label):
                with self.assertRaises(core.Refused):
                    aptly_signer.control_members(self.deb_with_control(self.control_tar(members)))
        ok = self.control_tar([("./", tf.DIRTYPE, b"", ""), control, ("./postinst", tf.REGTYPE, b"#!/bin/sh\n", "")])
        self.assertEqual(aptly_signer.control_members(self.deb_with_control(ok)), ["control", "postinst"])

    def test_extended_tar_headers_refused(self):
        """Verifier round 3: tarfile and GNU tar pick different names when pax
        or GNU long-name headers precede a member. Only plain ustar passes."""
        import tarfile as tf
        long_name = "./" + "c" * 120
        for label, fmt, members in (
                ("pax x header", tf.PAX_FORMAT, [("./control", b"x"), (long_name, b"x")]),
                ("pax path=preinst", tf.PAX_FORMAT, [("./control", b"x"), ("./preinst\u00e9", b"x")]),
                ("GNU long name", tf.GNU_FORMAT, [("./control", b"x"), (long_name, b"x")])):
            with self.subTest(case=label):
                buf = io.BytesIO()
                with tf.open(fileobj=buf, mode="w", format=fmt) as t:
                    for name, data in members:
                        info = tf.TarInfo(name); info.size = len(data)
                        t.addfile(info, io.BytesIO(data))
                with self.assertRaises(core.Refused):
                    aptly_signer.control_members(self.deb_with_control(buf.getvalue()))
        # a broken header checksum, and a non-octal size
        good = bytearray(self.control_tar([("./control", tf.REGTYPE, b"x", "")]))
        bad = bytearray(good); bad[0] ^= 1
        with self.assertRaises(core.Refused):
            aptly_signer.control_members(self.deb_with_control(bytes(bad)))
        # the Verifier's two crafted .debs, if present
        scratch = Path("/tmp/claude-1000/-home-claude/a9056178-c052-41ac-b853-73b5663b476b/scratchpad/r2t")
        for name in ("twox.deb", "Lctl2_xpreinst.deb"):
            if (scratch / name).exists():
                with self.subTest(deb=name):
                    with self.assertRaises(core.Refused):
                        aptly_signer.control_members((scratch / name).read_bytes())

    def test_refresh_write_order(self):
        raw = self.packages()
        self.propose_and_approve(raw)
        self.aptly_switch(raw)
        order = []
        real = os.replace
        def spy(src, dst):
            order.append(Path(dst).name)
            return real(src, dst)
        signer_client.os.replace = spy
        try:
            signer_client.refresh(self.client, TASK, switch=True)
        finally:
            signer_client.os.replace = real
        self.assertEqual(order, ["Release", "Release.gpg", "InRelease"])

    def test_refresh_refuses_an_unlisted_served_index(self):
        raw = self.packages()
        self.propose_and_approve(raw)
        self.aptly_switch(raw)
        (self.dist / "main/binary-amd64/Packages.xz").write_bytes(b"not listed")
        with self.assertRaises(core.Refused):
            signer_client.refresh(self.client, TASK, switch=True)

    def test_non_object_json_body(self):
        import urllib.request, urllib.error
        url = f"http://127.0.0.1:{self.signer.server_port}/propose"
        request = urllib.request.Request(url, data=b"[1, 2]", headers={"Content-Type": "application/json"})
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=10)
        self.assertEqual(caught.exception.code, 409)
        caught.exception.close()

    def test_control_archive_decompression_cap(self):
        deb = (self.public / self.debs["demo"]).read_bytes()
        with self.assertRaises(core.Refused):
            aptly_signer.control_members(deb, limit=10)
        self.assertIn("control", aptly_signer.control_members(deb))

    def test_pinned_fingerprint_refuses_another_key(self):
        other = aptly_signer.GpgBackend(self.home, "0" * 40, self.keyring)
        with self.assertRaises(core.Refused):
            other.sign_detached(b"x")

    def test_http_limits(self):
        import urllib.request, urllib.error
        url = f"http://127.0.0.1:{self.signer.server_port}/sign"
        big = urllib.request.Request(url, data=b"{}", headers={"Content-Length": str(10 ** 12)})
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(big, timeout=10)
        self.assertEqual(caught.exception.code, 409)
        caught.exception.close()
        state_before = Path(self.config["state"]).read_text()
        Path(self.config["state"]).write_text("{corrupt")
        with self.assertRaises(core.Refused):
            signer_client.call(self.client, "GET", "/current")
        Path(self.config["state"]).write_text(state_before)

    def test_deb_problems_refuse_the_proposal(self):
        raw = self.packages()
        cases = {
            # a .deb that differs from its Packages entry is refused by the signer
            "sha256 mismatch": lambda: (self.public / self.debs["demo"]).write_bytes(b"!<arch>\n" + b"x" * 100),
        }
        for label, damage in cases.items():
            with self.subTest(case=label):
                self.tearDown(); self.setUp()
                raw = self.packages()
                damage()
                with self.assertRaises(core.Refused):
                    signer_client.propose(self.client, self.rehearsal(raw), TASK)
        with self.assertRaises(core.Refused):
            aptly_signer.control_members(b"!<arch>\ncontrol.tar.gz  0           0     0     100644  10        `\nnotgzip!!!")


class RoutinePolicyEndToEndTest(SignerEndToEndTest):
    """Permission model phase 5 through the real service: the policy file next
    to the template, script maps read from the .debs sent in /propose, the
    console's view of automatic approvals, adopt-live and the re-sign cut-over."""

    def setUp(self):
        super().setUp()
        self.policy = self.base / "policy.json"
        self.policy.write_text(json.dumps({"schema": 1, "auto_approve": True, "max_sources": 1, "max_binary_records": 40,
                                           "min_interval_seconds": 600, "max_per_utc_day": 6}))
        self.config["policy"] = str(self.policy)

    def go_live(self, raw):
        """propose (console approval when not automatic), switch, refresh, /live."""
        answer = signer_client.propose_answer(self.client, self.rehearsal(raw), TASK)
        if answer["status"] != "approved":
            out = io.StringIO()
            self.assertEqual(aptly_signer.console(self.config, ["approve", answer["proposal"]], out=out, confirm=lambda _: "approve"), 0)
        self.aptly_switch(raw, date=datetime.now(timezone.utc) + timedelta(minutes=len(self.history)))
        self.history.append(raw)
        self.assertEqual(signer_client.refresh(self.client, TASK, switch=True), 0)
        self.assertTrue(signer_client.call(self.client, "POST", "/live", {})["ok"])
        return answer

    def new_version(self, name, version, postinst=False, source="demo"):
        root = self.base / f".deb-{name}-{version}"
        (root / "DEBIAN").mkdir(parents=True)
        (root / "DEBIAN" / "control").write_text(
            f"Package: {name}\nVersion: {version}\nArchitecture: amd64\nSource: {source}\nMaintainer: t <t@example.com>\nDescription: t\n")
        if postinst:
            (root / "DEBIAN" / "postinst").write_text("#!/bin/sh\nexit 0\n")
            os.chmod(root / "DEBIAN" / "postinst", 0o755)
        rel = f"pool/main/d/demo/{name}_{version}_amd64.deb"
        path = self.public / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["dpkg-deb", "--root-owner-group", "--build", str(root), str(path)], check=True, capture_output=True)
        data = path.read_bytes()
        return (f"Package: {name}\nVersion: {version}\nArchitecture: amd64\nSource: {source}\nMaintainer: t <t@example.com>\n"
                f"Filename: {rel}\nSize: {len(data)}\nSHA256: {hashlib.sha256(data).hexdigest()}\nDescription: t\n")

    def test_routine_upgrade_is_automatic_after_the_first_signing(self):
        self.history = []
        base = self.packages()  # demo (postinst) and libdemo1, both without a Source field: source = the name
        first = self.go_live(base)
        self.assertEqual(first["status"], "pending")  # rule 1/11: the first publication is May's
        self.assertIn("empty repository", " ".join(first["reasons"]))
        # one known source (demo), one version up, scripts unchanged: routine
        upgrade = base.decode() + "\n" + self.new_version("demo", "1.0+unity2", postinst=True, source="demo")
        answer = signer_client.propose_answer(self.client, self.rehearsal(upgrade.encode()), "UNITY-20261009-001")
        self.assertEqual((answer["status"], answer["approved_by"]), ("approved", "policy"), answer)
        out = io.StringIO()
        aptly_signer.console(self.config, ["list"], out=out)
        text = out.getvalue()
        self.assertIn("auto-approved", text)
        self.assertIn("UNITY-20261009-001", text)
        self.assertIn("added    demo amd64", text)
        self.assertIn("policy: auto_approve on", text)
        out = io.StringIO()
        aptly_signer.console(self.config, ["list"], out=out)
        self.assertNotIn("auto-approved", out.getvalue())  # shown once
        self.aptly_switch(upgrade.encode(), date=datetime.now(timezone.utc) + timedelta(minutes=5))
        self.assertEqual(signer_client.refresh(self.client, "UNITY-20261009-001", switch=True), 0)
        self.assertTrue(signer_client.call(self.client, "POST", "/live", {})["ok"])
        # a new source waits for the console, with the reason
        extra = upgrade + "\n" + self.new_version("other", "2.0", source="other")
        answer = signer_client.propose_answer(self.client, self.rehearsal(extra.encode()), "UNITY-20261009-002")
        self.assertEqual(answer["status"], "pending")
        self.assertTrue(any("other" in r and "not in last-live" in r for r in answer["reasons"]), answer)
        out = io.StringIO()
        aptly_signer.console(self.config, ["show", answer["proposal"]], out=out)
        self.assertIn("policy: not routine", out.getvalue())
        aptly_signer.console(self.config, ["reject", answer["proposal"]], out=io.StringIO())
        # a changed maintainer script waits: libdemo1 gains a postinst
        changed = upgrade + "\n" + self.new_version("libdemo1", "1.0+unity3", postinst=True, source="libdemo1")
        answer = signer_client.propose_answer(self.client, self.rehearsal(changed.encode()), "UNITY-20261009-003")
        self.assertEqual(answer["status"], "pending")
        self.assertTrue(any("maintainer scripts of libdemo1 amd64 differ" in r for r in answer["reasons"]), answer)
        # the kill switch
        self.policy.write_text(json.dumps({"schema": 1, "auto_approve": False, "max_sources": 1, "max_binary_records": 40,
                                           "min_interval_seconds": 600, "max_per_utc_day": 6}))
        routine = upgrade + "\n" + self.new_version("demo", "1.0+unity3", postinst=True, source="demo")
        answer = signer_client.propose_answer(self.client, self.rehearsal(routine.encode()), "UNITY-20261009-004")
        self.assertEqual(answer["status"], "pending")
        self.assertIn("automatic approval is off", " ".join(answer["reasons"]))
        aptly_signer.console(self.config, ["reject", answer["proposal"]], out=io.StringIO())  # a pending one is returned as is
        self.policy.unlink()  # a missing file approves nothing and says so
        answer = signer_client.propose_answer(self.client, self.rehearsal(routine.encode()), "UNITY-20261009-004")
        self.assertEqual(answer["status"], "pending")
        self.assertTrue(any("cannot read policy.json" in r for r in answer["reasons"]), answer)

    def test_deb_control_disagreeing_with_its_row_is_refused(self):
        """Verifier R1 through the service: a row that names a known binary but
        carries the bytes of another .deb."""
        self.history = []
        base = self.packages()
        self.go_live(base)
        # a live .deb's bytes under a new row: not read again, hence not routine (pending)
        other = (self.public / self.debs["libdemo1"]).read_bytes()
        rel = "pool/main/d/demo/demo_1.0+unity2_amd64.deb"
        (self.public / rel).write_bytes(other)
        row = (f"Package: demo\nVersion: 1.0+unity2\nArchitecture: amd64\nMaintainer: t <t@example.com>\n"
               f"Filename: {rel}\nSize: {len(other)}\nSHA256: {hashlib.sha256(other).hexdigest()}\nDescription: t\n")
        answer = signer_client.propose_answer(self.client, self.rehearsal(base + b"\n" + row.encode()), "UNITY-20261009-007")
        self.assertEqual(answer["status"], "pending")
        self.assertTrue(any("were not read" in r for r in answer["reasons"]), answer)
        aptly_signer.console(self.config, ["reject", answer["proposal"]], out=io.StringIO())
        # a new .deb whose own control says another package: refused outright
        evil = self.new_version("evil", "1.0+unity2", source="demo").replace("Package: evil\n", "Package: demo\n")
        with self.assertRaises(core.Refused) as caught:
            signer_client.propose_answer(self.client, self.rehearsal(base + b"\n" + evil.encode()), "UNITY-20261009-008")
        self.assertIn("does not describe it", str(caught.exception))

    def test_adopt_live_refuses_a_release_listing_contents(self):
        raw = self.packages()
        files = self.index_set(raw)
        self.write_tree(self.dist, files)
        own = core.build_release(TEMPLATE, files, datetime.now(timezone.utc)).decode()
        lines = [l for l in own.split("\n") if not l.startswith("Valid-Until:")]
        i = lines.index("SHA256:") + 1
        lines.insert(i, " " + "0" * 64 + "       10 main/Contents-amd64.gz")
        (self.dist / "Release").write_text("\n".join(lines))
        with self.assertRaises(core.Refused) as caught:
            aptly_signer.console(self.config, ["adopt-live"], out=io.StringIO(), confirm=lambda _: "adopt")
        self.assertIn("republish with -skip-contents", str(caught.exception))

    def test_adopt_live_and_the_resign_cutover(self):
        self.history = []
        raw = self.packages()
        files = self.index_set(raw)
        self.write_tree(self.dist, files)
        (self.dist / "Release").write_bytes(b"\n".join(l for l in core.build_release(TEMPLATE, files, datetime.now(timezone.utc)).split(b"\n")
                                                     if not l.startswith(b"Valid-Until:")))
        out = io.StringIO()
        self.assertEqual(aptly_signer.console(self.config, ["adopt-live"], out=out, confirm=lambda _: "no"), 1)
        self.assertIn("2 entries, 2 .debs read, sources: demo, libdemo1", out.getvalue())
        self.assertIn("not adopted", out.getvalue())
        out = io.StringIO()
        self.assertEqual(aptly_signer.console(self.config, ["adopt-live"], out=out, confirm=lambda _: "adopt"), 0)
        self.assertIn("adopted", out.getvalue())
        self.assertIn("1 with scripts", out.getvalue())
        with self.assertRaises(core.Refused):  # /current: nothing signed yet
            signer_client.call(self.client, "GET", "/current")
        # rule 11: a routine upgrade is not automatic before the first signing
        upgrade = raw.decode() + "\n" + self.new_version("demo", "1.0+unity2", postinst=True, source="demo")
        answer = signer_client.propose_answer(self.client, self.rehearsal(upgrade.encode()), "UNITY-20261009-005")
        self.assertEqual(answer["status"], "pending")
        self.assertIn("nothing signed by this signer has gone live yet", " ".join(answer["reasons"]))
        aptly_signer.console(self.config, ["reject", answer["proposal"]], out=io.StringIO())
        # May's cut-over path (a): re-sign the adopted content, install it on builder
        aptly_signer.resign_command(self.config, now=datetime.now(timezone.utc))
        self.assertEqual(signer_client.refresh(self.client, "cadence", switch=False), 0)
        self.assertTrue(self.gpgv(self.dist / "Release.gpg", self.dist / "Release"))
        out = self.base / "inrelease.out"
        self.assertTrue(self.gpgv("--output", out, self.dist / "InRelease"))
        self.assertIn(b"Valid-Until:", out.read_bytes())
        # now the same routine upgrade is automatic, and goes through the ordinary flow
        answer = signer_client.propose_answer(self.client, self.rehearsal(upgrade.encode()), "UNITY-20261009-006")
        self.assertEqual((answer["status"], answer["approved_by"]), ("approved", "policy"), answer)
        self.aptly_switch(upgrade.encode(), date=datetime.now(timezone.utc) + timedelta(minutes=5))
        self.assertEqual(signer_client.refresh(self.client, "UNITY-20261009-006", switch=True), 0)
        self.assertTrue(signer_client.call(self.client, "POST", "/live", {})["ok"])
        self.assertTrue(self.gpgv(self.dist / "Release.gpg", self.dist / "Release"))


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


if __name__ == "__main__":
    unittest.main()
