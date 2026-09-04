from threading import Lock

import pytest

from scripts import production_load_smoke


def test_percentile_uses_nearest_rank_without_underreporting_tail():
    values = [0.01, 0.02, 0.03, 0.04, 0.50]
    assert production_load_smoke.percentile(values, 50) == 0.03
    assert production_load_smoke.percentile(values, 95) == 0.50


@pytest.mark.parametrize(("requests", "concurrency"), [
    (19, 2), (5001, 2), (20, 1), (20, 101), (20, 21),
])
def test_load_shape_is_bounded_before_any_network_request(requests, concurrency):
    with pytest.raises(ValueError, match="20-5000 requests"):
        production_load_smoke.run(["http://127.0.0.1:1"], requests, concurrency)


def test_load_smoke_routes_traffic_and_checks_state_across_instances(monkeypatch):
    base_urls = ["http://127.0.0.1:8101", "http://127.0.0.1:8102"]
    expected_email = "container-load-00000000000000000000000000000000@example.com"
    observed = []
    lock = Lock()

    def request_json(base_url, path, *, method="GET", token=None, body=None, timeout=15):
        del method, body, timeout
        with lock:
            observed.append((base_url, path, token))
        if path == "/v1/auth/register":
            return 201, {"access_token": "shared-token"}, 0.001
        if path == "/ready":
            return 200, {"status": "ready"}, 0.001
        if path == "/v1/account":
            return 200, {
                "email": expected_email,
                "interests": ["nature", "space"],
            }, 0.001
        if path.startswith("/v1/catalog"):
            return 200, {"grade": 8}, 0.001
        return 200, {}, 0.001

    monkeypatch.setattr(production_load_smoke.uuid, "uuid4",
                        lambda: type("Uuid", (), {"hex": "0" * 32})())
    monkeypatch.setattr(production_load_smoke, "request_json", request_json)

    result = production_load_smoke.run(base_urls, requests=28, concurrency=4)

    assert result["instances"] == 2 and result["requests"] == 30
    traffic = observed[1:-2]
    assert {url for url, _, _ in traffic} == set(base_urls)
    assert observed[-2][0] == base_urls[0] and observed[-1][0] == base_urls[1]
