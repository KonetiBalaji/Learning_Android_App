"""Bounded concurrent smoke for a deployed production-shaped API.

This is a correctness gate under modest contention, not a capacity benchmark.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import math
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import uuid


def request_json(base_url: str, path: str, *, method: str = 'GET', token: str | None = None,
                 body: dict | None = None, timeout: float = 15) -> tuple[int, dict, float]:
    encoded = json.dumps(body).encode() if body is not None else None
    headers = {'Accept': 'application/json'}
    if body is not None:
        headers['Content-Type'] = 'application/json'
    if token:
        headers['Authorization'] = f'Bearer {token}'
    started = time.perf_counter()
    try:
        with urlopen(Request(base_url + path, data=encoded, headers=headers, method=method),
                     timeout=timeout) as response:
            payload = json.loads(response.read())
            return response.status, payload, time.perf_counter() - started
    except HTTPError as error:
        body_text = error.read(2048).decode('utf-8', errors='replace')
        raise RuntimeError(f'{method} {path} returned HTTP {error.code}: {body_text}') from error
    except (URLError, TimeoutError) as error:
        raise RuntimeError(f'{method} {path} transport failure: {type(error).__name__}') from error


def percentile(values: list[float], percent: int) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * percent / 100) - 1)]


def run(base_url: str, requests: int, concurrency: int) -> dict:
    if not 20 <= requests <= 5000 or not 2 <= concurrency <= 100 or concurrency > requests:
        raise ValueError('Use 20-5000 requests and 2-100 workers, with workers no greater than requests')
    email = f'container-load-{uuid.uuid4().hex}@example.com'
    status, registration, _ = request_json(base_url, '/v1/auth/register', method='POST',
        body={'email': email, 'password': 'load-smoke-password-long-enough'})
    if status != 201 or not isinstance(registration.get('access_token'), str):
        raise RuntimeError('Registration response did not contain a token')
    token = registration['access_token']
    operations = (
        ('GET', '/ready', None),
        ('GET', '/v1/account', None),
        ('GET', '/v1/catalog?grade=8', None),
        ('GET', '/v1/progress/dashboard?grade=8', None),
        ('GET', '/v1/progress/weekly-report?grade=8', None),
        ('GET', '/v1/privacy/retention', None),
        ('PUT', '/v1/account/interests', {'interests': ['nature', 'space']}),
    )

    def one(index: int) -> float:
        method, path, body = operations[index % len(operations)]
        code, payload, elapsed = request_json(base_url, path, method=method,
            token=None if path == '/ready' else token, body=body)
        if code != 200 or not isinstance(payload, dict):
            raise RuntimeError(f'{method} {path} returned an invalid success response')
        if path == '/ready' and payload.get('status') != 'ready':
            raise RuntimeError('Readiness changed during load')
        if path == '/v1/account' and payload.get('email') != email:
            raise RuntimeError('Authenticated account identity changed during load')
        if path.startswith('/v1/catalog') and payload.get('grade') != 8:
            raise RuntimeError('Catalog response changed grade during load')
        return elapsed

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(one, index) for index in range(requests)]
        latencies = [future.result() for future in as_completed(futures)]
    duration = time.perf_counter() - started
    code, profile, final_elapsed = request_json(base_url, '/v1/account', token=token)
    if code != 200 or profile.get('email') != email or profile.get('interests') != ['nature', 'space']:
        raise RuntimeError('Account state was inconsistent after concurrent traffic')
    latencies.append(final_elapsed)
    return {
        'requests': requests + 1,
        'concurrency': concurrency,
        'failures': 0,
        'duration_seconds': round(duration, 3),
        'requests_per_second': round(requests / duration, 2),
        'p50_ms': round(percentile(latencies, 50) * 1000, 2),
        'p95_ms': round(percentile(latencies, 95) * 1000, 2),
        'max_ms': round(max(latencies) * 1000, 2),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base_url')
    parser.add_argument('--requests', type=int, default=700)
    parser.add_argument('--concurrency', type=int, default=20)
    args = parser.parse_args()
    base_url = args.base_url.rstrip('/')
    if not base_url.startswith(('http://127.0.0.1:', 'https://')):
        parser.error('Use an HTTPS deployment or an explicit localhost test endpoint')
    result = run(base_url, args.requests, args.concurrency)
    print('Production-shaped concurrent smoke passed:', json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
