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
FILENAME_RE = re.compile(r"pool/[A-Za-z0-9][A-Za-z0-9+._~/-]*\.d?deb")  # .deb and .ddeb (debug symbols); .udeb stays excluded, as publish_aptly also rejects it
TASK_RE = re.compile(r"UNITY-[0-9]{8}-[0-9]{3}")
SCRIPT_NAMES = ("preinst", "postinst", "prerm", "postrm", "config")
# The routine policy (permission model phase 5, May's decision 4): the numbers
# are May's; the code accepts a policy only within these bounds.
POLICY_FIELDS = {"max_sources": (1, 1), "max_binary_records": (1, 1000), "min_interval_seconds": (1, 86400),
                 "max_per_utc_day": (1, 100)}
DIGITS_RE = re.compile(r"[0-9]+")
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


# ---- Debian version ordering (dpkg lib/dpkg/version.c, verrevcmp) --------------

def _order(c):
    if c == "~":
        return -1
    if c.isdigit():
        return 0
    if c.isalpha() and c.isascii():
        return ord(c)
    return ord(c) + 256


def _verrevcmp(a, b):
    i = j = 0
    while i < len(a) or j < len(b):
        first_diff = 0
        while (i < len(a) and not a[i].isdigit()) or (j < len(b) and not b[j].isdigit()):
            ac = _order(a[i]) if i < len(a) and not a[i].isdigit() else 0
            bc = _order(b[j]) if j < len(b) and not b[j].isdigit() else 0
            if ac != bc:
                return ac - bc
            if i < len(a) and not a[i].isdigit():
                i += 1
            if j < len(b) and not b[j].isdigit():
                j += 1
        while i < len(a) and a[i] == "0":
            i += 1
        while j < len(b) and b[j] == "0":
            j += 1
        while i < len(a) and a[i].isdigit() and j < len(b) and b[j].isdigit():
            if not first_diff:
                first_diff = ord(a[i]) - ord(b[j])
            i += 1
            j += 1
        if i < len(a) and a[i].isdigit():
            return 1
        if j < len(b) and b[j].isdigit():
            return -1
        if first_diff:
            return first_diff
    return 0


def _split_version(version):
    epoch, upstream, revision = 0, version, ""
    if ":" in upstream:
        head, upstream = upstream.split(":", 1)
        epoch = int(head)
    if "-" in upstream:
        upstream, revision = upstream.rsplit("-", 1)
    return epoch, upstream, revision


def version_compare(a, b):
    """<0, 0 or >0 as `dpkg --compare-versions` orders a against b (versions
    already matched by VERSION_RE). Tested against scripts/tests/data/dpkg_version_order.json."""
    ea, ua, ra = _split_version(a)
    eb, ub, rb = _split_version(b)
    if ea != eb:
        return ea - eb
    return _verrevcmp(ua, ub) or _verrevcmp(ra, rb)


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
        elif kind in ("bz2", "xz"):
            # exactly one complete stream: a second stream or trailing bytes
            # would be read differently by other tools (Verifier round 1)
            d = bz2.BZ2Decompressor() if kind == "bz2" else lzma.LZMADecompressor()
            out = d.decompress(data, MAX_INDEX + 1)
            if len(out) <= MAX_INDEX and (not d.eof or d.unused_data):
                raise Refused(f"a {kind} index is not exactly one complete stream")
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
                if not SHA256_RE.fullmatch(fields.get("SHA256", "")) or not DIGITS_RE.fullmatch(fields.get("Size", "")) \
                        or not FILENAME_RE.fullmatch(fields.get("Filename", "")) or ".." in fields["Filename"].split("/"):
                    raise Refused(f"{path}: entry {name} has an invalid SHA256, Size or Filename")
            key = (path, name, version, arch)
            if key in result:
                raise Refused(f"{path}: {name} {version} {arch} is listed twice")
            result[key] = fields
    return result


def source_of(key, fields):
    """(source name, source version) of an entry: Sources rows name themselves;
    a Packages row names its Source ("name" or "name (version)"), else itself."""
    index, name, version, arch = key
    if index.endswith("Sources"):
        return name, version
    source = (fields.get("Source") or "").strip()
    match = re.fullmatch(r"([a-z0-9][a-z0-9+.-]+)(?:\s+\(([^()\s]+)\))?", source) if source else None
    if source and not match:
        return None, None  # a Source field the signer cannot read: not a known source
    if match:
        return match.group(1), match.group(2) or version
    return name, version


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


def live_scripts(state):
    """{entry key: {script name: sha256}} of last-live, for the entries whose
    .deb the signer read; an entry without a map is unknown (not routine)."""
    live = state.get("last_live")
    return {tuple(json.loads(k)): v for k, v in (live or {}).get("scripts", {}).items()}


def script_flag(result):
    """A deb checker's answer is the console text, or (text, {name: sha256}),
    or (text, map, control fields of the .deb)."""
    if isinstance(result, tuple):
        return result[0], dict(result[1]), (dict(result[2]) if len(result) > 2 and result[2] is not None else None)
    return result, None, None


def check_control(key, fields, control):
    """The .deb's own control must describe the Packages row that names it
    (Verifier R1): Package, Version, Architecture and the source name."""
    for name in ("Package", "Version", "Architecture"):
        if control.get(name) != fields.get(name):
            raise Refused(f"the .deb of {printable(fields['Package'])} {printable(fields['Version'])} says "
                          f"{name} {printable(control.get(name))}: the Packages row does not describe it")
    if source_of(key, control)[0] != source_of(key, fields)[0]:
        raise Refused(f"the .deb of {printable(fields['Package'])} names source {printable(source_of(key, control)[0])}, "
                      f"the Packages row {printable(source_of(key, fields)[0])}")


def store_entries(found):
    return {json.dumps(list(k)): v for k, v in found.items()}


class DebSet:
    """The .debs builder sends with a proposal (design amendment (b), after the
    rehearsal: a new .deb is not on :8080 before the switch). The signer takes
    the maintainer-script flag only from bytes that match the SHA256 and Size of
    an entry in the Packages it checked itself; a missing, mismatched or extra
    .deb refuses the proposal. scanner(bytes) -> "scripts: ..." / "no scripts"."""

    def __init__(self, debs, scanner):
        if not isinstance(debs, dict):
            raise Refused("debs must be an object")
        self.debs, self.scanner, self.used = debs, scanner, set()

    def __call__(self, fields):
        name = fields["Filename"]
        data = self.debs.get(name)
        if data is None:
            raise Refused(f"the proposal lacks the .deb of {printable(name)}")
        if len(data) != int(fields["Size"]) or sha(data) != fields["SHA256"]:
            raise Refused(f"the .deb sent for {printable(name)} does not match its Packages SHA256 or Size")
        self.used.add(name)
        return self.scanner(data)

    def unused(self):
        return sorted(set(self.debs) - self.used)


def existing_proposal(state, sid, base):
    """The pending proposal or the unused approval of this content on this base,
    if any (a rerun of the publisher must not create a second copy)."""
    for pid, p in state["proposals"].items():
        if p["set_id"] == sid and p["base"] == base:
            return pid
    for aid, a in state["approvals"].items():
        if a["set_id"] == sid and a["base"] == base and a["status"] == "approved":
            return aid
    return None


def propose(state, template, files, task_id, deb_checker, now, max_pending=8, policy=None):
    """A proposal from builder: checked, diffed against last-live by the signer.
    deb_checker(fields) -> "scripts: ..." / "no scripts" or (that text, {script:
    sha256}), or raises Refused; it is asked for every entry whose SHA256 is not
    in last-live (added, or changed under the same name, version and arch).
    With a policy (phase 5), a routine proposal is approved at once by it."""
    check_state(state)
    content = check_index_set(template, files)
    found = entries(content)
    sid = set_id(content)
    base_id = (state.get("last_live") or {}).get("set_id")
    known = existing_proposal(state, sid, base_id)
    if known:
        log(state, f"proposal {known}: proposed again, same content and base")
        return known
    if len(state["proposals"]) >= max_pending:
        raise Refused("too many pending proposals")
    base = live_entries(state)
    changes = diff(base, found)
    if not changes and state.get("last_live") and state["last_live"]["set_id"] == sid:
        raise Refused("the proposal is the content that is already live")
    live_shas = {fields.get("SHA256") for fields in base.values()}
    known_maps = live_scripts(state)
    scripts = {}
    for key, fields in found.items():
        if key in base and base[key] == fields and key in known_maps:
            scripts[key] = known_maps[key]  # unchanged entry: the map is known
    for row in changes:
        if row["change"] == "removed" or not row["index"].endswith("Packages"):
            continue
        key = (row["index"], row["package"], row["version"], row["arch"])
        fields = found[key]
        if fields["SHA256"] not in live_shas:
            row["maintainer_scripts"], found_map, control = script_flag(deb_checker(fields))
            if control is not None:
                check_control(key, fields, control)
            if found_map is not None:
                scripts[key] = found_map
    extra = deb_checker.unused() if hasattr(deb_checker, "unused") else []
    if extra:
        raise Refused(f"the proposal carries .debs that are not new in it: {printable(', '.join(extra))}")
    pid = sha(canonical([sid, format_date(now)]).encode())[:16]
    state["proposals"][pid] = {
        "set_id": sid, "base": base_id,
        "task_id": task_id if isinstance(task_id, str) and TASK_RE.fullmatch(task_id) else None,
        "diff": changes, "entries": store_entries(found), "scripts": store_entries(scripts),
        "received": format_date(now)}
    log(state, f"proposal {pid}: {len(changes)} changes")
    state["auto_signed"] = [h for h in (state.get("auto_signed") or [])
                            if (now - datetime.fromisoformat(h["at"])).total_seconds() <= 2 * 86400]  # rules 8-9: 2 days
    if policy is not None:
        ok, reasons = routine(state, pid, policy, now)
        state["proposals"][pid]["policy"] = {"routine": ok, "reasons": reasons}
        if ok:
            summary = routine_summary(state["proposals"][pid])
            approve(state, pid, approved_by="policy")
            state["auto_signed"] = (state.get("auto_signed") or [])[-199:] + [
                {"at": now.isoformat(), "task_id": state["approvals"][pid]["task_id"], "pid": pid, "set_id": sid,
                 "shown": False}]
            log(state, f"auto-approved by policy: {pid} {summary}")
    return pid


def proposal_status(state, pid):
    """What the publisher hears: approved (by whom) or pending (why)."""
    if pid in state["approvals"]:
        return {"status": "approved", "approved_by": state["approvals"][pid].get("approved_by", "May"), "reasons": []}
    p = state["proposals"].get(pid)
    if p is None:
        raise Refused("no such proposal")
    return {"status": "pending", "approved_by": None, "reasons": list((p.get("policy") or {}).get("reasons", []))}


def check_policy(policy):
    """The problems of a policy object; [] when it is usable."""
    if not isinstance(policy, dict):
        return ["the policy is not an object"]
    problems = []
    if policy.get("schema") != 1:
        problems.append("policy: unsupported schema")
    if not isinstance(policy.get("auto_approve"), bool):
        problems.append("policy: auto_approve must be true or false")
    for key, (low, high) in POLICY_FIELDS.items():
        value = policy.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
            problems.append(f"policy: {key} must be an integer between {low} and {high}")
    return problems


def routine_summary(p):
    added = [r for r in p["diff"] if r["change"] == "added"]
    names = sorted({source_of((r["index"], r["package"], r["version"], r["arch"]),
                              p["entries"][json.dumps([r["index"], r["package"], r["version"], r["arch"]])])[0] or "?"
                    for r in added})
    versions = sorted({r["version"] for r in added})
    binaries = len([r for r in added if r["index"].endswith("Packages")])
    return printable(f"{p.get('task_id')} {','.join(names)} {','.join(versions)} ({binaries} binaries)")


def routine(state, pid, policy, now):
    """May's decision 4 as code: (True, []) when the proposal may be approved
    without him, else (False, reasons). Everything is taken from what the signer
    computed itself; nothing from builder's text."""
    if isinstance(policy, dict) and policy.get("_problem"):
        return False, [printable(policy["_problem"])]  # the service could not read a usable policy file
    problems = check_policy(policy)
    if problems:
        return False, problems
    if not policy["auto_approve"]:
        return False, ["policy: automatic approval is off"]
    p = state["proposals"][pid]
    reasons = []
    live = state.get("last_live")
    if not live:
        return False, ["no last-live content: an empty repository is never routine"]
    if not state.get("current"):
        # decision 8: the first signing under this signer's key (a publication May approved on the
        # console, or the re-sign of the content he adopted) is his; only then anything is automatic
        return False, ["nothing signed by this signer has gone live yet: the first publication is May's"]
    rows = p["diff"]
    not_added = [r for r in rows if r["change"] != "added"]
    if not_added:
        reasons.append("not only additions: " + ", ".join(sorted({f"{r['change']} {r['package']} {r['version']} {r['arch']}" for r in not_added})[:5]))
    base = live_entries(state)
    found = {tuple(json.loads(k)): v for k, v in p["entries"].items()}
    added = [(r["index"], r["package"], r["version"], r["arch"]) for r in rows if r["change"] == "added"]
    if not added:
        reasons.append("nothing added")
    sources = {}
    for key in added:
        name, version = source_of(key, found[key])
        if name is None:
            reasons.append(f"an added entry has a Source field the signer cannot read: {key[1]}")
            continue
        sources.setdefault(name, set()).add(version)
    live_sources = {source_of(key, fields)[0] for key, fields in base.items()}
    if len(sources) > policy["max_sources"]:
        reasons.append(f"more than {policy['max_sources']} source package: " + ", ".join(sorted(sources)))
    for name, versions in sorted(sources.items()):
        if name not in live_sources:
            reasons.append(f"source {name} is not in last-live: a new package is never routine")
        if len(versions) != 1:
            reasons.append(f"source {name} appears with several versions: " + ", ".join(sorted(versions)))
    for key in added:
        index, name, version, arch = key
        previous = [k for k in base if k[0] == index and k[1] == name and k[3] == arch]
        if not previous:
            reasons.append(f"{name} {arch} is not in last-live under that name and architecture")
            continue
        if any(version_compare(version, k[2]) <= 0 for k in previous):
            reasons.append(f"{name} {version} {arch} is not newer than every live version (" + ", ".join(sorted(k[2] for k in previous)) + ")")
        highest = max(previous, key=lambda k: VersionKey(k[2]))
        if source_of(highest, base[highest])[0] != source_of(key, found[key])[0]:
            reasons.append(f"{name} {arch} was built from another source in last-live ({source_of(highest, base[highest])[0]}): a name takeover is not routine")
        if index.endswith("Packages"):
            old_map = live_scripts(state).get(highest)
            new_map = {tuple(json.loads(k)): v for k, v in p.get("scripts", {}).items()}.get(key)
            if old_map is None:
                reasons.append(f"the maintainer scripts of the live {name} {highest[2]} {arch} are not on record")
            elif new_map is None:
                reasons.append(f"the maintainer scripts of {name} {version} {arch} were not read")
            elif old_map != new_map:
                reasons.append(f"the maintainer scripts of {name} {arch} differ from {highest[2]}")
    binaries = len([k for k in added if k[0].endswith("Packages")])
    if binaries > policy["max_binary_records"]:
        reasons.append(f"{binaries} binary records exceed the limit of {policy['max_binary_records']}")
    task = p.get("task_id")
    if not task:
        reasons.append("the proposal names no valid task id")
    history = state.get("auto_signed") or []
    if task and any(h.get("task_id") == task for h in history):
        reasons.append(f"task {task} was already signed automatically once")
    if history:
        last = datetime.fromisoformat(history[-1]["at"])
        if (now - last).total_seconds() < policy["min_interval_seconds"]:
            reasons.append(f"less than {policy['min_interval_seconds']} s since the last automatic approval")
    today = [h for h in history if datetime.fromisoformat(h["at"]).astimezone(timezone.utc).date() == now.astimezone(timezone.utc).date()]
    if len(today) >= policy["max_per_utc_day"]:
        reasons.append(f"{len(today)} automatic approvals today reach the limit of {policy['max_per_utc_day']}")
    return (not reasons), [printable(r) for r in reasons]


class VersionKey:
    """Orders versions by version_compare (for max/sorted)."""
    def __init__(self, v):
        self.v = v

    def __lt__(self, other):
        return version_compare(self.v, other.v) < 0


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
    policy = p.get("policy")
    if policy:
        out.append("policy: routine, approved automatically" if policy["routine"] else "policy: not routine")
        out += [f"         {reason}" for reason in policy.get("reasons", [])]
    return [printable(line) for line in out]


def auto_approval_lines(state, mark_shown=True):
    """Automatic approvals not yet shown on the console, each with the diff
    May would have seen; they are marked shown."""
    out = []
    for item in state.get("auto_signed") or []:
        if item.get("shown"):
            continue
        a = state["approvals"].get(item["pid"]) or {}
        out.append(f"auto-approved {item['pid']} at {item['at']} task {item['task_id']} ({a.get('status', 'consumed')})")
        for line in a.get("console", []):
            out.append("  " + line)
        if mark_shown:
            item["shown"] = True
    return [printable(line) for line in out]


def approve(state, pid, approved_by="May"):
    check_state(state)
    p = state["proposals"].get(pid)
    if p is None:
        raise Refused("no such proposal")
    if p["base"] != (state.get("last_live") or {}).get("set_id"):
        raise Refused("the proposal's base is no longer last-live; it needs a new proposal")
    state["approvals"][pid] = {"set_id": p["set_id"], "base": p["base"], "entries": p["entries"],
                               "scripts": p.get("scripts", {}), "task_id": p.get("task_id"),
                               "approved_by": approved_by, "console": console_lines(state, pid),
                               "status": "approved", "signed_key": None}
    del state["proposals"][pid]
    log(state, f"approval {pid} by {approved_by}")
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
        state["last_live"] = {"set_id": done["set_id"], "entries": approval["entries"], "signed_key": key,
                              "scripts": approval.get("scripts", {})}
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
    base = state["signed"][live_state["signed_key"]]  # an adopted set stores its files the same way
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


def adopt_live(state, template, files, served_release, deb_checker, now):
    """May's cut-over (phase 5, section 5): the content the repository serves
    becomes last-live without a signature. The index set is checked as a
    proposal, the served Release must be the signer's own apart from Date and
    Valid-Until, every Packages entry's .deb is read for its script map. Once."""
    check_state(state)
    if state.get("last_live"):
        raise Refused("last-live is already set; adoption happens once, on an empty state")
    content = check_index_set(template, files)
    found = entries(content)
    difference = compare_release(served_release, build_release(template, files, now))
    if difference:
        raise Refused(f"the served Release is not one the signer would build: {difference}")
    scripts, flagged = {}, 0
    for key, fields in found.items():
        if key[0].endswith("Packages"):
            text, found_map, control = script_flag(deb_checker(fields))
            if found_map is None:
                raise Refused("the .deb reader gives no script map")
            if control is not None:
                check_control(key, fields, control)
            scripts[key] = found_map
            flagged += bool(found_map)
    extra = deb_checker.unused() if hasattr(deb_checker, "unused") else []
    if extra:
        raise Refused(f"adopt-live was given .debs the Packages do not list: {printable(', '.join(extra))}")
    sid = set_id(content)
    key = "adopt-" + sid
    state["signed"][key] = {"approval": None, "set_id": sid, "date": None, "adopted": now.isoformat(),
                            "files": {p: d.hex() for p, d in files.items()},
                            "release": b"".hex(), "inrelease": b"".hex(), "release_gpg": b"".hex()}
    state["last_live"] = {"set_id": sid, "entries": store_entries(found), "signed_key": key,
                          "scripts": store_entries(scripts), "adopted": now.isoformat()}
    state["approvals"], state["proposals"] = {}, {}
    log(state, f"adopted the served content as last-live: {sid} ({len(found)} entries, {flagged} with scripts)")
    return {"set_id": sid, "entries": len(found), "with_scripts": flagged,
            "sources": sorted({source_of(k, v)[0] or "?" for k, v in found.items()}),
            "served_date": format_date(release_date(served_release.decode("utf-8", "replace")) or now)}


def current_trio(state):
    key = state.get("current")
    if not key:
        raise Refused("nothing is live")
    done = state["signed"][key]
    if done.get("approval") is None and done.get("adopted"):
        raise Refused("last-live was adopted, not yet signed by this signer")
    return {k: bytes.fromhex(done[k]) for k in ("release", "inrelease", "release_gpg")}
