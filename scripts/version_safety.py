#!/usr/bin/env python3
"""Apply Debian version ordering to measured archive and apt-candidate data."""

import argparse
import json
from pathlib import Path
import subprocess
import sys


def dpkg_cmp(left, operator, right):
    return subprocess.run(["dpkg", "--compare-versions", left, operator, right], check=False).returncode == 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path, help="JSON containing measured apt-cache/rmadison versions")
    parser.add_argument("--write", type=Path, help="write result JSON here; defaults to stdout")
    args = parser.parse_args()
    try: data = json.loads(args.record.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc: parser.error(f"cannot read input: {exc}")
    required = ("source_package", "source_commit", "target_series", "candidate_source_version", "candidate_binary_package", "candidate_binary_version", "apt_candidate_binary_package", "apt_candidate_binary_version", "archive_source_versions", "update_source_versions", "future_update_source_versions")
    missing = [key for key in required if key not in data]
    list_fields = ("archive_source_versions", "update_source_versions", "future_update_source_versions")
    if "newer_release_source_versions" in data:
        list_fields += ("newer_release_source_versions",)
    invalid_lists = [key for key in list_fields
                     if key in data and (not isinstance(data[key], list) or any(not isinstance(v, str) or not v for v in data[key]))]
    result = {"schema": 1, "result": "UNKNOWN", "reasons": []}
    if missing:
        result["reasons"].append("missing inputs: " + ", ".join(missing))
    elif invalid_lists:
        result["reasons"].append("version lists must be arrays of non-empty strings: " + ", ".join(invalid_lists))
    else:
        candidate = str(data["candidate_source_version"])
        updates = [str(value) for value in data["update_source_versions"]]
        archives = [str(value) for value in data["archive_source_versions"]]
        future = [str(value) for value in data["future_update_source_versions"]]
        apt_candidate = str(data["apt_candidate_binary_version"])
        binary_candidate = str(data["candidate_binary_version"])
        if not data["source_package"] or not data["source_commit"] or not candidate or not data["candidate_binary_package"] or not data["apt_candidate_binary_package"] or not binary_candidate or not apt_candidate or not isinstance(data["target_series"], str) or not archives:
            result["reasons"].append("empty or invalid version/series value, or archive_source_versions is empty")
        elif data["candidate_binary_package"] != data["apt_candidate_binary_package"]:
            result.update(result="UNSAFE", reasons=["apt-cache policy selected a different binary package"])
        elif apt_candidate != binary_candidate:
            result.update(result="UNSAFE", reasons=["apt-cache policy selects a binary version other than the candidate"])
        elif any(not dpkg_cmp(candidate, "gt", value) for value in updates):
            result.update(result="REPLACES_SECURITY_UPDATE", reasons=["candidate source version is not newer than a relevant update/security version"])
        elif any(not dpkg_cmp(candidate, "gt", value) for value in future):
            result.update(result="BLOCKS_FUTURE_UPDATE", reasons=["candidate ordering is not newer than a recorded future update in the target series"])
        elif not all(dpkg_cmp(candidate, "gt", value) for value in archives):
            result.update(result="UNSAFE", reasons=["candidate is not newer than every target archive source version"])
        elif data.get("archive_checked") is not True or data.get("apt_policy_checked") is not True or not data.get("checked_at"):
            result["reasons"].append("record archive_checked, apt_policy_checked, and checked_at after collecting real archive evidence")
        else:
            result.update(result="SAFE", reasons=["dpkg ordering and recorded apt candidate checks pass"])
        result.update({key: data.get(key) for key in required})
        result["checked_at"] = data.get("checked_at")
        result["archive_checked"] = data.get("archive_checked")
        result["apt_policy_checked"] = data.get("apt_policy_checked")
        newer_release_versions = data.get("newer_release_source_versions")
        if newer_release_versions is not None:
            result["reference_only"] = {
                "newer_release_source_versions": newer_release_versions,
                "note": "Newer-series versions are recorded for context and do not determine safety for the target series.",
            }
    output = json.dumps(result, indent=2) + "\n"
    if args.write:
        args.write.write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)
    return 0 if result["result"] == "SAFE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
