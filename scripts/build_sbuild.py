#!/usr/bin/env python3
"""Build the checked-out source with sbuild and emit artifact-hash provenance."""

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tarfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_dependencies import POOL_ROOT, field_error, in_pool, installed_build_depends, source_name  # noqa: E402
import sbuild_chroot  # noqa: E402

# UNITY-20260929-016: read by sbuild after the user's own config.
SBUILD_CONFIG = Path(__file__).resolve().parents[1] / "build" / "sbuild-config.pl"


def run(args, cwd=None, check=True, capture=True):
    return subprocess.run(args, cwd=cwd, check=check, text=True,
                          stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.STDOUT if capture else None)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


# Version-control metadata that must never be in a source package we build.
VCS_NAMES = {".git", ".svn", ".hg", ".bzr", "CVS", "_darcs", "_MTN", "RCS"}


def source_paths(path):
    """Paths inside a source file produced by this build: the '+++' paths of
    a .diff.gz, the members of a tarball. Raises on anything unreadable."""
    if path.name.endswith(".diff.gz"):
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as stream:
            return [line[4:].split("\t", 1)[0].rstrip("\n") for line in stream if line.startswith("+++ ")]
    with tarfile.open(path) as archive:
        return archive.getnames()


def vcs_entries(dsc_dir, names):
    """UNITY-20260928-007: every VCS path in the source files this build made.
    Orig tarballs (and their signatures) are upstream's, pinned by the .dsc's
    sha256, and not produced from the checkout, so they are not inspected."""
    found = []
    for name in names:
        if ".orig." in name or ".orig-" in name or name.endswith(".asc"):
            continue
        for member in source_paths(dsc_dir / name):
            if VCS_NAMES & set(member.split("/")):
                found.append(f"{name}: {member}")
    return found


def extra_packages(paths, build_arch, depdir):
    """UNITY-20260929-013: check every --extra-package, copy it into depdir,
    and read its fields from the copy - the bytes sbuild gets and the manifest
    hashes. Returns (records, error); on error sbuild is not started. sbuild
    itself would skip a missing path or a second file of the same name, read
    every .deb of a directory, and only warn about a foreign architecture -
    all refused here. UNITY-20260929-014: the path checks run for every file
    before anything is copied; the copies go to a partial directory that
    becomes depdir only when every package passed, and is removed on a
    refusal."""
    resolved_paths, error = extra_package_paths(paths)
    if error:
        return None, error
    partial = depdir.with_name(depdir.name + ".partial")
    partial.mkdir()
    try:
        records, error = copy_and_check(resolved_paths, build_arch, partial)
    except BaseException:
        shutil.rmtree(partial, ignore_errors=True)
        raise
    if error:
        shutil.rmtree(partial, ignore_errors=True)
        return None, error
    partial.rename(depdir)
    for record in records:
        record["copy"] = depdir / record["copy"].name
    return records, None


def extra_package_paths(paths):
    """([(given, resolved)], error): the path checks of extra_packages()."""
    result, names, files = [], set(), set()
    for given in paths:
        candidate = Path(given).expanduser()
        if not candidate.is_absolute():
            candidate = Path.cwd() / candidate
        try:
            resolved = candidate.resolve(strict=True)
        except (OSError, RuntimeError):
            return None, f"--extra-package {given}: no such file"
        if not resolved.is_file():
            return None, f"--extra-package {given}: not a regular file"
        if resolved.suffix != ".deb":
            return None, f"--extra-package {given}: only .deb files are accepted"
        if not os.access(resolved, os.R_OK):
            return None, f"--extra-package {given}: not readable"
        if resolved.name in names:
            return None, f"--extra-package {given}: a file named {resolved.name} is already given (sbuild would drop one)"
        if resolved in files:
            return None, f"--extra-package {given}: the same file is given twice"
        names.add(resolved.name); files.add(resolved)
        result.append((given, resolved))
    return result, None


def copy_and_check(resolved_paths, build_arch, depdir):
    """(records, error): copy each file into depdir and check the Debian
    fields read from the copy."""
    records, packages = [], set()
    for given, resolved in resolved_paths:
        copy = depdir / resolved.name
        shutil.copyfile(resolved, copy)
        info = run(["dpkg-deb", "-f", str(copy), "Package", "Version", "Architecture", "Source", "Package-Type"],
                   check=False)
        fields = dict(line.split(": ", 1) for line in info.stdout.splitlines() if ": " in line) if not info.returncode else {}
        package, version, arch = fields.get("Package"), fields.get("Version"), fields.get("Architecture")
        if info.returncode or not (package and version and arch):
            return None, f"--extra-package {given}: dpkg-deb cannot read Package, Version and Architecture"
        source = source_name(fields.get("Source"), package)
        error = field_error(package, version, arch, source)
        if error:
            return None, f"--extra-package {given}: {error}"
        if fields.get("Package-Type") == "udeb":
            return None, f"--extra-package {given}: udeb packages are not accepted"
        if arch not in ("all", build_arch):
            return None, f"--extra-package {given}: architecture {arch} is neither all nor {build_arch}"
        # apt installs one version of a package: two files of it (e.g. all and
        # amd64) would both read as used from one Installed-Build-Depends line
        if package in packages:
            return None, f"--extra-package {given}: package {package} is already given"
        packages.add(package)
        records.append({"given": given, "resolved": resolved, "copy": copy, "package": package,
                        "version": version, "architecture": arch, "source": source})
    return records, None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--target-series", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    # UNITY-20260929-013: a build dependency from outside the target series'
    # archive (our repository's nux for unity); copied into the output,
    # given to sbuild, and recorded in the manifest's build_dependencies.
    parser.add_argument("--extra-package", action="append", default=[], metavar="DEB",
                        help="a .deb for sbuild --extra-package, recorded in the manifest (repeatable)")
    # UNITY-20260929-016: the chroot is a tarball made by sbuild_chroot.py from
    # a pinned archive snapshot, passed to sbuild explicitly and recorded.
    parser.add_argument("--chroot-tarball", type=Path,
                        help="chroot tarball (default: the newest in ~/.cache/sbuild/chroots with a sidecar)")
    parser.add_argument("--allow-old-chroot", action="store_true",
                        help="accept a tarball whose snapshot is more than 7 days old (recorded)")
    parser.add_argument("--tested-with", type=Path, metavar="MANIFEST",
                        help="the manifest of the build tested on target; its chroot must be this build's")
    args = parser.parse_args()
    repo = args.source_repo.resolve()
    output = args.output_dir.resolve()
    if not repo.is_dir():
        parser.error("source repository must exist")
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        parser.error("use a fresh empty output directory for each build")
    if not args.task_id.startswith("UNITY-"):
        parser.error("task ID must use the UNITY-YYYYMMDD-NNN format")
    status = run(["git", "-C", str(repo), "status", "--porcelain"]).stdout
    if status.strip():
        parser.error("source repository must be clean before building")
    commit = run(["git", "-C", str(repo), "rev-parse", "HEAD"]).stdout.strip()
    tree = run(["git", "-C", str(repo), "rev-parse", "HEAD^{tree}"]).stdout.strip()
    version = run(["dpkg-parsechangelog", "-S", "Version"], cwd=repo).stdout.strip()
    package = run(["dpkg-parsechangelog", "-S", "Source"], cwd=repo).stdout.strip()
    build_arch = run(["dpkg", "--print-architecture"]).stdout.strip()
    # UNITY-20260929-016: which chroot, checked before anything is written.
    given = args.chroot_tarball or sbuild_chroot.current_tarball(args.target_series, build_arch)
    if given is None:
        print(f"no chroot tarball for {args.target_series}-{build_arch} in {sbuild_chroot.CHROOT_DIR}; "
              "create one with scripts/sbuild_chroot.py create", file=sys.stderr)
        return 2
    given = Path(given).expanduser()
    if not given.is_absolute():
        given = Path.cwd() / given
    if given.is_symlink():
        print(f"chroot tarball {given} is a symlink; give the file itself", file=sys.stderr)
        return 2
    tarball = given.resolve()  # sbuild logs the resolved path
    chroot, error = sbuild_chroot.check_tarball(tarball, args.target_series, build_arch, args.allow_old_chroot)
    if error:
        print(error, file=sys.stderr)
        return 2
    if args.tested_with:
        try:
            tested = json.loads(args.tested_with.read_text(encoding="utf-8"))
            tested_sha = tested["chroot"]["sha256"]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print(f"cannot read the chroot of the tested build from {args.tested_with}: {exc}", file=sys.stderr)
            return 2
        if tested_sha != chroot["sha256"]:
            print(f"the tested build used another chroot ({tested_sha}); build on the same tarball, "
                  "or compare the .buildinfo Installed-Build-Depends and repeat the target test", file=sys.stderr)
            return 2
        chroot["tested_with"] = {"manifest": str(args.tested_with.resolve()),
                                 "manifest_sha256": sha256(args.tested_with), "chroot_sha256": tested_sha}
    dependencies = []
    if args.extra_package:
        records, error = extra_packages(args.extra_package, build_arch, output / "build-dependencies")
        if error:
            print(error, file=sys.stderr)
            return 2
        # The copy is what sbuild gets and what the manifest hashes. The pool
        # root can be redirected for the tests only; the gate and the
        # publisher check against POOL_ROOT themselves.
        pool_root = Path(os.environ.get("BUILD_SBUILD_POOL_ROOT", POOL_ROOT))
        for record in records:
            copy = record["copy"]
            digest = sha256(copy)
            found, where = in_pool(pool_root, record["package"], record["version"], record["architecture"],
                                   record["source"], digest)
            entry = {"file": f"build-dependencies/{copy.name}", "sha256": digest, "size": copy.stat().st_size,
                     "package": record["package"], "version": record["version"],
                     "architecture": record["architecture"], "source": record["source"],
                     "given_path": record["given"], "resolved_path": str(record["resolved"]),
                     "in_our_repository_pool": found}
            if found:
                entry["pool_path"] = str(where)
            dependencies.append((copy, entry))
    started = datetime.now(timezone.utc)
    # sbuild prints its build log to stdout only when stdout is a terminal or
    # --verbose is given; otherwise the log goes to its own .build file only.
    # UNITY-20260928-007: sbuild builds the source package from this checkout
    # with dpkg-source. Format 3.0 ignores VCS metadata by default, format 1.0
    # does not (.git is diffed, or tarred for full tarballs): -i and -I apply
    # dpkg-source's default ignore lists to every format.
    command = ["sbuild", "-d", args.target_series, "--no-clean-source", "--verbose",
               "--dpkg-source-opt=-i", "--dpkg-source-opt=-I",
               "--chroot-mode=unshare", f"--chroot={tarball}"]
    command += [f"--extra-package={copy}" for copy, _entry in dependencies]
    logfile = output / f"{args.task_id}-{package}-{version}-sbuild.log"
    env = dict(os.environ, SBUILD_CONFIG=str(SBUILD_CONFIG))
    with logfile.open("w", encoding="utf-8") as log:
        log.write(f"$ SBUILD_CONFIG={shlex.quote(str(SBUILD_CONFIG))} " + shlex.join(command) + "\n")
        log.flush()
        result = subprocess.run(command, cwd=repo, text=True, stdout=log, stderr=subprocess.STDOUT, check=False,
                                env=env)
    finished = datetime.now(timezone.utc)
    if result.returncode:
        print(f"sbuild failed ({result.returncode}); see {logfile}", file=sys.stderr)
        return result.returncode
    # UNITY-20260929-016: sbuild used this tarball, unchanged, built no chroot
    # of its own, and fetched only from the snapshot.
    if sbuild_chroot.sha256(tarball) != chroot["sha256"]:
        print(f"chroot tarball {tarball} changed during the build; no manifest written", file=sys.stderr)
        return 2
    fetched, error = sbuild_chroot.check_log(logfile.read_text(encoding="utf-8", errors="replace"),
                                             tarball, chroot["snapshot"])
    if error:
        print(f"{error}; no manifest written", file=sys.stderr)
        return 2
    chroot["log_inrelease"] = fetched
    # sbuild puts result files next to the source tree by default. The .changes
    # of this run lists every binary it produced; the source package is the
    # .dsc. Debian file names carry the version without its epoch.
    file_version = version.split(":", 1)[-1]
    search_roots = [repo.parent, output]
    def fresh(pattern):
        found = {p.resolve() for root in search_roots for p in root.glob(pattern)
                 if p.is_file() and p.stat().st_mtime >= started.timestamp() - 2}
        return sorted(found)
    changes = fresh(f"{package}_{file_version}_*.changes")
    dscs = fresh(f"{package}_{file_version}.dsc")
    if len(changes) != 1 or len(dscs) != 1:
        print(f"expected one .changes and one .dsc from this run, found {len(changes)} and {len(dscs)}", file=sys.stderr)
        return 2
    def checksums(path):
        """(name, sha256) pairs of a .changes or .dsc Checksums-Sha256 field."""
        pairs, section = [], None
        for line in path.read_text(encoding="utf-8").splitlines():
            if line and not line[0].isspace():
                section = line.split(":", 1)[0]
            elif section == "Checksums-Sha256" and line.strip():
                digest, _size, name = line.split()
                pairs.append((name, digest))
        return pairs
    listed = checksums(changes[0])
    if not listed:
        print(f"{changes[0].name} lists no files", file=sys.stderr)
        return 2
    # The source package: the .dsc and every file it names (orig/debian tarballs,
    # native tarball, diff.gz), taken with the hashes the .dsc records.
    source_files = checksums(dscs[0])
    source_names = {dscs[0].name} | {name for name, _ in source_files}
    selected = [(dscs[0], None, "source"), (changes[0], None, None)]
    for name, digest in source_files:
        path = dscs[0].parent / name
        if not path.is_file() or sha256(path) != digest:
            print(f"{name} listed in {dscs[0].name} is missing or does not match its sha256", file=sys.stderr)
            return 2
        selected.append((path, digest, "source_file"))
    try:
        leaked = vcs_entries(dscs[0].parent, [name for name, _ in source_files])
    except (OSError, EOFError, tarfile.TarError) as exc:
        print(f"cannot inspect the source files of {dscs[0].name} for VCS metadata: {exc}", file=sys.stderr)
        return 2
    if leaked:
        print("the source package contains version-control metadata; no manifest written:", file=sys.stderr)
        for entry in leaked:
            print(f"  {entry}", file=sys.stderr)
        return 2
    for name, digest in listed:
        path = changes[0].parent / name
        if not path.is_file() or sha256(path) != digest:
            print(f"{name} listed in {changes[0].name} is missing or does not match its sha256", file=sys.stderr)
            return 2
        if name in source_names:
            continue  # a source-full .changes: already recorded from the .dsc
        selected.append((path, digest, None))
    if dependencies:
        # UNITY-20260929-013: the copies are the bytes recorded, and each must
        # have been installed for the build - sbuild adds them to apt without
        # a pin, so one not newer than the archive's version is silently not
        # used; the .buildinfo's Installed-Build-Depends says what was.
        for copy, entry in dependencies:
            if sha256(copy) != entry["sha256"]:
                print(f"{entry['file']} changed during the build; no manifest written", file=sys.stderr)
                return 2
        buildinfos = [changes[0].parent / name for name, _ in listed if name.endswith(".buildinfo")]
        if len(buildinfos) != 1:
            print(f"--extra-package needs the build's .buildinfo to prove use; {changes[0].name} lists {len(buildinfos)}",
                  file=sys.stderr)
            return 2
        try:
            installed = installed_build_depends(buildinfos[0].read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"cannot read {buildinfos[0].name}: {exc}", file=sys.stderr)
            return 2
        for _copy, entry in dependencies:
            used = [installed.get((entry["package"], qualifier))
                    for qualifier in (None, entry["architecture"], build_arch)]
            if entry["version"] not in used:
                seen = sorted({v for (name, _q), v in installed.items() if name == entry["package"]})
                print(f"extra package {entry['package']} {entry['version']} was not used by the build "
                      f"(Installed-Build-Depends: {', '.join(seen) or 'absent'}); no manifest written", file=sys.stderr)
                return 2
    artifacts = []
    for path, _digest, role in selected:
        copied = output / path.name
        if path.resolve() != copied.resolve():
            copied.write_bytes(path.read_bytes())
            path = copied
        item = {"file": path.name, "sha256": sha256(path), "size": path.stat().st_size}
        if path.suffix in {".deb", ".ddeb", ".udeb"}:
            item.update({"kind": "binary", "package": run(["dpkg-deb", "-f", str(path), "Package"]).stdout.strip(),
                         "version": run(["dpkg-deb", "-f", str(path), "Version"]).stdout.strip(),
                         "architecture": run(["dpkg-deb", "-f", str(path), "Architecture"]).stdout.strip()})
        elif role == "source":
            item.update({"kind": "source", "package": package, "version": version})
        elif role == "source_file":
            item.update({"kind": "source_file", "package": package, "version": version})
        else:
            item["kind"] = path.suffix.lstrip(".")
        artifacts.append(item)
    if not any(item["kind"] == "source" for item in artifacts) or not any(item["kind"] == "binary" for item in artifacts):
        print("sbuild succeeded but matching source and binary artifacts were not both found", file=sys.stderr)
        return 2
    manifest = {
        "schema": 1, "task_id": args.task_id, "package": package,
        "candidate_version": version, "target_series": args.target_series,
        "source_repo": str(repo), "source_commit": commit,
        "source_tree_hash": tree, "build_command": command,
        "build_started": started.isoformat(), "build_finished": finished.isoformat(),
        "result": "PASS", "log": {"file": logfile.name, "sha256": sha256(logfile)},
        "artifacts": artifacts,
    }
    if dependencies:
        manifest["build_dependencies"] = [entry for _copy, entry in dependencies]
    manifest["chroot"] = chroot
    manifest_path = output / f"{args.task_id}-{package}-build-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
