"""Fixtures for UNITY-20260927-050: one manifest per contract case, with real
.deb/.ddeb/.udeb files built by dpkg-deb, each case in its own directory.
cases(dir) returns (name, case_dir, artifacts, expect); expect is the list of
snapshot entries the contract requires, or "ERROR: <text>" it must report."""
import hashlib
import subprocess
from pathlib import Path

SRC, VER = "demo", "1:1.0"


def deb(dirpath, package, version, arch="amd64", ext="deb", source=None, ptype=None):
    root = dirpath / f".b-{package}-{version}-{ext}"
    (root / "DEBIAN").mkdir(parents=True, exist_ok=True)
    lines = [f"Package: {package}", f"Version: {version}", f"Architecture: {arch}"]
    if source:
        lines.append(f"Source: {source}")
    if ptype:
        lines.append(f"Package-Type: {ptype}")
    lines += ["Maintainer: t <t@example.com>", "Description: t"]
    (root / "DEBIAN" / "control").write_text("\n".join(lines) + "\n")
    name = f"{package}_{version.split(':', 1)[-1]}_{arch}.{ext}"
    subprocess.run(["dpkg-deb", "--root-owner-group", "-Zxz", "--build", str(root), str(dirpath / name)],
                   check=True, capture_output=True)
    return {"file": name, "kind": "binary", "package": package, "version": version, "architecture": arch}


def plain(dirpath, name, kind):
    (dirpath / name).write_text(kind + "\n")
    return {"file": name, "kind": kind}


def cases(dirpath):
    base = Path(dirpath)
    out = []

    def case(name, build, expect):
        d = base / f"case{len(out) + 1}"
        d.mkdir()
        (d / "demo_1.0.dsc").write_text("Source: demo\n")
        artifacts = [{"file": "demo_1.0.dsc", "kind": "source", "package": SRC, "version": VER}]
        artifacts += build(d)
        artifacts += [plain(d, "demo_1.0_amd64.changes", "changes"), plain(d, "demo_1.0_amd64.buildinfo", "buildinfo")]
        for a in artifacts:
            a["sha256"] = hashlib.sha256((d / a["file"]).read_bytes()).hexdigest()
        out.append((name, d, artifacts, expect))

    case("deb and ddeb, source version",
         lambda d: [deb(d, "demo-bin", VER, source=SRC), deb(d, "demo-bin-dbgsym", VER, ext="ddeb", source=SRC)],
         ["demo_1:1.0_source", "demo-bin_1:1.0_amd64", "demo-bin-dbgsym_1:1.0_amd64"])
    case("binary named after the source, no Source field",
         lambda d: [deb(d, "demo", VER)],
         ["demo_1:1.0_source", "demo_1:1.0_amd64"])
    case("binNMU binary and dbgsym with their own version",
         lambda d: [deb(d, "demo-bin", "1:1.0+b1", source="demo (1:1.0)"),
                    deb(d, "demo-bin-dbgsym", "1:1.0+b1", ext="ddeb", source="demo (1:1.0)")],
         ["demo_1:1.0_source", "demo-bin_1:1.0+b1_amd64", "demo-bin-dbgsym_1:1.0+b1_amd64"])
    case("udeb",
         lambda d: [deb(d, "demo-bin", VER, source=SRC), deb(d, "demo-udeb", VER, ext="udeb", source=SRC)],
         "ERROR: udeb")
    case("binary from another source",
         lambda d: [deb(d, "demo-bin", VER, source=SRC), deb(d, "other-bin", VER, source="other")],
         "ERROR: built from")
    case("binary version differs, no Source version",
         lambda d: [deb(d, "demo-bin", VER, source=SRC), deb(d, "demo-x", "1:1.1", source=SRC)],
         "ERROR: built from")
    case("manifest record differs from the file",
         lambda d: [dict(deb(d, "demo-bin", VER, source=SRC), version="1:9.9")],
         "ERROR: does not match")
    case("unknown artifact kind",
         lambda d: [deb(d, "demo-bin", VER, source=SRC), plain(d, "demo_1.0.tar.xz", "xz")],
         "ERROR: no publication rule")
    return out
