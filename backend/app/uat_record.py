"""Create and validate a candidate-bound Learn Smart AI UAT record."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

from .release_candidate import CandidateVerificationError, load_and_verify_artifact


REQUIREMENT_IDS = (
    "AUTH-01", "AUTH-02", "CUR-01", "ASM-01", "TUT-01", "TUT-02", "TUT-03",
    "TUT-04", "TUT-05", "TUT-06", "MAST-01", "PROG-01", "PROG-02", "PROG-03",
    "PARENT-01", "PARENT-02", "DOC-01", "DOC-02", "DOC-03", "UX-01", "DATA-01",
    "SEC-01", "SEC-02", "UP-01", "QA-01",
)
DECISIONS = {"PENDING", "ACCEPTED", "REJECTED"}
RESULTS = {"PENDING", "PASS", "FAIL", "NOT_TESTABLE", "SCOPE_ACCEPTED"}
ISSUE_FIELDS = {"id", "requirement_ids", "steps", "expected", "actual", "impact", "evidence", "fix_commit", "retest", "status"}


class UatRecordError(ValueError):
    """The record is incomplete, inconsistent, or not valid acceptance evidence."""


def new_record(manifest: dict[str, object]) -> dict[str, object]:
    return {
        "candidate": {
            "git_commit": manifest["git_commit"],
            "version_name": manifest["version_name"],
            "version_code": manifest["version_code"],
            "apk_sha256": manifest["apk_sha256"],
            "signing_certificate_sha256": manifest["signing_certificate_sha256"],
            "backend_url": manifest["backend_url"],
        },
        "tester": {"name": "", "role": "", "tested_at": ""},
        "device": {"model": "", "android_version": "", "screen": "", "font_scale": "", "theme": ""},
        "requirements": [
            {"id": requirement, "result": "PENDING", "evidence": "", "scope_approval": ""}
            for requirement in REQUIREMENT_IDS
        ],
        "issues": [],
        "decision": "PENDING",
        "decision_note": "",
    }


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _candidate_matches(candidate: object, manifest: dict[str, object]) -> None:
    expected = {key: manifest[key] for key in (
        "git_commit", "version_name", "version_code", "apk_sha256",
        "signing_certificate_sha256", "backend_url",
    )}
    if candidate != expected:
        raise UatRecordError("UAT candidate identity does not match the verified APK manifest")


def validate_record(record: object, manifest: dict[str, object], *, require_acceptance: bool = False) -> dict[str, object]:
    if not isinstance(record, dict) or set(record) != {
        "candidate", "tester", "device", "requirements", "issues", "decision", "decision_note"
    }:
        raise UatRecordError("UAT record fields are incomplete or unexpected")
    _candidate_matches(record["candidate"], manifest)
    if record["decision"] not in DECISIONS:
        raise UatRecordError("UAT decision is invalid")
    requirements = record["requirements"]
    if not isinstance(requirements, list) or len(requirements) != len(REQUIREMENT_IDS):
        raise UatRecordError("UAT requirement coverage is incomplete")
    by_id = {}
    for item in requirements:
        if not isinstance(item, dict) or set(item) != {"id", "result", "evidence", "scope_approval"}:
            raise UatRecordError("UAT requirement result fields are invalid")
        if item["id"] in by_id or item["id"] not in REQUIREMENT_IDS or item["result"] not in RESULTS:
            raise UatRecordError("UAT requirement identity or result is invalid")
        by_id[item["id"]] = item
    if set(by_id) != set(REQUIREMENT_IDS):
        raise UatRecordError("UAT requirement coverage is incomplete")
    issues = record["issues"]
    if not isinstance(issues, list) or any(
        not isinstance(issue, dict) or set(issue) != ISSUE_FIELDS
        or issue.get("status") not in {"OPEN", "CLOSED"}
        for issue in issues
    ):
        raise UatRecordError("UAT issues must be structured records")
    if require_acceptance and record["decision"] != "ACCEPTED":
        raise UatRecordError("UAT has not been accepted")
    if record["decision"] == "ACCEPTED":
        tester = record["tester"]
        device = record["device"]
        if (not isinstance(tester, dict) or set(tester) != {"name", "role", "tested_at"}
                or not all(_nonempty(tester.get(key)) for key in tester)):
            raise UatRecordError("Accepted UAT requires tester identity, role, and time")
        try:
            tested_at = datetime.fromisoformat(tester["tested_at"].replace("Z", "+00:00"))
        except ValueError as exc:
            raise UatRecordError("UAT tested_at must be an ISO-8601 timestamp") from exc
        if tested_at.tzinfo is None:
            raise UatRecordError("UAT tested_at must include a timezone")
        if (not isinstance(device, dict) or set(device) != {"model", "android_version", "screen", "font_scale", "theme"}
                or not all(_nonempty(device.get(key)) for key in device)):
            raise UatRecordError("Accepted UAT requires complete physical-device details")
        for requirement, item in by_id.items():
            if item["result"] not in {"PASS", "SCOPE_ACCEPTED"} or not _nonempty(item["evidence"]):
                raise UatRecordError(f"Accepted UAT lacks passing evidence for {requirement}")
            if item["result"] == "SCOPE_ACCEPTED" and not _nonempty(item["scope_approval"]):
                raise UatRecordError(f"Accepted scope change lacks explicit approval for {requirement}")
        if any(issue.get("status") != "CLOSED" for issue in issues):
            raise UatRecordError("Accepted UAT contains an unresolved issue")
        if not _nonempty(record["decision_note"]):
            raise UatRecordError("Accepted UAT requires an explicit decision note")
    return record


def _read_json(path: Path, label: str) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise UatRecordError(f"{label} is unreadable") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    init = subparsers.add_parser("init")
    init.add_argument("manifest", type=Path)
    init.add_argument("output", type=Path)
    verify = subparsers.add_parser("verify")
    verify.add_argument("manifest", type=Path)
    verify.add_argument("record", type=Path)
    verify.add_argument("--require-acceptance", action="store_true")
    args = parser.parse_args()
    try:
        manifest = load_and_verify_artifact(args.manifest)
        if args.command == "init":
            if args.output.exists():
                raise UatRecordError("Refusing to overwrite an existing UAT record")
            args.output.write_text(json.dumps(new_record(manifest), indent=2) + "\n", encoding="utf-8")
            print(args.output)
        else:
            record = validate_record(_read_json(args.record, "UAT record"), manifest,
                                     require_acceptance=args.require_acceptance)
            print(json.dumps({"valid": True, "decision": record["decision"],
                              "git_commit": manifest["git_commit"]}, sort_keys=True))
    except (CandidateVerificationError, UatRecordError) as exc:
        parser.exit(2, f"UAT record verification failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
