#!/usr/bin/env python3
"""The sbuild unshare chroot (UNITY-20260929-016).

A tarball is built by mmdebstrap from a pinned snapshot of the Ubuntu archive,
https://snapshot.ubuntu.com/ubuntu/<T>, with the target series' release,
-updates and -security pockets and the components main, universe and
restricted (May's decision, 2026-09-29). Its /etc/apt/sources.list keeps those
three lines, so sbuild's apt-get update/dist-upgrade in every build sees the
same archive state as the tarball: the same tarball gives the same build
dependencies, now and later.

  sbuild_chroot.py create [--snapshot <T>] [--series resolute] [--arch amd64]

writes ~/.cache/sbuild/chroots/<series>-<arch>-<T>.tar.zst and a sidecar
<series>-<arch>-<T>.json (sources, each pocket's InRelease Date and sha256,
mmdebstrap argv and version, package list, the tarball's sha256). It never
overwrites. build_sbuild.py checks a tarball with check_tarball() before a
build and the sbuild log with check_log() after it.
"""

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

SNAPSHOT = "https://snapshot.ubuntu.com/ubuntu"
COMPONENTS = ("main", "universe", "restricted")
CHROOT_DIR = Path.home() / ".cache" / "sbuild" / "chroots"
MAX_AGE = timedelta(days=7)
STAMP_RE = re.compile(r"\d{8}T\d{6}Z")
SUFFIX = ".tar.zst"
# sbuild's own lines when it builds a chroot instead of using the given one
ON_DEMAND = ("Creating chroot on-demand", "Creating new chroot tarball", "Unpacking tarball from STDIN")


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def pockets(series):
    return [series, f"{series}-updates", f"{series}-security"]


def sources_lines(series, stamp):
    return [f"deb {SNAPSHOT}/{stamp} {pocket} {' '.join(COMPONENTS)}" for pocket in pockets(series)]


def parse_stamp(stamp):
    if not isinstance(stamp, str) or not STAMP_RE.fullmatch(stamp):
        raise ValueError(f"snapshot timestamp {stamp!r} is not YYYYMMDDTHHMMSSZ")
    return datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)


def tarball_name(series, arch, stamp):
    return f"{series}-{arch}-{stamp}{SUFFIX}"


def sidecar_path(tarball):
    tarball = Path(tarball)
    return tarball.with_name(tarball.name[:-len(SUFFIX)] + ".json")


def tar_member(tarball, member):
    """The bytes of one member of a .tar.zst, or raise OSError."""
    result = subprocess.run(["tar", "--zstd", "-xOf", str(tarball), member], capture_output=True)
    if result.returncode:
        raise OSError(f"cannot read {member} from {tarball}: {result.stderr.decode(errors='replace').strip()}")
    return result.stdout


def source_lines_in(tarball):
    """The non-empty, non-comment lines of the tarball's sources.list
    (mmdebstrap separates its entries with blank lines)."""
    text = tar_member(tarball, "./etc/apt/sources.list").decode("utf-8", errors="replace")
    return [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]


def other_sources_in(tarball):
    """Files in the tarball's etc/apt/sources.list.d/ (there must be none)."""
    result = subprocess.run(["tar", "--zstd", "-tf", str(tarball)], capture_output=True, text=True)
    if result.returncode:
        raise OSError(f"cannot list {tarball}: {result.stderr.strip()}")
    return [name for name in result.stdout.splitlines()
            if name.lstrip("./").startswith("etc/apt/sources.list.d/") and not name.endswith("/")]


def current_tarball(series, arch, directory=None):
    """The newest <series>-<arch>-<T>.tar.zst in the chroot directory that has
    a sidecar, or None."""
    directory = Path(directory) if directory else CHROOT_DIR
    found = []
    for path in directory.glob(f"{series}-{arch}-*{SUFFIX}"):
        stamp = path.name[len(f"{series}-{arch}-"):-len(SUFFIX)]
        if STAMP_RE.fullmatch(stamp) and sidecar_path(path).is_file():
            found.append((stamp, path))
    return max(found)[1] if found else None


def check_tarball(tarball, series, arch, allow_old=False, now=None):
    """(info, error) for a build: the tarball is a real file (not a symlink)
    named <series>-<arch>-<T>.tar.zst, its sidecar matches its sha256, series
    and arch, the sources inside it are exactly the three snapshot pockets of
    <T>, and <T> is at most seven days old unless allow_old."""
    tarball = Path(tarball)
    if not tarball.is_absolute() or tarball.is_symlink() or not tarball.is_file():
        return None, f"chroot tarball {tarball} must be an absolute path to a regular file, not a symlink"
    prefix = f"{series}-{arch}-"
    stamp = tarball.name[len(prefix):-len(SUFFIX)] if tarball.name.startswith(prefix) and tarball.name.endswith(SUFFIX) else None
    try:
        taken = parse_stamp(stamp)
    except ValueError:
        return None, f"chroot tarball {tarball.name} is not named {prefix}<YYYYMMDDTHHMMSSZ>{SUFFIX}"
    sidecar = sidecar_path(tarball)
    try:
        record = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, f"chroot tarball {tarball.name} has no readable sidecar {sidecar.name}: {exc}"
    digest = sha256(tarball)
    expected = sources_lines(series, stamp)
    for key, value in (("schema", 1), ("series", series), ("arch", arch), ("snapshot", stamp),
                       ("tarball", tarball.name), ("sha256", digest), ("sources", expected)):
        if not isinstance(record, dict) or record.get(key) != value:
            return None, f"chroot sidecar {sidecar.name} does not match the tarball ({key})"
    try:
        inside, extra = source_lines_in(tarball), other_sources_in(tarball)
    except OSError as exc:
        return None, str(exc)
    if inside != expected or extra:
        return None, (f"chroot tarball {tarball.name} has other apt sources than the snapshot pockets: "
                      f"{inside!r} {extra!r}")
    now = now or datetime.now(timezone.utc)
    old = now - taken > MAX_AGE
    if old and not allow_old:
        return None, (f"chroot tarball {tarball.name} is from a snapshot more than {MAX_AGE.days} days old; "
                      "create a new one with scripts/sbuild_chroot.py create, or pass --allow-old-chroot")
    info = {"tarball": str(tarball), "sha256": digest, "size": tarball.stat().st_size,
            "sidecar": str(sidecar), "sidecar_sha256": sha256(sidecar), "snapshot": stamp,
            "sources": expected, "inrelease": record.get("inrelease"), "allow_old_chroot": bool(allow_old),
            "older_than_max_age": old}
    return info, None


def check_log(text, tarball, stamp):
    """(inrelease_lines, error) for an sbuild log: sbuild unpacked exactly this
    tarball, built no chroot of its own, and every http(s) fetch came from the
    snapshot <T>. Local file:/copy: fetches (sbuild's archive of the build
    dependencies) are allowed."""
    lines = text.splitlines()
    for marker in ON_DEMAND:
        if any(marker in line for line in lines):
            return None, f"sbuild built a chroot of its own, on-demand ({marker!r} in the log)"
    if not any(line.startswith(f"I: Unpacking {tarball} to ") for line in lines):
        return None, f"the sbuild log does not show the chroot tarball {tarball} being unpacked"
    base = f"{SNAPSHOT}/{stamp}"
    fetched = []
    for line in lines:
        match = re.match(r"^(?:Get|Hit|Ign|Err):\d+ (\S+)", line)
        if not match:
            continue
        uri = match.group(1)
        if uri.startswith(("file:", "copy:")):
            continue
        if uri != base and not uri.startswith(base + "/"):
            return None, f"the build fetched from outside the snapshot {base}: {line.strip()}"
        if line.rstrip().endswith("InRelease") or "InRelease [" in line:
            fetched.append(line.strip())
    return fetched, None


def fetch(url, attempts=5):
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                return response.read()
        except (urllib.error.URLError, OSError) as exc:
            if attempt == attempts - 1:
                raise OSError(f"cannot fetch {url}: {exc}")
            time.sleep(5 * (attempt + 1))


def packages(tarball):
    status = tar_member(tarball, "./var/lib/dpkg/status").decode("utf-8", errors="replace")
    result = []
    for block in status.split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line and not line[0].isspace())
        if fields.get("Status", "").endswith(" installed"):
            result.append(f"{fields.get('Package')}:{fields.get('Architecture')}={fields.get('Version')}")
    return sorted(result)


def create(args):
    stamp = args.snapshot or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    parse_stamp(stamp)
    directory = Path(args.directory).expanduser() if args.directory else CHROOT_DIR
    directory.mkdir(parents=True, exist_ok=True)
    tarball = directory / tarball_name(args.series, args.arch, stamp)
    if tarball.exists() or sidecar_path(tarball).exists():
        print(f"{tarball} or its sidecar already exists", file=sys.stderr)
        return 2
    inrelease = {}
    for pocket in pockets(args.series):
        data = fetch(f"{SNAPSHOT}/{stamp}/dists/{pocket}/InRelease")
        date = next((line.split(":", 1)[1].strip() for line in data.decode("utf-8", errors="replace").splitlines()
                     if line.startswith("Date:")), None)
        if not date:
            print(f"{pocket} InRelease of snapshot {stamp} has no Date", file=sys.stderr)
            return 2
        inrelease[pocket] = {"date": date, "sha256": hashlib.sha256(data).hexdigest()}
    partial = tarball.with_name(tarball.name + ".partial" + SUFFIX)
    lines = sources_lines(args.series, stamp)
    # The snapshot answers only over https, and the buildd variant has no CA
    # certificates: without them sbuild's apt-get update in the chroot fails.
    # The components are in the deb lines (--components only applies to bare
    # mirror arguments).
    argv = ["mmdebstrap", "--variant=buildd", f"--arch={args.arch}", "--skip=output/mknod",
            "--include=ca-certificates", '--aptopt=Acquire::Retries "5"',
            args.series, str(partial)] + lines
    print("$ " + " ".join(argv), flush=True)
    try:
        subprocess.run(argv, check=True)
        if source_lines_in(partial) != lines or other_sources_in(partial):
            print(f"mmdebstrap wrote other apt sources than {lines!r}; tarball not kept", file=sys.stderr)
            partial.unlink()
            return 2
        version = subprocess.run(["dpkg-query", "-W", "-f=${Version}", "mmdebstrap"], capture_output=True,
                                 text=True).stdout.strip()
        record = {"schema": 1, "series": args.series, "arch": args.arch, "snapshot": stamp,
                  "sources": lines, "components": list(COMPONENTS), "inrelease": inrelease,
                  "mmdebstrap": {"version": version, "argv": argv[:-len(lines) - 1] + ["<tarball>"] + lines},
                  "created_at": datetime.now(timezone.utc).isoformat(), "tarball": tarball.name,
                  "sha256": sha256(partial), "size": partial.stat().st_size, "packages": packages(partial)}
    except (OSError, subprocess.CalledProcessError) as exc:
        if partial.exists():
            partial.unlink()
        print(f"creating the chroot failed: {exc}", file=sys.stderr)
        return 2
    os.rename(partial, tarball)
    sidecar_path(tarball).write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    print(tarball)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    make = sub.add_parser("create", help="create a tarball from a snapshot of the archive")
    make.add_argument("--snapshot", help="snapshot timestamp YYYYMMDDTHHMMSSZ (default: now, UTC)")
    make.add_argument("--series", default="resolute")
    make.add_argument("--arch", default="amd64")
    make.add_argument("--directory", help=f"output directory (default {CHROOT_DIR})")
    args = parser.parse_args()
    return create(args)


if __name__ == "__main__":
    sys.exit(main())
