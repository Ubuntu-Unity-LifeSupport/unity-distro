#!/usr/bin/env python3
"""gpg stand-in for aptly (UNITY-20260929-021). aptly finds it as `gpg` on PATH
(set up at cut-over by May; this task installs nothing) and calls it as its
GnuPG signer does in aptly 1.6.2 (pgp/gnupg.go):

  gpg --version
  gpg -o <dest> --digest-algo SHA256 --armor --yes [options] --detach-sign <Release>
  gpg -o <dest> --digest-algo SHA256 --yes [options] --clearsign <Release>

It signs nothing itself. It sends aptly's Release and the index files the
Release lists (read from aptly's temporary directory, where they are named
with '/' replaced by '_') to the signer, and writes the signer's answer to
<dest>: Release.gpg (a detached signature over the signer's Release) or
InRelease (the signer's clearsigned Release, with Valid-Until). The trio is
also stored 0600 under the store directory, named by the sha256 of aptly's
Release, for the refresh right after the switch (card sections 8 and 10).

Unknown options, a positional count other than one, a symlink, a missing
listed file, a refusal or a timeout: exit non-zero, write nothing. aptly then
aborts before it renames anything into place. --passphrase is never sent or
logged.
"""

import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request

VERSION = "gpg (GnuPG) 2.4.8\nlibgcrypt 1.11.0\n"
WITH_VALUE = {"-o", "--output", "--digest-algo", "--keyring", "--secret-keyring", "-u", "--local-user",
              "--pinentry-mode", "--passphrase", "--passphrase-file", "--status-fd"}
FLAGS = {"--armor", "--yes", "--no-auto-check-trustdb", "--no-default-keyring", "--no-tty", "--batch"}
MODES = {"--detach-sign": "detached", "--clearsign": "clear"}
CONFIG = os.environ.get("APTLY_SIGNER_STANDIN_CONFIG",
                        str(Path.home() / ".config" / "aptly-signer" / "standin.json"))


def fail(message):
    print(f"gpg-standin: {message}", file=sys.stderr)
    return 2


def parse(argv):
    """(mode, dest, source) or raises ValueError."""
    mode = dest = None
    positional = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in WITH_VALUE:
            if i + 1 >= len(argv):
                raise ValueError(f"{arg} needs a value")
            if arg in ("-o", "--output"):
                dest = argv[i + 1]
            i += 2
            continue
        if arg in FLAGS:
            i += 1
            continue
        if arg in MODES:
            if mode:
                raise ValueError("more than one signing mode")
            mode = MODES[arg]
            i += 1
            continue
        if arg.startswith("-"):
            raise ValueError(f"unknown option {arg.split('=', 1)[0]}")
        positional.append(arg)
        i += 1
    if mode is None or dest is None or len(positional) != 1:
        raise ValueError("expected one signing mode, -o <dest> and exactly one file")
    return mode, dest, positional[0]


def regular(path):
    p = Path(path)
    if p.is_symlink() or not p.is_file():
        raise ValueError(f"{p.name} is not a regular file")
    return p.read_bytes()


def listed_files(release):
    """The paths the Release lists in its SHA256 section."""
    paths, inside = [], False
    for line in release.decode("utf-8").splitlines():
        if line and not line[0].isspace():
            inside = line.startswith("SHA256:")
        elif inside and line.strip():
            paths.append(line.split()[-1])
    return paths


def main(argv):
    if argv == ["--version"]:
        sys.stdout.write(VERSION)
        return 0
    try:
        mode, dest, source = parse(argv)
        release = regular(source)
        tempdir = Path(source).parent
        files = {}
        for path in listed_files(release):
            if "/" in path and (path.startswith("/") or ".." in path.split("/")):
                raise ValueError("a listed path is not relative")
            files[path] = base64.b64encode(regular(tempdir / path.replace("/", "_"))).decode()
        config = json.loads(Path(CONFIG).read_text(encoding="utf-8"))
    except (ValueError, OSError, UnicodeDecodeError) as exc:
        return fail(exc)
    body = json.dumps({"release": base64.b64encode(release).decode(), "files": files}).encode()
    request = urllib.request.Request(config["url"].rstrip("/") + "/sign", data=body,
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=config.get("timeout", 120)) as response:
            answer = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        try:
            reason = json.loads(exc.read()).get("error")
        except ValueError:
            reason = exc.reason
        finally:
            exc.close()
        return fail(f"the signer refused: {reason}")
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return fail(f"the signer is not reachable: {exc}")
    try:
        trio = {k: base64.b64decode(answer[k], validate=True) for k in ("release", "inrelease", "release_gpg")}
    except (KeyError, ValueError):
        return fail("the signer's answer is malformed")
    store = Path(os.path.expanduser(config.get("store", "~/.cache/aptly-signer/switch")))
    store.mkdir(parents=True, exist_ok=True, mode=0o700)
    key = hashlib.sha256(release).hexdigest()
    record = store / f"{key}.json"
    tmp = record.with_name(record.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump({k: base64.b64encode(v).decode() for k, v in trio.items()}, stream)
    os.replace(tmp, record)
    out = trio["release_gpg"] if mode == "detached" else trio["inrelease"]
    dest_tmp = Path(dest).with_name(Path(dest).name + ".standin-tmp")
    dest_tmp.write_bytes(out)
    os.replace(dest_tmp, dest)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
