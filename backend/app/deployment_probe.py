"""Privacy-safe deployment identity/readiness probe for schedulers and alerts."""

from __future__ import annotations

import argparse
import json
import re
import time

from .release_candidate import CandidateVerificationError, _public_https_url, verify_health, verify_readiness


REVISION = re.compile(r"^[0-9a-f]{40}$")


def probe(backend_url: str, revision: str, environment: str, *, timeout: float = 10.0,
          max_latency_ms: int = 5000, opener=None, clock=time.monotonic) -> dict[str, object]:
    if not REVISION.fullmatch(revision):
        raise CandidateVerificationError("Expected deployment revision is invalid")
    if environment not in {"staging", "production"}:
        raise CandidateVerificationError("Expected environment must be staging or production")
    if not 0.1 <= timeout <= 120:
        raise CandidateVerificationError("Probe timeout must be between 0.1 and 120 seconds")
    if not 100 <= max_latency_ms <= 120_000:
        raise CandidateVerificationError("Latency ceiling must be between 100 and 120000 milliseconds")
    origin = _public_https_url(backend_url)
    identity = {"backend_url": origin, "git_commit": revision}
    kwargs = {"timeout": timeout}
    if opener is not None:
        kwargs["opener"] = opener
    started = clock()
    health = verify_health(identity, environment, **kwargs)
    readiness = verify_readiness(identity, environment, **kwargs)
    elapsed_ms = round((clock() - started) * 1000)
    if elapsed_ms > max_latency_ms:
        raise CandidateVerificationError("Deployment readiness exceeded the configured latency ceiling")
    return {
        "ready": True, "environment": health["environment"], "revision": health["revision"],
        "provider": health["ai_provider"], "model": health["model"],
        "checks": readiness["checks"], "latency_ms": elapsed_ms,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-url", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--environment", choices=("staging", "production"), required=True)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--max-latency-ms", type=int, default=5000)
    args = parser.parse_args()
    try:
        result = probe(args.backend_url, args.revision, args.environment,
                       timeout=args.timeout, max_latency_ms=args.max_latency_ms)
    except CandidateVerificationError as exc:
        parser.exit(2, f"Deployment probe failed: {exc}\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
