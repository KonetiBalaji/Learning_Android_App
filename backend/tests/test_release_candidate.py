import hashlib
import io
import json
import subprocess
import sys
from contextlib import contextmanager

import pytest

from app.release_candidate import CandidateVerificationError, load_and_verify_artifact, verify_health


REVISION = "a" * 40


def candidate(tmp_path, **changes):
    apk = tmp_path / "learn-smart-private-release.apk"
    apk.write_bytes(b"signed-apk-fixture")
    manifest = {
        "product": "Learn Smart AI", "distribution": "private APK", "git_commit": REVISION,
        "version_name": "1.0", "version_code": 1, "backend_url": "https://learn.example.org",
        "apk_file": apk.name, "apk_sha256": hashlib.sha256(apk.read_bytes()).hexdigest(),
        "signing_certificate_sha256": "b" * 64, "built_at_utc": "2026-09-04T00:00:00Z",
        "production_verified": False, "uat_accepted": False,
    }
    manifest.update(changes)
    path = tmp_path / "candidate-manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def opener(payload, status=200):
    @contextmanager
    def open_response(request, timeout):
        assert request.full_url == "https://learn.example.org/health" and timeout > 0
        response = io.BytesIO(json.dumps(payload).encode())
        response.status = status
        yield response
    return open_response


def health(**changes):
    result = {"status": "ok", "environment": "staging", "revision": REVISION,
              "ai_provider": "deterministic", "model": "none"}
    result.update(changes)
    return result


def test_candidate_artifact_and_staging_identity_are_verified(tmp_path):
    manifest = load_and_verify_artifact(candidate(tmp_path))
    assert verify_health(manifest, "staging", opener=opener(health()))["revision"] == REVISION


@pytest.mark.parametrize("url", [
    "http://learn.example.org", "https://localhost", "https://10.0.2.2",
    "https://qa.invalid", "https://learn.example.org/path", "https://learn.example.org?token=x",
])
def test_local_placeholder_or_non_origin_backend_is_rejected(tmp_path, url):
    with pytest.raises(CandidateVerificationError, match="URL"):
        load_and_verify_artifact(candidate(tmp_path, backend_url=url))


def test_modified_apk_is_rejected(tmp_path):
    path = candidate(tmp_path)
    (tmp_path / "learn-smart-private-release.apk").write_bytes(b"modified")
    with pytest.raises(CandidateVerificationError, match="does not match"):
        load_and_verify_artifact(path)


@pytest.mark.parametrize("changes,message", [
    ({"revision": "c" * 40}, "revision"),
    ({"environment": "production"}, "environment"),
    ({"unexpected": "field"}, "identity"),
])
def test_wrong_backend_identity_is_rejected(tmp_path, changes, message):
    manifest = load_and_verify_artifact(candidate(tmp_path))
    with pytest.raises(CandidateVerificationError, match=message):
        verify_health(manifest, "staging", opener=opener(health(**changes)))


def test_production_requires_openai_provider_and_model(tmp_path):
    manifest = load_and_verify_artifact(candidate(tmp_path))
    with pytest.raises(CandidateVerificationError, match="provider"):
        verify_health(manifest, "production", opener=opener(health(environment="production")))
    verified = verify_health(manifest, "production", opener=opener(
        health(environment="production", ai_provider="openai", model="gpt-5-mini")))
    assert verified["model"] == "gpt-5-mini"


def test_cli_failure_is_concise_and_has_no_traceback(tmp_path):
    result = subprocess.run([
        sys.executable, "-m", "app.release_candidate", str(tmp_path / "missing.json"),
        "--expected-environment", "staging",
    ], capture_output=True, text=True)
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr == "Candidate verification failed: Candidate manifest is unreadable\n"
