#!/usr/bin/env python3
"""aptly-signer: the signing service on the signer VM (UNITY-20260929-021,
design UNITY-20260929-019 with the -021 amendment). Standard library only.

  aptly_signer.py --config FILE serve          HTTP API on the host-only address
  aptly_signer.py --config FILE console CMD    May's console, on the signer's TTY:
        init | template-hash | list | show ID | approve ID | reject ID | log
  aptly_signer.py --config FILE resign         scheduled re-sign of last-live

The logic is in signer_core.py. This file keeps the state (one JSON file,
flock across processes, atomic writes; missing or corrupt state refuses
everything), signs with gpg (a pinned key, every output checked with gpgv),
reads added .debs from the repository for the maintainer-script flag, and
serves the API with size limits and timeouts.
"""

import argparse
import base64
import contextlib
import fcntl
import hashlib
import http.server
import io
import json
import lzma
import os
from pathlib import Path
import posixpath
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zlib
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent))
import signer_core as core  # noqa: E402

try:
    from compression import zstd
except ImportError:  # pragma: no cover
    zstd = None

# max_body bounds a whole request; the .debs of a proposal travel base64 inside
# it, so together they may be at most about 3/4 of it (~72 MiB). Larger
# proposals are refused (fail closed).
DEFAULTS = {"port": 8580, "max_body": 96 * 1024 * 1024, "timeout": 30, "max_control": 16 * 1024 * 1024,
            "distribution": "resolute", "gpg": "/usr/bin/gpg", "gpgv": "/usr/bin/gpgv"}
SCRIPTS = ("preinst", "postinst", "prerm", "postrm", "config")


def load_config(path):
    config = dict(DEFAULTS)
    config.update(json.loads(Path(path).read_text(encoding="utf-8")))
    for key in ("bind", "state", "template", "gnupghome", "fingerprint", "keyring", "repo_base"):
        if not config.get(key):
            raise SystemExit(f"config: {key} is required")
    for key in ("gpg", "gpgv"):
        if not Path(config[key]).is_absolute():
            raise SystemExit(f"config: {key} must be an absolute path")
    return config


# ---- state -------------------------------------------------------------------

class Store:
    """The signer's state: one JSON file, flock on <file>.lock, atomic writes."""

    def __init__(self, path):
        self.path = Path(path)
        self.lockfile = self.path.with_name(self.path.name + ".lock")

    @contextlib.contextmanager
    def locked(self, create=False):
        with open(self.lockfile, "a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if create:
                if self.path.exists():
                    raise core.Refused("the state already exists; it is never reinitialised")
                state = core.new_state()
            else:
                try:
                    state = core.check_state(json.loads(self.path.read_text(encoding="utf-8")))
                except (OSError, ValueError):
                    raise core.Refused("the signer state is missing or corrupt; nothing is signed")
            yield state
            self.save(state)

    def save(self, state):
        tmp = self.path.with_name(self.path.name + ".tmp")
        with open(tmp, "w", encoding="utf-8") as stream:
            json.dump(state, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, self.path)
        fd = os.open(self.path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


# ---- signing -----------------------------------------------------------------

class GpgBackend:
    """gpg with the pinned key; gpgv against a keyring holding only that key.
    Both by absolute path, never looked up on PATH (the rehearsal put a gpg
    stand-in first on PATH; the signer must never call it)."""

    def __init__(self, homedir, fingerprint, keyring, gpg="/usr/bin/gpg", gpgv="/usr/bin/gpgv"):
        if not (Path(gpg).is_absolute() and Path(gpgv).is_absolute()):
            raise core.Refused("gpg and gpgv must be absolute paths")
        self.homedir, self.fpr, self.keyring = str(homedir), fingerprint, str(keyring)
        self.gpg, self.gpgv = str(gpg), str(gpgv)

    def _gpg(self, args, data):
        env = dict(os.environ, GNUPGHOME=self.homedir)
        run = subprocess.run([self.gpg, "--homedir", self.homedir, "--batch", "--no-tty", "--yes",
                              "--local-user", self.fpr + "!", "--digest-algo", "SHA256", *args, "--output", "-"],
                             input=data, capture_output=True, env=env, timeout=60)
        if run.returncode:
            raise core.Refused("gpg failed to sign")
        return run.stdout

    def sign_detached(self, data):
        return self._gpg(["--armor", "--detach-sign"], data)

    def sign_clear(self, data):
        return self._gpg(["--clearsign"], data)

    def _gpgv(self, args):
        return subprocess.run([self.gpgv, "--keyring", self.keyring, *args], capture_output=True, timeout=60)

    def verify_detached(self, signature, data):
        with tempfile.TemporaryDirectory() as tmp:
            sig, body = Path(tmp) / "Release.gpg", Path(tmp) / "Release"
            sig.write_bytes(signature)
            body.write_bytes(data)
            return self._gpgv([str(sig), str(body)]).returncode == 0

    def verify_clear(self, clear):
        with tempfile.TemporaryDirectory() as tmp:
            path, out = Path(tmp) / "InRelease", Path(tmp) / "out"
            path.write_bytes(clear)
            if self._gpgv(["--output", str(out), str(path)]).returncode:
                return None
            return out.read_bytes()


# ---- the maintainer-script flag, from the repository -------------------------

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def fetch(base, rel, limit, timeout):
    parts = rel.split("/")
    if rel.startswith("/") or "%" in rel or "\\" in rel or ".." in parts or posixpath.normpath(rel) != rel:
        raise core.Refused("a Filename is not a plain relative path")
    url = base.rstrip("/") + "/" + urllib.parse.quote(rel)
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(url, timeout=timeout) as response:
            data = response.read(limit + 1)
    except urllib.error.HTTPError as exc:
        exc.close()
        raise core.Refused(f"cannot fetch {core.printable(rel)} from the repository: HTTP {exc.code}")
    except (urllib.error.URLError, OSError) as exc:
        raise core.Refused(f"cannot fetch {core.printable(rel)} from the repository: {exc}")
    if len(data) > limit:
        raise core.Refused(f"{core.printable(rel)} is larger than its Packages Size")
    return data


def bounded_decompress(name, body, limit):
    """The control archive decompressed in memory, never beyond limit bytes,
    as exactly one complete stream with nothing after it. dpkg reads every
    gzip member, so a second member could carry a postinst that a
    one-member reader never sees (Verifier round 1): anything but one stream
    is refused."""
    try:
        if name == "control.tar":
            return body if len(body) <= limit else _too_big()
        if name == "control.tar.gz":
            d = zlib.decompressobj(16 + zlib.MAX_WBITS)
        elif name == "control.tar.xz":
            d = lzma.LZMADecompressor()
        elif name == "control.tar.zst":
            if zstd is None:
                raise core.Refused("no zstd support")
            d = zstd.ZstdDecompressor()
        else:
            raise core.Refused(f"unsupported control archive {core.printable(name)}")
        out = d.decompress(body, limit + 1)
        if len(out) > limit:
            _too_big()
        if not d.eof or d.unused_data or (hasattr(d, "unconsumed_tail") and d.unconsumed_tail):
            raise core.Refused(f"{core.printable(name)} is not exactly one complete compressed stream")
    except (zlib.error, lzma.LZMAError, ValueError, EOFError) as exc:
        raise core.Refused(f"malformed {core.printable(name)}: {exc}")
    except core.Refused:
        raise
    except Exception as exc:  # zstd raises its own error type
        raise core.Refused(f"malformed {core.printable(name)}: {exc}")
    return out


def _too_big():
    raise core.Refused("a control archive decompresses beyond the limit")


def control_members(deb, limit=16 * 1024 * 1024):
    """The member names of a .deb's control archive (ar, control.tar.{gz,xz,zst}),
    read in memory with a decompression cap; nothing is extracted."""
    if not deb.startswith(b"!<arch>\n"):
        raise core.Refused("not an ar archive")
    pos = 8
    while pos + 60 <= len(deb):
        header = deb[pos:pos + 60]
        name = header[:16].decode("ascii", "replace").strip().rstrip("/")
        try:
            size = int(header[48:58].decode("ascii").strip())
        except ValueError:
            raise core.Refused("malformed ar header")
        body = deb[pos + 60:pos + 60 + size]
        if len(body) != size:
            raise core.Refused("truncated ar member")
        if name.startswith("control.tar"):
            plain = bounded_decompress(name, body, limit)
            try:
                with tarfile.open(fileobj=io.BytesIO(plain), mode="r:") as tar:
                    names = [m.name.lstrip("./") for m in tar.getmembers()]
                    end = tar.offset
                # a complete tar ends with two zero blocks after its last member
                if plain[end:end + 1024] != b"\0" * 1024:
                    raise core.Refused("the control archive has no end-of-archive marker")
                return names
            except (tarfile.TarError, EOFError, OSError) as exc:
                raise core.Refused(f"malformed control archive: {exc}")
        pos += 60 + size + (size % 2)
    raise core.Refused("no control archive in the .deb")


def script_scanner(config):
    def scan(data):
        found = sorted(set(control_members(data, config.get("max_control", DEFAULTS["max_control"]))) & set(SCRIPTS))
        return "scripts: " + ",".join(found) if found else "no scripts"
    return scan


# ---- the API -----------------------------------------------------------------

def decode_files(obj):
    if not isinstance(obj, dict):
        raise core.Refused("files must be an object")
    return {str(k): base64.b64decode(v, validate=True) for k, v in obj.items()}


def make_handler(config, store, template, backend):
    class Handler(http.server.BaseHTTPRequestHandler):
        server_version = "aptly-signer"

        def log_message(self, fmt, *args):
            sys.stderr.write(core.printable(fmt % args) + "\n")

        def setup(self):
            super().setup()
            self.request.settimeout(config["timeout"])

        def reply(self, code, payload):
            body = json.dumps(payload).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def body(self):
            if self.headers.get("Transfer-Encoding"):
                raise core.Refused("chunked bodies are refused")
            try:
                length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                raise core.Refused("Content-Length is required")
            if length < 0 or length > config["max_body"]:
                raise core.Refused("the request is too large")
            try:
                request = json.loads(self.rfile.read(length))
            except ValueError:
                raise core.Refused("the request is not JSON")
            if not isinstance(request, dict):
                raise core.Refused("the request is not a JSON object")
            return request

        def do_POST(self):
            now = datetime.now(timezone.utc)
            try:
                request = self.body()
                if self.path == "/propose":
                    debs = core.DebSet(decode_files(request.get("debs", {})), script_scanner(config))
                    with store.locked() as state:
                        pid = core.propose(state, template, decode_files(request.get("files")),
                                           request.get("task_id"), debs, now)
                    return self.reply(200, {"ok": True, "proposal": pid})
                if self.path == "/sign":
                    release = base64.b64decode(request.get("release", ""), validate=True)
                    with store.locked() as state:
                        trio = core.sign(state, template, release, decode_files(request.get("files")), backend, now)
                    return self.reply(200, {"ok": True, **{k: base64.b64encode(v).decode() for k, v in trio.items()}})
                if self.path == "/live":
                    served = fetch(config["repo_base"], f"dists/{config['distribution']}/InRelease",
                                   1024 * 1024, config["timeout"])
                    with store.locked() as state:
                        sid = core.live(state, served)
                    return self.reply(200, {"ok": True, "last_live": sid})
                return self.reply(404, {"ok": False, "error": "unknown endpoint"})
            except core.Refused as exc:
                with contextlib.suppress(core.Refused, OSError):
                    with store.locked() as state:
                        core.log(state, f"refused {self.path}: {exc}")
                return self.reply(409, {"ok": False, "error": core.printable(exc)})
            except (ValueError, KeyError, TypeError) as exc:
                return self.reply(400, {"ok": False, "error": core.printable(f"bad request: {exc}")})

        def do_GET(self):
            if self.path != "/current":
                return self.reply(404, {"ok": False, "error": "unknown endpoint"})
            try:
                with store.locked() as state:
                    trio = core.current_trio(state)
            except core.Refused as exc:
                return self.reply(409, {"ok": False, "error": core.printable(exc)})
            return self.reply(200, {"ok": True, **{k: base64.b64encode(v).decode() for k, v in trio.items()}})

    return Handler


def make_server(config, backend=None):
    template = core.check_template(json.loads(Path(config["template"]).read_text(encoding="utf-8")))
    backend = backend or GpgBackend(config["gnupghome"], config["fingerprint"], config["keyring"],
                                    config.get("gpg", "/usr/bin/gpg"), config.get("gpgv", "/usr/bin/gpgv"))
    server = http.server.HTTPServer((config["bind"], int(config["port"])),
                                    make_handler(config, Store(config["state"]), template, backend))
    server.timeout = config["timeout"]
    return server


# ---- console and re-sign -------------------------------------------------------

def console(config, argv, out=sys.stdout, confirm=input):
    store = Store(config["state"])
    raw = Path(config["template"]).read_bytes()
    template = core.check_template(json.loads(raw))
    command = argv[0] if argv else "list"
    if command == "template-hash":
        print(f"release template sha256 {hashlib.sha256(raw).hexdigest()}", file=out)
        return 0
    if command == "init":
        with store.locked(create=True):
            pass
        print(f"state created; release template sha256 {hashlib.sha256(raw).hexdigest()}", file=out)
        return 0
    with store.locked() as state:
        if command == "list":
            for pid, p in sorted(state["proposals"].items()):
                print(core.printable(f"{pid}  {p['received']}  {len(p['diff'])} changes"), file=out)
            live = state.get("last_live") or {}
            print(core.printable(f"last-live: {live.get('set_id') or '(none)'}"), file=out)
        elif command == "show":
            for line in core.console_lines(state, argv[1]):
                print(line, file=out)
        elif command == "approve":
            for line in core.console_lines(state, argv[1]):
                print(line, file=out)
            if confirm("type 'approve' to approve exactly this content: ").strip() != "approve":
                print("not approved", file=out)
                return 1
            core.approve(state, argv[1])
            print("approved", file=out)
        elif command == "reject":
            core.reject(state, argv[1])
            print("rejected", file=out)
        elif command == "log":
            for line in state.get("log", [])[-50:]:
                print(line, file=out)
        else:
            print("unknown command", file=out)
            return 2
    return 0


def resign_command(config, backend=None, now=None):
    template = core.check_template(json.loads(Path(config["template"]).read_text(encoding="utf-8")))
    backend = backend or GpgBackend(config["gnupghome"], config["fingerprint"], config["keyring"],
                                    config.get("gpg", "/usr/bin/gpg"), config.get("gpgv", "/usr/bin/gpgv"))
    with Store(config["state"]).locked() as state:
        core.resign(state, template, backend, now or datetime.now(timezone.utc))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", required=True)
    parser.add_argument("command", choices=("serve", "console", "resign"))
    parser.add_argument("args", nargs="*")
    args = parser.parse_args()
    config = load_config(args.config)
    try:
        if args.command == "serve":
            make_server(config).serve_forever()
        elif args.command == "console":
            return console(config, args.args)
        else:
            return resign_command(config)
    except core.Refused as exc:
        print(f"refused: {core.printable(exc)}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
