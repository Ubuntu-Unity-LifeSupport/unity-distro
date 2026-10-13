#!/usr/bin/env python3
"""UNITY-20260929-021 rehearsal: the local signer on 127.0.0.1 with a throwaway
key (coordinator's conditions: mkdtemp 0700, explicit --homedir, gpgconf kill
and removal at the end, ~/.gnupg untouched), plus a server of the rehearsal
public directory standing in for :8080.

  rehearsal_signer.py up <rehearsal dir> [<proposal public dir>]
                                             key, configs, state; serves until interrupted

TEMPORARY, rehearsal only (coordinator, 2026-09-29, deviation 4; not part of
the product): with a proposal public dir, the repository server stands for
:8080 by serving <rehearsal dir>/state/public first and the proposal
publication's public dir second, so that the signer finds a new .deb before
the switch. The product fix is design amendment (b): the .deb travels in
/propose.
  (Ctrl-C / SIGTERM)                         stops, kills gpg-agent of the temp home, removes it
"""

import json
import functools
import http.server
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import threading

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "signer"))
import aptly_signer  # noqa: E402


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def union_handler(first, second):
    """Serve from first, else from second (rehearsal only)."""
    class Union(Quiet):
        def translate_path(self, path):
            for root in (first, second):
                self.directory = str(root)
                candidate = super().translate_path(path)
                if Path(candidate).exists():
                    return candidate
            self.directory = str(first)
            return super().translate_path(path)
    return functools.partial(Union, directory=str(first))


def snapshot(path):
    return sorted((str(p.relative_to(path)), p.lstat().st_mtime_ns) for p in Path(path).rglob("*")) if Path(path).exists() else None


def main():
    work = Path(sys.argv[2]).resolve()
    public = work / "state" / "public"
    public.mkdir(parents=True, exist_ok=True)
    before = snapshot(Path.home() / ".gnupg")
    home = Path(tempfile.mkdtemp(prefix="signer-rehearsal-gnupg-"))
    os.chmod(home, 0o700)
    env = dict(os.environ, GNUPGHOME=str(home))
    gpg = ["/usr/bin/gpg", "--homedir", str(home), "--batch", "--pinentry-mode", "loopback", "--passphrase", ""]
    servers = []

    def cleanup(*_):
        for s in servers:
            s.shutdown()
        subprocess.run(["/usr/bin/gpgconf", "--homedir", str(home), "--kill", "all"], capture_output=True)
        shutil.rmtree(home, ignore_errors=True)
        after = snapshot(Path.home() / ".gnupg")
        print(f"cleanup: temp gnupg home removed: {not home.exists()}; ~/.gnupg unchanged: {after == before}", flush=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, cleanup)
    try:
        subprocess.run(gpg + ["--quick-gen-key", "aptly-signer rehearsal <rehearsal@example.invalid>", "ed25519", "sign", "0"],
                       check=True, capture_output=True, env=env)
        listing = subprocess.run(["/usr/bin/gpg", "--homedir", str(home), "--with-colons", "--list-secret-keys"],
                                 check=True, capture_output=True, text=True, env=env).stdout
        fpr = next(l.split(":")[9] for l in listing.splitlines() if l.startswith("fpr:"))
        keyring = work / "signer-pub.gpg"
        keyring.write_bytes(subprocess.run(["/usr/bin/gpg", "--homedir", str(home), "--export", fpr],
                                           check=True, capture_output=True, env=env).stdout)
        if len(sys.argv) > 3:
            handler = union_handler(public, Path(sys.argv[3]).resolve())
            print(f"TEMPORARY rehearsal-only repository view: {public} then {sys.argv[3]}", flush=True)
        else:
            handler = functools.partial(Quiet, directory=str(public))
        repo = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        config = {"bind": "127.0.0.1", "port": 0, "state": str(work / "signer-state.json"),
                  "template": str(REPO / "signer" / "release-template.json"), "gnupghome": str(home),
                  "fingerprint": fpr, "keyring": str(keyring), "repo_base": f"http://127.0.0.1:{repo.server_port}",
                  "timeout": 30, "max_body": 96 * 1024 * 1024, "max_deb": 64 * 1024 * 1024, "distribution": "resolute"}
        (work / "signer-config.json").write_text(json.dumps(config, indent=1))
        if not Path(config["state"]).exists():
            aptly_signer.console(config, ["init"])
        signer = aptly_signer.make_server(config)
        url = f"http://127.0.0.1:{signer.server_port}"
        (work / "standin.json").write_text(json.dumps({"url": url, "timeout": 60, "store": str(work / "switch"),
                                                       "trace": str(work / "standin-trace.jsonl")}, indent=1))
        (work / "client.json").write_text(json.dumps({"url": url, "timeout": 60, "public_root": str(public),
                                                      "distribution": "resolute", "keyring": str(keyring),
                                                      "store": str(work / "switch"), "marker_dir": str(work / "markers"),
                                                      "log": str(work / "rehearsal-log.txt")}, indent=1))
        for s in (repo, signer):
            servers.append(s)
            threading.Thread(target=s.serve_forever, daemon=True).start()
        print(f"signer {url}  repo http://127.0.0.1:{repo.server_port}  key {fpr}", flush=True)
        signal.pause()
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()


if __name__ == "__main__":
    main()
