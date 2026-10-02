#!/usr/bin/env python3
"""builder's side of the aptly-signer (UNITY-20260929-021).

  signer_client.py propose <rehearsal public dir> [--task UNITY-...]
  signer_client.py refresh --task UNITY-... (--switch | --current)
  signer_client.py live

propose: sends the rehearsal publication's index set (dists/<dist>/<component>
files the signer signs) for May's approval, with every .deb whose SHA256 is not
in the live Packages under public_root, read from the rehearsal publication's
pool (design amendment (b): a new .deb is not on :8080 before the switch). The
signer checks each against the Packages it validated itself.

refresh --switch: right after the switch, installs the trio the gpg stand-in
received at the switch (stored under its sha256 of aptly's Release, which is
now the served Release). --current: the signer's latest re-signed trio.
Before writing anything, every refresh checks that the trio's Release lists
exactly the index files served under dists/<dist>/ with their sizes and
checksums, that InRelease and Release.gpg verify with the signer's pinned
public key over that Release, and (--switch) that it equals aptly's Release
apart from Date and Valid-Until. Then it writes Release and Release.gpg, each
through a temporary file and a rename, then InRelease, and deletes the stored
trio. On any failure it writes nothing, leaves the marker
<marker_dir>/<task>.refresh-failed and a REFRESH-FAILED line in the log, and
exits non-zero (card sections 8 and 10).

live: reports the switch; the signer fetches InRelease itself.
"""

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "signer"))
import signer_core as core  # noqa: E402

CONFIG = os.environ.get("APTLY_SIGNER_CLIENT_CONFIG",
                        str(Path.home() / ".config" / "aptly-signer" / "client.json"))
TASK_RE = re.compile(r"UNITY-[0-9]{8}-[0-9]{3}")
SIGNED_FILES = re.compile(r"[a-z0-9-]+/(binary-[a-z0-9-]+/(Packages(\.gz|\.bz2|\.xz)?|Release)"
                          r"|source/(Sources(\.gz|\.bz2|\.xz)?|Release))")


def load_config():
    config = json.loads(Path(CONFIG).read_text(encoding="utf-8"))
    config.setdefault("distribution", "resolute")
    config.setdefault("timeout", 120)
    for key in ("store", "marker_dir", "log"):
        if key in config:
            config[key] = os.path.expanduser(config[key])
    return config


def call(config, method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(config["url"].rstrip("/") + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=config["timeout"]) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        try:
            reason = json.loads(exc.read()).get("error")
        except ValueError:
            reason = exc.reason
        finally:
            exc.close()
        raise core.Refused(f"the signer refused: {reason}")
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise core.Refused(f"the signer is not reachable: {exc}")


def packages_entries(dist_dir):
    """Every Packages entry under dists/<dist>/<component>/binary-*/Packages."""
    found = []
    for path in sorted(Path(dist_dir).glob("*/binary-*/Packages")):
        if path.is_symlink() or not path.is_file():
            raise core.Refused(f"{path.name} is not a regular file")
        found += core.parse_stanzas(path.read_text(encoding="utf-8"), str(path))
    return found


def propose(config, public_dir, task):
    dist = Path(public_dir) / "dists" / config["distribution"]
    files = {}
    for path in sorted(dist.rglob("*")):
        rel = path.relative_to(dist).as_posix()
        if path.is_symlink():
            raise core.Refused(f"{rel} is a symlink")
        if path.is_file() and SIGNED_FILES.fullmatch(rel):
            files[rel] = base64.b64encode(path.read_bytes()).decode()
    if not files:
        raise core.Refused("no index files found")
    live_dist = Path(config["public_root"]) / "dists" / config["distribution"]
    live = {e.get("SHA256") for e in packages_entries(live_dist)} if live_dist.exists() else set()
    debs = {}
    for entry in packages_entries(dist):
        name = entry.get("Filename", "")
        if entry.get("SHA256") in live or name in debs:
            continue
        deb = Path(public_dir) / name
        if ".." in name.split("/") or name.startswith("/") or deb.is_symlink() or not deb.is_file():
            raise core.Refused(f"the proposal's pool lacks {core.printable(name)}")
        debs[name] = base64.b64encode(deb.read_bytes()).decode()
    answer = call(config, "POST", "/propose", {"task_id": task, "files": files, "debs": debs})
    return answer["proposal"]


def gpgv(keyring, args):
    # by absolute path: a gpg stand-in may be first on PATH on builder
    return subprocess.run(["/usr/bin/gpgv", "--keyring", keyring, *args], capture_output=True,
                          timeout=60).returncode == 0


def check_trio(config, trio, dist_dir, aptly_release=None):
    """Nothing is written unless this passes (R2)."""
    release = trio["release"]
    try:
        text = release.decode("utf-8")
    except UnicodeDecodeError:
        raise core.Refused("the trio's Release is not UTF-8")
    listed, inside = {}, False
    for line in text.splitlines():
        if line and not line[0].isspace():
            inside = line.startswith("SHA256:")
        elif inside and line.strip():
            digest, size, path = line.split()
            listed[path] = (digest, int(size))
    if not listed:
        raise core.Refused("the trio's Release lists no files")
    for path in sorted(dist_dir.rglob("*")):
        rel = path.relative_to(dist_dir).as_posix()
        if path.is_file() and SIGNED_FILES.fullmatch(rel) and rel not in listed:
            raise core.Refused(f"{core.printable(rel)} is served but not listed by the trio's Release")
    for path, (digest, size) in listed.items():
        served = dist_dir / path
        if served.is_symlink() or not served.is_file():
            raise core.Refused(f"{core.printable(path)} listed by the trio is not served")
        data = served.read_bytes()
        if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
            raise core.Refused(f"{core.printable(path)} served does not match the trio's Release")
    with tempfile.TemporaryDirectory() as tmp:
        body, sig, clear, out = (Path(tmp) / n for n in ("Release", "Release.gpg", "InRelease", "out"))
        body.write_bytes(release)
        sig.write_bytes(trio["release_gpg"])
        clear.write_bytes(trio["inrelease"])
        if not gpgv(config["keyring"], [str(sig), str(body)]):
            raise core.Refused("Release.gpg does not verify with the signer's key")
        if not gpgv(config["keyring"], ["--output", str(out), str(clear)]) or out.read_bytes() != release:
            raise core.Refused("InRelease does not verify with the signer's key over the same Release")
    if aptly_release is not None:
        difference = core.compare_release(aptly_release, release)
        if difference:
            raise core.Refused(f"the stored trio does not belong to the served Release: {difference}")


def install(dist_dir, trio):
    for name, key in (("Release", "release"), ("Release.gpg", "release_gpg"), ("InRelease", "inrelease")):
        tmp = dist_dir / f".{name}.refresh-tmp"
        tmp.write_bytes(trio[key])
        os.replace(tmp, dist_dir / name)


def mark_failed(config, task, reason):
    marker_dir = Path(config["marker_dir"])
    marker_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")
    (marker_dir / f"{task}.refresh-failed").write_text(f"{stamp} {core.printable(reason)}\n", encoding="utf-8")
    with open(config["log"], "a", encoding="utf-8") as log:
        log.write(f"{stamp} REFRESH-FAILED {task}: {core.printable(reason)}\n")


def refresh(config, task, switch):
    dist_dir = Path(config["public_root"]) / "dists" / config["distribution"]
    stored = None
    try:
        if switch:
            served_release = (dist_dir / "Release").read_bytes()
            stored = Path(config["store"]) / f"{hashlib.sha256(served_release).hexdigest()}.json"
            if stored.is_symlink() or not stored.is_file():
                raise core.Refused("no stored switch-time trio for the served Release")
            raw = json.loads(stored.read_text(encoding="utf-8"))
            trio = {k: base64.b64decode(raw[k], validate=True) for k in ("release", "inrelease", "release_gpg")}
            check_trio(config, trio, dist_dir, aptly_release=served_release)
        else:
            answer = call(config, "GET", "/current")
            trio = {k: base64.b64decode(answer[k], validate=True) for k in ("release", "inrelease", "release_gpg")}
            check_trio(config, trio, dist_dir)
        install(dist_dir, trio)
    except (core.Refused, OSError, ValueError, KeyError) as exc:
        mark_failed(config, task, exc)
        raise core.Refused(f"refresh failed: {exc}")
    if stored is not None:
        stored.unlink()
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("propose")
    p.add_argument("public_dir")
    p.add_argument("--task")
    r = sub.add_parser("refresh")
    r.add_argument("--task", required=True)
    group = r.add_mutually_exclusive_group(required=True)
    group.add_argument("--switch", action="store_true")
    group.add_argument("--current", action="store_true")
    sub.add_parser("live")
    args = parser.parse_args()
    if getattr(args, "task", None) and not TASK_RE.fullmatch(args.task):
        parser.error("task must be UNITY-YYYYMMDD-NNN")
    config = load_config()
    try:
        if args.command == "propose":
            print(propose(config, args.public_dir, args.task))
        elif args.command == "refresh":
            refresh(config, args.task, args.switch)
        else:
            print(call(config, "POST", "/live", {})["last_live"])
    except core.Refused as exc:
        print(f"signer-client: {core.printable(exc)}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
