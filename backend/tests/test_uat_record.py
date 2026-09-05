import hashlib
import json
import re
from pathlib import Path

import pytest

from app.release_candidate import load_and_verify_artifact
from app.uat_record import REQUIREMENT_IDS, UatRecordError, new_record, validate_record


def candidate(tmp_path):
    apk = tmp_path / "candidate.apk"
    apk.write_bytes(b"signed-candidate")
    manifest = {
        "product": "Learn Smart AI", "distribution": "private APK", "git_commit": "a" * 40,
        "version_name": "1.0.0-uat.1", "version_code": 3,
        "backend_url": "https://staging.learnsmart.example.org", "apk_file": apk.name,
        "apk_sha256": hashlib.sha256(apk.read_bytes()).hexdigest(),
        "signing_certificate_sha256": "b" * 64, "built_at_utc": "2026-09-05T00:00:00Z",
        "production_verified": False, "uat_accepted": False,
    }
    path = tmp_path / "candidate-manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return load_and_verify_artifact(path)


def accepted_record(manifest):
    record = new_record(manifest)
    record["tester"] = {"name": "Test Owner", "role": "Product owner", "tested_at": "2026-09-05T12:00:00+05:30"}
    record["device"] = {"model": "Physical test phone", "android_version": "16", "screen": "1080x2400", "font_scale": "1.0", "theme": "light and dark"}
    for item in record["requirements"]:
        item.update(result="PASS", evidence=f"Observed {item['id']} journey", scope_approval="")
    record["decision"] = "ACCEPTED"
    record["decision_note"] = "I accept this exact candidate after completing the recorded journeys."
    return record


def test_template_covers_every_preproduction_requirement_once(tmp_path):
    record = new_record(candidate(tmp_path))
    assert tuple(item["id"] for item in record["requirements"]) == REQUIREMENT_IDS
    assert record["decision"] == "PENDING"


def test_requirement_contract_matches_release_ledger():
    ledger = Path(__file__).resolve().parents[2] / "docs" / "release-acceptance.md"
    ids = tuple(re.findall(r"^\| ([A-Z]+-[0-9]+) \|", ledger.read_text(encoding="utf-8"), re.MULTILINE))
    assert ids == REQUIREMENT_IDS + ("UAT-01", "PROD-01")


def test_complete_candidate_bound_acceptance_passes(tmp_path):
    manifest = candidate(tmp_path)
    record = accepted_record(manifest)
    assert validate_record(record, manifest, require_acceptance=True)["decision"] == "ACCEPTED"


@pytest.mark.parametrize("mutation,message", [
    (lambda r: r["candidate"].update(apk_sha256="c" * 64), "candidate"),
    (lambda r: r["requirements"].pop(), "coverage"),
    (lambda r: r["requirements"][0].update(result="NOT_TESTABLE"), "AUTH-01"),
    (lambda r: r["requirements"][0].update(evidence=""), "AUTH-01"),
    (lambda r: r["issues"].append({
        "id": "UAT-1", "requirement_ids": ["AUTH-01"], "steps": "Register", "expected": "Account created",
        "actual": "Request failed", "impact": "blocking", "evidence": "redacted screenshot", "fix_commit": "",
        "retest": "", "status": "OPEN",
    }), "unresolved"),
    (lambda r: r["tester"].update(tested_at="2026-09-05"), "timezone"),
])
def test_incomplete_or_mismatched_acceptance_fails_closed(tmp_path, mutation, message):
    manifest = candidate(tmp_path)
    record = accepted_record(manifest)
    mutation(record)
    with pytest.raises(UatRecordError, match=message):
        validate_record(record, manifest, require_acceptance=True)


def test_scope_change_requires_explicit_approval(tmp_path):
    manifest = candidate(tmp_path)
    record = accepted_record(manifest)
    record["requirements"][1].update(result="SCOPE_ACCEPTED", scope_approval="")
    with pytest.raises(UatRecordError, match="explicit approval"):
        validate_record(record, manifest)
    record["requirements"][1]["scope_approval"] = "Product owner approved disabled Google login for this release."
    assert validate_record(record, manifest)["decision"] == "ACCEPTED"
