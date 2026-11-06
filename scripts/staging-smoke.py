"""Exercise the deployed staging API using a verified TLS connection."""
import argparse
import http.client
import json
import secrets
import ssl
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--ca-file")
parser.add_argument("--host", default="localhost")
parser.add_argument("--scan", type=Path)
parser.add_argument("--check-google-deletion", action="store_true")
args = parser.parse_args()
context = ssl.create_default_context(cafile=args.ca_file)
host = args.host


def call(path, method="GET", body=None, token=None, expected=200, content_type="application/json"):
    headers = {"Content-Type": content_type}
    if path in ("/delete-account", "/delete-account/google") and method == "POST":
        headers["Origin"] = f"https://{host}"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = json.dumps(body).encode() if isinstance(body, dict) else body
    request = Request(f"https://{host}{path}", data=payload, headers=headers, method=method)
    try:
        response = urlopen(request, context=context, timeout=120)
    except HTTPError as error:
        response = error
    with response:
        if response.status != expected:
            raise AssertionError(f"{method} {path}: expected {expected}, received {response.status}")
        raw = response.read()
        if response.headers.get_content_type() == "text/html":
            return raw.decode("utf-8")
    return json.loads(raw) if raw else None


def upload(name, content, content_type, token):
    boundary = secrets.token_hex(16)
    multipart = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\n'
        f'Content-Type: {content_type}\r\n\r\n'
    ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
    return call("/documents", "POST", multipart, token, 201, f"multipart/form-data; boundary={boundary}")


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
credentials = []
try:
    for _ in range(2):
        credentials.append({
            "username": "staging-" + secrets.token_hex(5),
            "password": secrets.token_urlsafe(24),
        })
        tokens.append(call("/auth/register", "POST", credentials[-1])["token"])
    owner, outsider = tokens
    catalog = call("/curriculum", token=owner)
    assert {chapter["subject"] for chapter in catalog if chapter["grade"] == 6} == {
        "Mathematics", "Science", "English", "Social Studies",
    }
    fractions = "/curriculum/fractions/lesson"
    decimals = "/curriculum/decimals/lesson"
    call(decimals, "POST", token=owner, expected=409)
    lesson = call(fractions, "POST", token=owner)
    for action, fields, expected_phase in (
        ("diagnostic", {"choice": 0}, "coach"),
        ("continue", {}, "practice"),
        ("practice", {"response": "3/4"}, "rewrite"),
        ("rewrite", {"response": "Add the numerators and keep the denominator unchanged."}, "mastered"),
    ):
        lesson = call(fractions + "/actions", "POST",
                      {"version": lesson["version"], "action": action, **fields}, owner)
        assert lesson["phase"] == expected_phase
        if expected_phase == "coach":
            assert "You chose 1/2." in lesson["feedback"]
            assert {"Soccer", "Gaming"} <= lesson["example_variants"].keys()
    assert lesson["diagnostic_score"] == {"correct": 0, "total": 1}
    assert call(decimals, "POST", token=owner)["phase"] == "diagnostic"
    call(decimals, "POST", token=outsider, expected=409)
    print("Verified curriculum coaching, mastery, diagnostic scoring and owner-only chapter unlock.")
    sample = (Path(__file__).resolve().parents[1] / "shared/sample-study-material.txt").read_bytes()
    document = upload("sample.txt", sample, "text/plain", owner)
    root = f'/documents/{document["id"]}'
    call(root + "/offline-bundle", token=outsider, expected=404)
    quiz = call(root + "/quizzes", "POST", {"count": 1}, owner, 201)
    assert quiz["mode"] == "local_practice"
    assert call("/documents", token=owner)[0]["id"] == document["id"]
    hits = call(root + "/search", "POST", {"query": "cell power factory"}, owner)["hits"]
    assert hits and "mitochondria" in hits[0]["quote"].lower()
    if args.scan:
        scan = upload("sample-scan.pdf", args.scan.read_bytes(), "application/pdf", owner)
        scan_root = f'/documents/{scan["id"]}'
        page = call(scan_root + "/ocr-pages/1", token=owner)
        assert "mitochondria" in page["text"].lower() and "ribosomes" in page["text"].lower()
        assert page["image_base64"]
        assert call(scan_root + "/ocr-pages/1/review", "POST", {"text": page["text"]}, owner)["processing_state"] == "ready"
        print("Verified real OCR and confirmed a scanned PDF page.")
    call(root, "DELETE", token=owner, expected=204)
    call(root + "/offline-bundle", token=owner, expected=404)
    call(f'/quizzes/{quiz["id"]}', token=owner, expected=404)
    deletion_page = call("/delete-account")
    assert "Delete your Saras account" in deletion_page
    if args.check_google_deletion:
        assert 'href="/delete-account/google"' in deletion_page
        google_page = call("/delete-account/google")
        assert 'https://accounts.google.com/gsi/client' in google_page
        assert 'data-nonce="' in google_page
        call("/delete-account/google", "POST", b"", expected=400,
             content_type="application/x-www-form-urlencoded")
        print("Verified Google deletion page wiring and rejection without confirmation. No Google session was requested.")
    form = urlencode({**credentials[0], "confirm": "yes"}).encode()
    assert "were deleted" in call("/delete-account", "POST", form, content_type="application/x-www-form-urlencoded")
    tokens.remove(owner)
    call("/account", token=owner, expected=401)
finally:
    for token in tokens:
        call("/account", "DELETE", token=token, expected=204)

print("Verified HTTPS redirect, trusted TLS, readiness, upload, semantic retrieval, owner isolation, quiz generation and web account deletion.")
