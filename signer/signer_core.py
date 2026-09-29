#!/usr/bin/env python3
"""The aptly-signer's logic (UNITY-20260929-021, design UNITY-20260929-019 with
the amendment in the -021 card, section 8). Pure: no network, no gpg, no
files. The service (aptly_signer.py) feeds it requests and a signing backend,
and keeps its state.

May's invariant: the signer signs a Release only if it is identical to the one
it builds itself - from its template, over index files it checked against the
content May approved on its console - except for Date and Valid-Until.
Scheduled re-signing covers only the approved, last-live content.
"""

import bz2
from datetime import datetime, timedelta, timezone
import gzip
import hashlib
import json
import lzma
import re

try:
    from compression import zstd
except ImportError:  # pragma: no cover - Python < 3.14
    zstd = None

MAX_INDEX = 64 * 1024 * 1024          # decompressed size of one index file
MAX_FILES = 64                        # files in one index set
DATE_FMT = "%a, %d %b %Y %H:%M:%S UTC"
SECTIONS = (("MD5Sum", "md5"), ("SHA1", "sha1"), ("SHA256", "sha256"), ("SHA512", "sha512"))
COMPRESSIONS = {"": None, ".gz": "gz", ".bz2": "bz2", ".xz": "xz"}
NAME_RE = re.compile(r"[a-z0-9][a-z0-9+.-]+")
VERSION_RE = re.compile(r"(?:[0-9]+:)?[0-9][A-Za-z0-9.+~-]*")
ARCH_RE = re.compile(r"[a-z0-9][a-z0-9-]*")
SHA256_RE = re.compile(r"[0-9a-f]{64}")
FILENAME_RE = re.compile(r"pool/[A-Za-z0-9][A-Za-z0-9+._~/-]*\.deb")
TASK_RE = re.compile(r"UNITY-\d{8}-\d{3}")
FIELD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*")


class Refused(Exception):
    """A request the signer refuses; the message names what differs."""


def sha(data, algo="sha256"):
    return hashlib.new(algo, data).hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def printable(text):
    """What may reach the console or a log: printable ASCII only."""
    return "".join(c if 32 <= ord(c) < 127 else "?" for c in str(text))


# ---- the template and the files it allows ------------------------------------

def check_template(template):
    if not isinstance(template, dict) or template.get("schema") != 1:
        raise Refused("release template: unsupported schema")
    for key in ("distribution", "prefix", "components", "architectures", "valid_days", "release", "component_release"):
        if key not in template:
            raise Refused(f"release template: {key} missing")
    keys = [k for k, _ in template["release"]]
    if "Date" not in keys or "Valid-Until" not in keys or len(keys) != len(set(keys)):
        raise Refused("release template: Date and Valid-Until must appear once")
    return template


def allowed_paths(template):
    """{relative path: (kind, component, arch, compression)} the Release may list."""
    paths = {}
    for component in template["components"]:
        for arch in template["architectures"]:
            base = f"{component}/binary-{arch}"
            for ext in COMPRESSIONS:
                paths[f"{base}/Packages{ext}"] = ("index", f"{base}/Packages", ext)
            paths[f"{base}/Release"] = ("component_release", (component, arch), "")
        base = f"{component}/source"
        for ext in COMPRESSIONS:
            paths[f"{base}/Sources{ext}"] = ("index", f"{base}/Sources", ext)
        paths[f"{base}/Release"] = ("component_release", (component, "source"), "")
    return paths


def component_release(template, component, arch):
    lines = []
    for key, value in template["component_release"]:
        value = value.replace("@arch", arch).replace("@component", component)
        lines.append(f"{key}: {value}")
    return ("\n".join(lines) + "\n").encode()


def decompress(data, kind):
    try:
        if kind is None:
            out = data
        elif kind == "gz":
            out = gzip.GzipFile(fileobj=__import__("io").BytesIO(data)).read(MAX_INDEX + 1)
        elif kind == "bz2":
            out = bz2.BZ2Decompressor().decompress(data, MAX_INDEX + 1)
        elif kind == "xz":
            out = lzma.LZMADecompressor().decompress(data, MAX_INDEX + 1)
        else:
            raise Refused(f"unknown compression {kind}")
    except (OSError, EOFError, lzma.LZMAError, ValueError) as exc:
        raise Refused(f"cannot decompress ({kind}): {exc}")
    if len(out) > MAX_INDEX:
        raise Refused("an index file decompresses beyond the size limit")
    return out


def check_index_set(template, files):
    """The content of an index set, checked: {base path: decompressed bytes}.
    files: {relative path: bytes}. Every path must be one the template allows,
    every compressed variant must decompress to the same content, and every
    component Release must be exactly the template's."""
    if not isinstance(files, dict) or not files or len(files) > MAX_FILES:
        raise Refused("the index set is empty or too large")
    allowed = allowed_paths(template)
    content = {}
    for path, data in sorted(files.items()):
        if path not in allowed:
            raise Refused(f"the index set contains a file the signer does not sign: {printable(path)}")
        kind, key, ext = allowed[path]
        if kind == "component_release":
            if data != component_release(template, *key):
                raise Refused(f"{path} is not the component Release of the template")
            content[path] = data
            continue
        plain = decompress(data, COMPRESSIONS[ext])
        if key in content and content[key] != plain:
            raise Refused(f"{path} does not decompress to the same content as the other variants of {key}")
        content[key] = plain
    return content


def set_id(content):
    """The identity of approved content: sha256 over every decompressed file."""
    return sha(canonical({path: sha(data) for path, data in sorted(content.items())}).encode())


# ---- Packages / Sources entries ---------------------------------------------

def parse_stanzas(text, path):
    stanzas = []
    for block in text.split("\n\n"):
        if not block.strip():
            continue
        fields, last = {}, None
        for line in block.split("\n"):
            if not line:
                continue
            if line[0] in " \t":
                if last is None:
                    raise Refused(f"{path}: continuation line without a field")
                fields[last] += "\n" + line
                continue
            if ":" not in line:
                raise Refused(f"{path}: malformed line")
            key, value = line.split(":", 1)
            if not FIELD_RE.fullmatch(key):
                raise Refused(f"{path}: malformed field name")
            if key in fields:
                raise Refused(f"{path}: field {key} appears twice in one entry")
            fields[key], last = value.strip(), key
        stanzas.append(fields)
    return stanzas


def entries(content):
    """{(index, package, version, arch): fields} of every Packages/Sources in the
    content, each validated. A repository lists several versions of a package
    (rehearsal deviation 6); an entry is a duplicate only when index, package,
    version and architecture all match."""
    result = {}
    for path, data in sorted(content.items()):
        if path.endswith("/Release"):
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            raise Refused(f"{path}: not UTF-8")
        for fields in parse_stanzas(text, path):
            name, version = fields.get("Package"), fields.get("Version")
            arch = fields.get("Architecture", "source" if path.endswith("Sources") else None)
            if not (name and NAME_RE.fullmatch(name)) or not (version and VERSION_RE.fullmatch(version)) \
                    or not (arch and ARCH_RE.fullmatch(arch)):
                raise Refused(f"{path}: an entry has an invalid Package, Version or Architecture")
            if path.endswith("Packages"):
                if not SHA256_RE.fullmatch(fields.get("SHA256", "")) or not fields.get("Size", "").isdigit() \
                        or not FILENAME_RE.fullmatch(fields.get("Filename", "")) or ".." in fields["Filename"].split("/"):
                    raise Refused(f"{path}: entry {name} has an invalid SHA256, Size or Filename")
            key = (path, name, version, arch)
            if key in result:
                raise Refused(f"{path}: {name} {version} {arch} is listed twice")
            result[key] = fields
    return result


def diff(base_entries, new_entries):
    """What May sees: per record, added / removed / changed, from validated
    fields only. Other changed fields appear by name with the hashes of their
    old and new values, never their text."""
    changes = []
    for key in sorted(set(base_entries) | set(new_entries)):
        old, new = base_entries.get(key), new_entries.get(key)
        if old == new:
            continue
        index, name, version, arch = key
        row = {"index": index, "package": name, "version": version, "arch": arch,
               "change": "added" if old is None else "removed" if new is None else "changed"}
        others = sorted(k[2] for k in base_entries if k[:2] == (index, name) and k[3] == arch and k[2] != version)
        if others:
            row["other_versions_before"] = others
        for side, fields in (("old", old), ("new", new)):
            if fields:
                row[side] = {"version": fields["Version"], "sha256": fields.get("SHA256"), "size": fields.get("Size")}
        if old and new:
            other = sorted(k for k in set(old) | set(new)
                           if k not in ("Package", "Version", "Architecture", "SHA256", "Size")
                           and old.get(k) != new.get(k))
            row["other_fields"] = [{"field": k, "old": sha((old.get(k) or "").encode())[:16],
                                    "new": sha((new.get(k) or "").encode())[:16]} for k in other]
        changes.append(row)
    return changes


# ---- Release -----------------------------------------------------------------

def format_date(moment):
    return moment.astimezone(timezone.utc).strftime(DATE_FMT)


def build_release(template, files, date):
    """The Release the signer publishes: the template's fields, Date and
    Valid-Until from the signer's clock, and every file of the (checked) index
    set with its size and checksums, in aptly's format and order."""
    valid = date + timedelta(days=template["valid_days"])
    lines = []
    for key, value in template["release"]:
        value = value.replace("@date", format_date(date)).replace("@valid_until", format_date(valid))
        lines.append(f"{key}: {value}")
    for section, algo in SECTIONS:
        lines.append(f"{section}:")
        for path in sorted(files):
            lines.append(f" {sha(files[path], algo)} {len(files[path]):8d} {path}")
    return ("\n".join(lines) + "\n").encode()


def release_date(release_text, field="Date"):
    for line in release_text.splitlines():
        if line.startswith(f"{field}:"):
            return datetime.strptime(line.split(":", 1)[1].strip(), DATE_FMT).replace(tzinfo=timezone.utc)
    return None


def compare_release(aptly_release, own_release):
    """None if aptly's Release equals the signer's apart from the Date value and
    the Valid-Until line (aptly writes none); else the first difference."""
    try:
        theirs = aptly_release.decode("utf-8").split("\n")
    except UnicodeDecodeError:
        return "aptly's Release is not UTF-8"
    if any(line.startswith("Valid-Until:") for line in theirs):
        return "aptly's Release carries a Valid-Until"
    ours = [line for line in own_release.decode().split("\n") if not line.startswith("Valid-Until:")]
    field_names = lambda lines: [l.split(":", 1)[0] for l in lines if l and l[0] not in " \t" and ":" in l]
    a_fields, b_fields = field_names(theirs), field_names(ours)
    for name in b_fields:
        if name not in a_fields:
            return f"field {printable(name)} is missing from aptly's Release"
    for name in a_fields:
        if name not in b_fields:
            return f"field {printable(name)} is not in the signer's Release"
    if a_fields != b_fields:
        return "the fields are in another order than the signer's Release"
    for i in range(max(len(theirs), len(ours))):
        a = theirs[i] if i < len(theirs) else None
        b = ours[i] if i < len(ours) else None
        if a is not None and b is not None and a.startswith("Date:") and b.startswith("Date:"):
            continue
        if a != b:
            line = b if b is not None else a
            if line.startswith(" "):
                path = line.split()[-1] if line.split() else "?"
                return f"a checksum line differs from the signer's Release (file {printable(path)})"
            return f"field {printable(line.split(':', 1)[0])} differs from the signer's Release"
    return None


# ---- state -------------------------------------------------------------------

def new_state():
    return {"schema": 1, "last_live": None, "proposals": {}, "approvals": {}, "signed": {}, "last_date": None,
            "current": None, "log": []}


def check_state(state):
    if not isinstance(state, dict) or state.get("schema") != 1:
        raise Refused("the signer state is missing or corrupt; nothing is signed")
    return state


def log(state, message):
    state["log"] = (state.get("log") or [])[-999:] + [printable(message)]


def live_entries(state):
    live = state.get("last_live")
    return {tuple(json.loads(k)): v for k, v in (live or {}).get("entries", {}).items()}


def store_entries(found):
    return {json.dumps(list(k)): v for k, v in found.items()}


def propose(state, template, files, task_id, deb_checker, now, max_pending=8):
    """A proposal from builder: checked, diffed against last-live by the signer.
    deb_checker(fields) -> "scripts" / "no scripts", or raises Refused."""
    check_state(state)
    if len(state["proposals"]) >= max_pending:
        raise Refused("too many pending proposals")
    content = check_index_set(template, files)
    found = entries(content)
    changes = diff(live_entries(state), found)
    if not changes and state.get("last_live") and state["last_live"]["set_id"] == set_id(content):
        raise Refused("the proposal is the content that is already live")
    for row in changes:
        if row["change"] != "removed" and row["index"].endswith("Packages"):
            row["maintainer_scripts"] = deb_checker(found[(row["index"], row["package"], row["version"], row["arch"])])
    pid = sha(canonical([set_id(content), format_date(now)]).encode())[:16]
    state["proposals"][pid] = {
        "set_id": set_id(content), "base": (state.get("last_live") or {}).get("set_id"),
        "task_id": task_id if isinstance(task_id, str) and TASK_RE.fullmatch(task_id) else None,
        "diff": changes, "entries": store_entries(found), "received": format_date(now)}
    log(state, f"proposal {pid}: {len(changes)} changes")
    return pid


def console_lines(state, pid):
    """The console's text for one proposal: signer-computed, printable only."""
    p = state["proposals"][pid]
    out = [f"proposal {pid}  received {p['received']}"]
    out.append(f"task (claimed by builder): {p['task_id']}" if p["task_id"] else "task: (not shown)")
    out.append(f"base: {p['base'] or '(empty repository)'}   new content: {p['set_id']}")
    for row in p["diff"]:
        line = f"{row['change']:8} {row['package']} {row['arch']}"
        if "old" in row:
            line += f"  old {row['old']['version']} sha256 {row['old']['sha256']} size {row['old']['size']}"
        if "new" in row:
            line += f"  new {row['new']['version']} sha256 {row['new']['sha256']} size {row['new']['size']}"
        if "maintainer_scripts" in row:
            line += f"  [{row['maintainer_scripts']}]"
        if row.get("other_versions_before"):
            line += f"  (other versions before: {', '.join(row['other_versions_before'])})"
        out.append(line)
        for f in row.get("other_fields", []):
            out.append(f"         field {f['field']} changed ({f['old']} -> {f['new']})")
    return [printable(line) for line in out]


def approve(state, pid):
    check_state(state)
    p = state["proposals"].get(pid)
    if p is None:
        raise Refused("no such proposal")
    if p["base"] != (state.get("last_live") or {}).get("set_id"):
        raise Refused("the proposal's base is no longer last-live; it needs a new proposal")
    state["approvals"][pid] = {"set_id": p["set_id"], "base": p["base"], "entries": p["entries"],
                               "status": "approved", "signed_key": None}
    del state["proposals"][pid]
    log(state, f"approval {pid}")
    return pid


def reject(state, pid):
    state["proposals"].pop(pid, None)
    log(state, f"rejected {pid}")


def next_date(state, now, template=None):
    """The signer's clock, backdated by the template's date_backdate_seconds
    (clients with a slow clock refuse a Release dated in their future: target2
    was 4.5 minutes behind), whole seconds, strictly after the last signed Date."""
    back = int((template or {}).get("date_backdate_seconds", 0))
    date = (now - timedelta(seconds=back)).replace(microsecond=0)
    last = state.get("last_date")
    if last:
        last = datetime.fromisoformat(last)
        if date <= last:
            date = last + timedelta(seconds=1)
    return date


def request_key(aptly_release, files):
    return sha(canonical([sha(aptly_release), {p: sha(d) for p, d in sorted(files.items())}]).encode())


def sign(state, template, aptly_release, files, backend, now):
    """aptly's gpg call, through the stand-in: returns the signer's
    {"release", "inrelease", "release_gpg"} (bytes)."""
    check_state(state)
    key = request_key(aptly_release, files)
    done = state["signed"].get(key)
    if done is not None:
        approval = state["approvals"].get(done["approval"])
        if approval is None or approval["status"] != "signed" or approval["base"] != (state.get("last_live") or {}).get("set_id"):
            raise Refused("this Release was signed for an approval that is no longer valid")
        return {k: bytes.fromhex(done[k]) for k in ("release", "inrelease", "release_gpg")}
    content = check_index_set(template, files)
    sid = set_id(content)
    live = (state.get("last_live") or {}).get("set_id")
    candidates = [aid for aid, a in state["approvals"].items() if a["set_id"] == sid]
    usable = [aid for aid in candidates if state["approvals"][aid]["status"] == "approved"
              and state["approvals"][aid]["base"] == live]
    if not usable:
        if any(state["approvals"][aid]["status"] != "approved" for aid in candidates):
            raise Refused("the approval for this content was already used")
        if candidates:
            raise Refused("the approval for this content was made against another last-live state")
        raise Refused("this content was not approved on the signer console")
    aid = usable[0]
    date = next_date(state, now, template)
    own = build_release(template, files, date)
    difference = compare_release(aptly_release, own)
    if difference:
        raise Refused(difference)
    trio = signed_trio(backend, own)
    state["signed"][key] = {"approval": aid, "set_id": sid, "date": date.isoformat(),
                            "files": {p: d.hex() for p, d in files.items()},
                            **{k: v.hex() for k, v in trio.items()}}
    state["approvals"][aid].update(status="signed", signed_key=key)
    state["last_date"] = date.isoformat()
    log(state, f"signed {aid} Date {format_date(date)}")
    return trio


def signed_trio(backend, own):
    detached, clear = backend.sign_detached(own), backend.sign_clear(own)
    if not backend.verify_detached(detached, own):
        raise Refused("the detached signature does not verify over the signer's Release")
    if backend.verify_clear(clear) != own:
        raise Refused("InRelease does not verify, or is not over the same bytes as Release.gpg")
    return {"release": own, "inrelease": clear, "release_gpg": detached}


def live(state, served_inrelease):
    """builder reports the switch: the InRelease served must be exactly the one
    the signer produced for an approval that is signed, unconsumed, and based on
    the current last-live. Then last-live moves; the approval is consumed and
    every other approval is revoked."""
    check_state(state)
    current = (state.get("last_live") or {}).get("set_id")
    for key, done in state["signed"].items():
        if bytes.fromhex(done["inrelease"]) != served_inrelease:
            continue
        approval = state["approvals"].get(done["approval"])
        if approval is None or approval["status"] != "signed" or approval["signed_key"] != key \
                or approval["base"] != current:
            raise Refused("the served InRelease belongs to an approval that is used, revoked or not based on last-live")
        state["last_live"] = {"set_id": done["set_id"], "entries": approval["entries"], "signed_key": key}
        state["current"] = key
        state["approvals"] = {}
        state["proposals"] = {pid: p for pid, p in state["proposals"].items() if p["base"] == done["set_id"]}
        log(state, f"live {done['approval']}")
        return done["set_id"]
    raise Refused("the served InRelease is not one the signer produced for a pending approval")


def resign(state, template, backend, now):
    """Scheduled re-sign: last-live only, from the template and the stored files
    of the approved set; nothing from builder."""
    check_state(state)
    live_state = state.get("last_live")
    if not live_state:
        raise Refused("nothing is live; nothing to re-sign")
    base = state["signed"][live_state["signed_key"]]
    files = {p: bytes.fromhex(d) for p, d in base["files"].items()}
    if set_id(check_index_set(template, files)) != live_state["set_id"]:
        raise Refused("the stored files of last-live do not match its content")
    date = next_date(state, now, template)
    own = build_release(template, files, date)
    trio = signed_trio(backend, own)
    key = "resign-" + sha(own)
    state["signed"][key] = {"approval": None, "set_id": live_state["set_id"], "date": date.isoformat(),
                            "files": base["files"], **{k: v.hex() for k, v in trio.items()}}
    state["current"] = key
    state["last_date"] = date.isoformat()
    log(state, f"re-signed last-live Date {format_date(date)}")
    return trio


def resign_set(state, sid):
    """A re-sign is only ever of last-live."""
    if sid != (state.get("last_live") or {}).get("set_id"):
        raise Refused("only the last-live set is re-signed")


def current_trio(state):
    key = state.get("current")
    if not key:
        raise Refused("nothing is live")
    done = state["signed"][key]
    return {k: bytes.fromhex(done[k]) for k in ("release", "inrelease", "release_gpg")}
