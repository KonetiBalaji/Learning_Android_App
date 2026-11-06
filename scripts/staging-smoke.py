"""Exercise the deployed staging API using a verified TLS connection."""
import argparse
import http.client
import json
import os
import secrets
import ssl
import subprocess
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--ca-file")
parser.add_argument("--host", default="localhost")
parser.add_argument("--scan", type=Path)
parser.add_argument("--check-google-deletion", action="store_true")
parser.add_argument("--recreate-disposable-api", action="store_true",
                    help="Replace the API container in the local disposable Compose stack during the test.")
args = parser.parse_args()
context = ssl.create_default_context(cafile=args.ca_file)
host = args.host


def call(path, method="GET", body=None, token=None, expected=200, content_type="application/json", *, origin=None):
    headers = {"Content-Type": content_type}
    if path in ("/delete-account", "/delete-account/google") and method == "POST":
        headers["Origin"] = origin if origin is not None else f"https://{host}"
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


def verify_disposable_restore(owner, outsider, document_id, quiz_id, readiness_result, credentials):
    compose = ["docker", "compose"]
    snapshot = subprocess.check_output(compose + ["exec", "-T", "api", "python", "-c", """
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

with TemporaryDirectory() as directory:
    target = Path(directory) / "backup.sqlite3"
    with closing(sqlite3.connect("file:/data/study.sqlite3?mode=ro", uri=True)) as source:
        with closing(sqlite3.connect(target)) as backup:
            source.backup(backup)
    sys.stdout.buffer.write(target.read_bytes())
"""])
    image = subprocess.check_output(compose + ["images", "-q", "api"], text=True).strip()
    key = Path(os.environ["STUDY_STORAGE_KEY_PATH"]).resolve(strict=True)
    fixture = json.dumps([owner, outsider, document_id, quiz_id, readiness_result, credentials]).encode()
    subprocess.run(
        ["docker", "run", "--rm", "-i", "--network", "none", "--mount", "type=volume,target=/data",
         "--mount", f"type=bind,source={key},target=/run/secrets/storage_key,readonly",
         "-e", "STUDY_STORAGE_KEY_FILE=/run/secrets/storage_key", "-e", "STUDY_GENERATION_MODE=local_practice",
         image, "python", "-c", """
import json
import os
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from study.api import create_app

owner, outsider, document_id, quiz_id, expected, credentials = json.loads(sys.stdin.buffer.readline())
with Path("/data/study.sqlite3").open("xb") as database:
    database.write(sys.stdin.buffer.read())
with closing(sqlite3.connect("/data/study.sqlite3")) as database:
    assert database.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
    assert database.execute("PRAGMA foreign_key_check").fetchall() == []
original_key = os.environ["STUDY_STORAGE_KEY_FILE"]
with TemporaryDirectory() as directory:
    wrong_key = Path(directory) / "wrong.key"
    wrong_key.write_bytes(Fernet.generate_key())
    os.environ["STUDY_STORAGE_KEY_FILE"] = str(wrong_key)
    try:
        create_app()
    except RuntimeError as error:
        assert str(error) == "The storage key does not match this database."
    else:
        raise AssertionError("Restored database opened with the wrong key.")
    finally:
        os.environ["STUDY_STORAGE_KEY_FILE"] = original_key
with TestClient(create_app()) as client:
    headers = {"Authorization": f"Bearer {owner}"}
    documents = client.get("/documents", headers=headers)
    assert documents.status_code == 200 and documents.json()[0]["id"] == document_id
    assert client.get(f"/quizzes/{quiz_id}", headers=headers).status_code == 200
    attempt = client.post("/curriculum/readiness/grade6-math", headers=headers)
    assert attempt.status_code == 200 and attempt.json() == expected
    login = client.post("/auth/login", json=credentials)
    assert login.status_code == 200
    fresh_headers = {"Authorization": "Bearer " + login.json()["token"]}
    fresh_documents = client.get("/documents", headers=fresh_headers)
    assert fresh_documents.status_code == 200 and fresh_documents.json() == documents.json()
    outsider_headers = {"Authorization": f"Bearer {outsider}"}
    assert client.get(f"/documents/{document_id}/offline-bundle", headers=outsider_headers).status_code == 404
"""],
        input=fixture + b"\n" + snapshot, check=True,
    )
    print("Verified SQLite backup recovery, fresh sign-in, and rejection of an incorrect mounted key.")


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
    unfinished_readiness = "/curriculum/readiness"
    readiness = unfinished_readiness + "/grade6-math"
    call(decimals, "POST", token=owner, expected=409)
    call(readiness, "POST", token=owner, expected=409)
    assert call(unfinished_readiness, token=owner) == []
    lesson = call(fractions, "POST", token=owner)
    for action, fields, expected_phase in (
        ("diagnostic", {"choice": 0}, "coach"),
        ("continue", {}, "diagnostic"),
        ("diagnostic", {"choice": 2}, "practice"),
        ("practice", {"response": "3/4"}, "rewrite"),
        ("rewrite", {"response": "Add the numerators and keep the denominator unchanged."}, "mastered"),
    ):
        lesson = call(fractions + "/actions", "POST",
                      {"version": lesson["version"], "action": action, **fields}, owner)
        assert lesson["phase"] == expected_phase
        if expected_phase == "coach":
            assert "You chose 1/2." in lesson["feedback"]
            assert {"Soccer", "Gaming"} <= lesson["example_variants"].keys()
    assert lesson["diagnostic_score"] == {"correct": 1, "total": 2}
    lesson = call(decimals, "POST", token=owner)
    assert lesson["phase"] == "diagnostic"
    call(decimals, "POST", token=outsider, expected=409)
    print("Verified curriculum coaching, mastery, diagnostic scoring and owner-only chapter unlock.")
    for action, fields, expected_phase in (
        ("diagnostic", {"choice": 0}, "diagnostic"),
        ("diagnostic", {"choice": 1}, "practice"),
        ("practice", {"response": "0.68"}, "rewrite"),
        ("rewrite", {"response": "Align the decimal points to add matching place values."}, "mastered"),
    ):
        lesson = call(decimals + "/actions", "POST",
                      {"version": lesson["version"], "action": action, **fields}, owner)
        assert lesson["phase"] == expected_phase
    sample = (Path(__file__).resolve().parents[1] / "shared/sample-study-material.txt").read_bytes()
    document = upload("sample.txt", sample, "text/plain", owner)
    root = f'/documents/{document["id"]}'
    call(root + "/offline-bundle", token=outsider, expected=404)
    quiz = call(root + "/quizzes", "POST", {"count": 1}, owner, 201)
    assert quiz["mode"] == "local_practice"
    assert call("/documents", token=owner)[0]["id"] == document["id"]
    hits = call(root + "/search", "POST", {"query": "cell power factory"}, owner)["hits"]
    assert hits and "mitochondria" in hits[0]["quote"].lower()
    attempt = call(readiness, "POST", token=owner)
    assert attempt["index"] == 0 and "correct" not in attempt
    call(readiness + "/answers", "POST", {"index": 0, "choice": 1}, outsider, 404)
    for index, choice in enumerate((1, 0, 3, 0, 1, 0)):
        attempt = call(readiness + "/answers", "POST", {"index": index, "choice": choice}, owner)
        assert attempt["index"] == index + 1
        if index < 5:
            assert not attempt["complete"] and "correct" not in attempt
        if index == 0:
            if args.recreate_disposable_api:
                subprocess.run(
                    ["docker", "compose", "up", "--force-recreate", "--no-deps", "--wait", "--wait-timeout", "120", "api"],
                    cwd=Path(__file__).resolve().parents[1], check=True,
                )
                assert call("/ready")["status"] == "ready"
                assert call("/documents", token=owner)[0]["id"] == document["id"]
                assert call(f'/quizzes/{quiz["id"]}', token=owner)["id"] == quiz["id"]
                call(root + "/offline-bundle", token=outsider, expected=404)
            assert call(unfinished_readiness, token=owner) == ["grade6-math"]
            assert call(unfinished_readiness, token=outsider) == []
            assert call(readiness, "POST", token=owner) == attempt
            if args.recreate_disposable_api:
                print("Verified sessions, study data and unfinished readiness after replacing the API container.")
    assert attempt["complete"] and attempt["correct"] == 5 and attempt["total"] == 6
    assert call(unfinished_readiness, token=owner) == []
    assert "answers" not in attempt
    assert call(readiness + "/answers", "POST", {"index": 0, "choice": 1}, owner) == attempt
    invitation = call("/progress-sharing/invitations", "POST", {"role": "parent"}, owner, 201)
    link = call("/progress-sharing/redeem", "POST", {"code": invitation["code"]}, outsider, 201)
    shared = f'/progress-sharing/{link["id"]}'
    call(shared + "/report", token=owner, expected=404)
    report = call(shared + "/report", token=outsider)
    assert report["week"] == {"chapters_active": 2, "chapters_mastered": 2}
    math = next(row for row in report["subjects"] if row["grade"] == 6 and row["subject"] == "Mathematics")
    assert (math["week_active"], math["week_mastered"]) == (2, 2)
    assert report["readiness"] == {"correct": 5, "total": 6, "by_chapter": attempt["by_chapter"]}
    call(shared, "DELETE", token=owner, expected=204)
    call(shared + "/report", token=outsider, expected=404)
    print("Verified readiness resume, account isolation, scoring, retry, parent aggregates and revocation over HTTPS.")
    if args.recreate_disposable_api:
        verify_disposable_restore(owner, outsider, document["id"], quiz["id"], attempt, credentials[0])
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
        form_type = "application/x-www-form-urlencoded"
        unconfirmed = call("/delete-account/google", "POST", b"", expected=400, content_type=form_type)
        assert "Confirm permanent deletion" in unconfirmed
        confirmed = b"confirm=yes"
        wrong_origin = call("/delete-account/google", "POST", confirmed, expected=403,
                            content_type=form_type, origin="https://untrusted.example")
        assert "Open this page directly" in wrong_origin
        missing_credential = call("/delete-account/google", "POST", confirmed, expected=400, content_type=form_type)
        assert "Choose your Google account" in missing_credential
        for token in tokens:
            assert call("/account", token=token)["owner_id"]
        print("Verified Google deletion page, origin and form guards over HTTPS without a Google session.")
    form = urlencode({**credentials[0], "confirm": "yes"}).encode()
    assert "were deleted" in call("/delete-account", "POST", form, content_type="application/x-www-form-urlencoded")
    tokens.remove(owner)
    call("/account", token=owner, expected=401)
finally:
    for token in tokens:
        call("/account", "DELETE", token=token, expected=204)

print("Verified HTTPS redirect, trusted TLS, readiness, upload, semantic retrieval, owner isolation, quiz generation and web account deletion.")
