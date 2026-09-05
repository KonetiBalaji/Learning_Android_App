import io
import json
import subprocess
import sys
from contextlib import contextmanager

import pytest

from app.deployment_probe import probe
from app.release_candidate import CandidateVerificationError


REVISION = "a" * 40


def opener(health, readiness):
    @contextmanager
    def open_response(request, timeout):
        assert request.full_url in {"https://learn.example.org/health", "https://learn.example.org/ready"}
        payload = health if request.full_url.endswith("/health") else readiness
        response = io.BytesIO(json.dumps(payload).encode())
        response.status = 200
        yield response
    return open_response


def payloads(environment="production", revision=REVISION):
    return (
        {"status": "ok", "environment": environment, "revision": revision,
         "ai_provider": "openai" if environment == "production" else "deterministic",
         "model": "gpt-5-mini" if environment == "production" else "none"},
        {"status": "ready", "environment": environment, "revision": revision,
         "checks": ["database", "upload_storage"]},
    )


def test_production_probe_binds_identity_provider_storage_and_latency():
    health, ready = payloads()
    times = iter((10.0, 10.125))
    result = probe("https://learn.example.org", REVISION, "production",
                   opener=opener(health, ready), clock=lambda: next(times))
    assert result == {
        "ready": True, "environment": "production", "revision": REVISION,
        "provider": "openai", "model": "gpt-5-mini",
        "checks": ["database", "upload_storage"], "latency_ms": 125,
    }


@pytest.mark.parametrize("url", ["http://learn.example.org", "https://localhost", "https://qa.invalid"])
def test_probe_rejects_insecure_local_or_placeholder_origin(url):
    with pytest.raises(CandidateVerificationError, match="URL"):
        probe(url, REVISION, "production")


def test_probe_fails_when_total_readiness_exceeds_budget():
    health, ready = payloads("staging")
    times = iter((1.0, 7.0))
    with pytest.raises(CandidateVerificationError, match="latency"):
        probe("https://learn.example.org", REVISION, "staging", max_latency_ms=5000,
              opener=opener(health, ready), clock=lambda: next(times))


@pytest.mark.parametrize("timeout,latency", [(0, 5000), (121, 5000), (10, 99), (10, 120001)])
def test_probe_rejects_unsafe_time_bounds(timeout, latency):
    with pytest.raises(CandidateVerificationError, match="timeout|Latency"):
        probe("https://learn.example.org", REVISION, "staging",
              timeout=timeout, max_latency_ms=latency)


def test_cli_failure_is_concise_and_does_not_echo_sensitive_url():
    result = subprocess.run([
        sys.executable, "-m", "app.deployment_probe", "--backend-url",
        "https://user:secret@learn.example.org", "--revision", REVISION,
        "--environment", "production",
    ], capture_output=True, text=True)
    assert result.returncode == 2 and result.stdout == ""
    assert "secret" not in result.stderr and "Traceback" not in result.stderr
