"""Independently verify a private-APK candidate against its deployed backend."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit


HEX_64 = re.compile(r"^[0-9a-f]{64}$")
GIT_REVISION = re.compile(r"^[0-9a-f]{40}$")
REQUIRED_MANIFEST_FIELDS = {
    "product", "distribution", "git_commit", "version_name", "version_code",
    "backend_url", "apk_file", "apk_sha256", "signing_certificate_sha256",
    "built_at_utc", "production_verified", "uat_accepted",
}


class CandidateVerificationError(ValueError):
    """The candidate cannot be tied safely to the expected deployment."""


def _public_https_url(value: object) -> str:
    if not isinstance(value, str):
        raise CandidateVerificationError("Candidate backend URL is missing")
    parsed = urlsplit(value)
    host = (parsed.hostname or "").lower()
    if (parsed.scheme != "https" or not host or parsed.username or parsed.password
            or parsed.query or parsed.fragment or parsed.path not in ("", "/")):
        raise CandidateVerificationError("Candidate backend URL must be an HTTPS service origin")
    if (host in {"localhost", "127.0.0.1", "10.0.2.2"} or host.endswith(".invalid")
            or host.endswith(".example") or host.endswith(".test")):
        raise CandidateVerificationError("Candidate backend URL is local or a placeholder")
    return value.rstrip("/")


def load_and_verify_artifact(manifest_path: Path) -> dict[str, object]:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CandidateVerificationError("Candidate manifest is unreadable") from exc
    if not isinstance(manifest, dict) or set(manifest) != REQUIRED_MANIFEST_FIELDS:
        raise CandidateVerificationError("Candidate manifest fields are incomplete or unexpected")
    if manifest["product"] != "Learn Smart AI" or manifest["distribution"] != "private APK":
        raise CandidateVerificationError("Candidate product identity is invalid")
    if not isinstance(manifest["git_commit"], str) or not GIT_REVISION.fullmatch(manifest["git_commit"]):
        raise CandidateVerificationError("Candidate Git revision is invalid")
    if not isinstance(manifest["version_name"], str) or not manifest["version_name"].strip():
        raise CandidateVerificationError("Candidate version name is invalid")
    if type(manifest["version_code"]) is not int or manifest["version_code"] < 1:
        raise CandidateVerificationError("Candidate version code is invalid")
    _public_https_url(manifest["backend_url"])
    for field in ("apk_sha256", "signing_certificate_sha256"):
        if not isinstance(manifest[field], str) or not HEX_64.fullmatch(manifest[field]):
            raise CandidateVerificationError(f"Candidate {field} is invalid")
    if type(manifest["uat_accepted"]) is not bool or type(manifest["production_verified"]) is not bool:
        raise CandidateVerificationError("Candidate acceptance flags are invalid")
    apk_name = manifest["apk_file"]
    if not isinstance(apk_name, str) or Path(apk_name).name != apk_name or not apk_name.endswith(".apk"):
        raise CandidateVerificationError("Candidate APK filename is invalid")
    apk_path = manifest_path.resolve().parent / apk_name
    try:
        digest = hashlib.sha256(apk_path.read_bytes()).hexdigest()
    except OSError as exc:
        raise CandidateVerificationError("Candidate APK is missing or unreadable") from exc
    if digest != manifest["apk_sha256"]:
        raise CandidateVerificationError("Candidate APK SHA-256 does not match the manifest")
    return manifest


def verify_health(manifest: dict[str, object], expected_environment: str,
                  *, timeout: float = 10.0, opener=urllib.request.urlopen) -> dict[str, str]:
    if expected_environment not in {"staging", "production"}:
        raise CandidateVerificationError("Expected environment must be staging or production")
    url = _public_https_url(manifest["backend_url"]) + "/health"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with opener(request, timeout=timeout) as response:
            if response.status != 200:
                raise CandidateVerificationError(f"Backend health returned HTTP {response.status}")
            payload = response.read(65537)
            if len(payload) > 65536:
                raise CandidateVerificationError("Backend health response is unexpectedly large")
            health = json.loads(payload)
    except CandidateVerificationError:
        raise
    except (OSError, urllib.error.URLError, UnicodeError, json.JSONDecodeError) as exc:
        raise CandidateVerificationError("Backend health could not be verified") from exc
    expected_fields = {"status", "environment", "revision", "ai_provider", "model"}
    if not isinstance(health, dict) or set(health) != expected_fields:
        raise CandidateVerificationError("Backend health identity is incomplete or unexpected")
    if health["status"] != "ok" or health["environment"] != expected_environment:
        raise CandidateVerificationError("Backend health or environment does not match the candidate")
    if health["revision"] != manifest["git_commit"]:
        raise CandidateVerificationError("Backend revision does not match the APK candidate")
    if expected_environment == "production" and (health["ai_provider"] != "openai" or health["model"] == "none"):
        raise CandidateVerificationError("Production backend is not using the reviewed AI provider")
    return health


def verify_readiness(manifest: dict[str, object], expected_environment: str,
                     *, timeout: float = 10.0, opener=urllib.request.urlopen) -> dict[str, object]:
    url = _public_https_url(manifest['backend_url']) + '/ready'
    request = urllib.request.Request(url, headers={'Accept': 'application/json'})
    try:
        with opener(request, timeout=timeout) as response:
            if response.status != 200:
                raise CandidateVerificationError(f'Backend readiness returned HTTP {response.status}')
            payload = response.read(65537)
            if len(payload) > 65536:
                raise CandidateVerificationError('Backend readiness response is unexpectedly large')
            readiness = json.loads(payload)
    except CandidateVerificationError:
        raise
    except (OSError, urllib.error.URLError, UnicodeError, json.JSONDecodeError) as exc:
        raise CandidateVerificationError('Backend readiness could not be verified') from exc
    expected = {'status', 'environment', 'revision', 'checks'}
    if not isinstance(readiness, dict) or set(readiness) != expected:
        raise CandidateVerificationError('Backend readiness identity is incomplete or unexpected')
    if (readiness['status'] != 'ready' or readiness['environment'] != expected_environment
            or readiness['revision'] != manifest['git_commit']
            or readiness['checks'] != ['database', 'upload_storage']):
        raise CandidateVerificationError('Backend runtime is not ready for this candidate')
    return readiness


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--expected-environment", choices=("staging", "production"), required=True)
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()
    try:
        manifest = load_and_verify_artifact(args.manifest)
        health = verify_health(manifest, args.expected_environment, timeout=args.timeout)
        readiness = verify_readiness(manifest, args.expected_environment, timeout=args.timeout)
    except CandidateVerificationError as exc:
        parser.exit(2, f"Candidate verification failed: {exc}\n")
    print(json.dumps({
        "verified": True, "environment": health["environment"], "revision": health["revision"],
        "apk_sha256": manifest["apk_sha256"],
        "signing_certificate_sha256": manifest["signing_certificate_sha256"],
        "runtime_checks": readiness["checks"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
