"""Exercise the deployed staging API using a verified TLS connection."""
import argparse
import http.client
import json
import secrets
import ssl
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--ca-file")
parser.add_argument("--host", default="localhost")
args = parser.parse_args()
context = ssl.create_default_context(cafile=args.ca_file)
host = args.host


def call(path, method="GET", body=None, token=None, expected=200, content_type="application/json"):
    headers = {"Content-Type": content_type}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = json.dumps(body).encode() if isinstance(body, dict) else body
    request = Request(f"https://{host}{path}", data=payload, headers=headers, method=method)
    try:
        response = urlopen(request, context=context, timeout=45)
    except HTTPError as error:
        response = error
    with response:
        if response.status != expected:
            raise AssertionError(f"{method} {path}: expected {expected}, received {response.status}")
        raw = response.read()
    return json.loads(raw) if raw else None


redirect = http.client.HTTPConnection(host, timeout=5)
try:
    redirect.request("GET", "/health")
    response = redirect.getresponse()
    assert response.status == 308
    assert response.getheader("Location") == f"https://{host}/health"
finally:
    redirect.close()

assert call("/health")["generation_mode"] == "local_practice"
assert call("/ready")["status"] == "ready"
tokens = []
try:
    for _ in range(2):
        tokens.append(call("/auth/register", "POST", {
            "username": "staging-" + secrets.token_hex(5),
            "password": secrets.token_urlsafe(24),
        })["token"])
    owner, outsider = tokens
    sample = (Path(__file__).resolve().parents[1] / "shared/sample-study-material.txt").read_bytes()
    boundary = secrets.token_hex(16)
    multipart = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="sample.txt"\r\n'
        'Content-Type: text/plain\r\n\r\n'
    ).encode() + sample + f"\r\n--{boundary}--\r\n".encode()
    document = call("/documents", "POST", multipart, owner, 201, f"multipart/form-data; boundary={boundary}")
    root = f'/documents/{document["id"]}'
    call(root + "/offline-bundle", token=outsider, expected=404)
    quiz = call(root + "/quizzes", "POST", {"count": 1}, owner, 201)
    assert quiz["mode"] == "local_practice"
    assert call("/documents", token=owner)[0]["id"] == document["id"]
    call(root, "DELETE", token=owner, expected=204)
    call(root + "/offline-bundle", token=owner, expected=404)
    call(f'/quizzes/{quiz["id"]}', token=owner, expected=404)
finally:
    for token in tokens:
        call("/account", "DELETE", token=token, expected=204)

print("Verified HTTPS redirect, trusted TLS, readiness, upload, owner isolation, quiz generation and deletion.")
