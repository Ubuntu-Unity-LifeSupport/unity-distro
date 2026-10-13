"""Fixtures for UNITY-20260929-016: a small chroot tarball as sbuild_chroot.py
makes it (etc/apt/sources.list with mmdebstrap's blank-line-separated entries,
an empty sources.list.d/, a dpkg status), with its sidecar."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sbuild_chroot  # noqa: E402


def stamp_days_ago(days):
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y%m%dT%H%M%SZ")


def make_chroot(directory, series="resolute", arch="amd64", stamp=None, lines=None, extra_files=(),
                sidecar_changes=None, write_sidecar=True):
    """Build <directory>/<series>-<arch>-<stamp>.tar.zst and its sidecar.
    lines: the sources.list lines (default: the snapshot pockets);
    extra_files: paths (relative) to add, e.g. etc/apt/sources.list.d/x.list;
    sidecar_changes: keys to override in the sidecar."""
    directory = Path(directory)
    stamp = stamp or stamp_days_ago(1)
    lines = sbuild_chroot.sources_lines(series, stamp) if lines is None else lines
    root = directory / f".root-{stamp}-{len(list(directory.glob('.root-*'))) if directory.exists() else 0}"
    (root / "etc/apt/sources.list.d").mkdir(parents=True)
    (root / "etc/apt/sources.list").write_text("\n\n".join(lines) + "\n")
    (root / "var/lib/dpkg").mkdir(parents=True)
    (root / "var/lib/dpkg/status").write_text(
        "Package: base-files\nStatus: install ok installed\nArchitecture: amd64\nVersion: 14ubuntu1\n\n")
    for name in extra_files:
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text("deb http://example.invalid/ubuntu resolute main\n")
    tarball = directory / sbuild_chroot.tarball_name(series, arch, stamp)
    subprocess.run(["tar", "--zstd", "-cf", str(tarball), "-C", str(root), "."], check=True)
    if write_sidecar:
        record = {"schema": 1, "series": series, "arch": arch, "snapshot": stamp,
                  "sources": sbuild_chroot.sources_lines(series, stamp), "components": list(sbuild_chroot.COMPONENTS),
                  "inrelease": {p: {"date": "Mon, 28 Sep 2026 21:58:00 UTC", "sha256": "0" * 64}
                                for p in sbuild_chroot.pockets(series)},
                  "tarball": tarball.name, "sha256": hashlib.sha256(tarball.read_bytes()).hexdigest(),
                  "size": tarball.stat().st_size, "packages": ["base-files:amd64=14ubuntu1"]}
        record.update(sidecar_changes or {})
        sbuild_chroot.sidecar_path(tarball).write_text(json.dumps(record))
    return tarball
