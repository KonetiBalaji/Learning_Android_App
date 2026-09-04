from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def test_production_compose_keeps_api_private_and_requires_external_state_and_secrets():
    compose_text = (ROOT / "deploy" / "compose.production.yml").read_text(encoding="utf-8")
    compose = yaml.safe_load(compose_text)
    api = compose["services"]["api"]
    proxy = compose["services"]["proxy"]

    assert api["read_only"] is True and "ports" not in api and api["expose"] == ["8000"]
    assert api["volumes"] == ["runtime:/runtime"]
    assert compose["volumes"]["runtime"]["external"] is True
    assert api["environment"]["LEARNING_ENVIRONMENT"] == "production"
    for required in ("LEARNING_API_IMAGE", "LEARNING_RELEASE_REVISION", "LEARNING_JWT_SECRET",
                     "OPENAI_API_KEY", "LEARNING_RUNTIME_VOLUME", "LEARNING_TLS_DIR"):
        assert f"${{{required}:?" in compose_text
    assert proxy["read_only"] is True and proxy["security_opt"] == ["no-new-privileges:true"]
    assert proxy["depends_on"]["api"]["condition"] == "service_healthy"


def test_tls_proxy_has_bounded_ingress_and_does_not_trust_forwarded_client_identity():
    nginx = (ROOT / "deploy" / "nginx.conf").read_text(encoding="utf-8")
    for directive in (
        "listen 443 ssl;", "ssl_protocols TLSv1.2 TLSv1.3;",
        "client_max_body_size 51456k;", "client_body_timeout 30s;",
        "client_header_timeout 15s;", "proxy_connect_timeout 5s;",
        "proxy_send_timeout 60s;", "proxy_read_timeout 180s;",
        "limit_req zone=api_per_ip burst=60 nodelay;", "proxy_request_buffering off;",
        "proxy_set_header X-Forwarded-For $remote_addr;",
    ):
        assert directive in nginx
    assert "$http_x_forwarded_for" not in nginx
