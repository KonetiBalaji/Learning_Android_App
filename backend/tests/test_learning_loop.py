from __future__ import annotations

from pathlib import Path
from io import BytesIO

import fitz
from docx import Document
from fastapi.testclient import TestClient


def test_document_to_feedback_to_results(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LEARNING_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.setenv("LEARNING_JWT_SECRET", "test-secret-that-is-long-enough-32")
    from app.main import app

    with TestClient(app) as client:
        registration = client.post("/v1/auth/register", json={"email": "student@example.com", "password": "long-enough-password"})
        assert registration.status_code == 201
        headers = {"Authorization": f"Bearer {registration.json()['access_token']}"}
        content = """Chapter 1 Introduction to Biology
Cells are the basic units of life in living organisms. Mitochondria release usable energy for cellular work. Ribosomes support protein synthesis inside cells. Cell membranes regulate what enters and leaves the cell. Photosynthesis converts light energy into chemical energy in plants.
"""
        uploaded = client.post("/v1/documents", files={"file": ("biology.txt", content, "text/plain")}, headers=headers)
        assert uploaded.status_code == 201, uploaded.text
        document = uploaded.json()
        quiz = client.post(f"/v1/documents/{document['id']}/quizzes", json={"chapter_ids": [document['chapters'][0]['id']], "question_count": 5}, headers=headers)
        assert quiz.status_code == 201, quiz.text
        first = quiz.json()["first_question"]
        wrong_option = next(option for option in first["options"] if option != first["options"][0])
        feedback = client.post(f"/v1/quizzes/{quiz.json()['id']}/questions/{first['id']}/answer", json={"selected_option": wrong_option}, headers=headers)
        assert feedback.status_code == 200, feedback.text
        assert "source" in feedback.json()["source_reference"].lower()
        duplicate = client.post(f"/v1/quizzes/{quiz.json()['id']}/questions/{first['id']}/answer", json={"selected_option": wrong_option}, headers=headers)
        assert duplicate.status_code == 409
        results = client.get(f"/v1/quizzes/{quiz.json()['id']}/results", headers=headers)
        assert results.status_code == 200
        assert results.json()["answered"] == 1


def test_document_access_is_owner_scoped(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LEARNING_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.setenv("LEARNING_JWT_SECRET", "test-secret-that-is-long-enough-32")
    from app.main import app

    with TestClient(app) as client:
        first = client.post("/v1/auth/register", json={"email": "first@example.com", "password": "long-enough-password"}).json()
        second = client.post("/v1/auth/register", json={"email": "second@example.com", "password": "long-enough-password"}).json()
        first_headers = {"Authorization": f"Bearer {first['access_token']}"}
        second_headers = {"Authorization": f"Bearer {second['access_token']}"}
        text = "Cells are the basic units of life. Mitochondria release usable energy. Ribosomes support protein synthesis. Membranes regulate entry and exit. Plants use photosynthesis to store energy."
        upload = client.post("/v1/documents", files={"file": ("notes.txt", text, "text/plain")}, headers=first_headers)
        assert upload.status_code == 201
        assert client.delete(f"/v1/documents/{upload.json()['id']}", headers=second_headers).status_code == 404


def test_upload_rejects_unsupported_or_empty_material(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LEARNING_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.setenv("LEARNING_JWT_SECRET", "test-secret-that-is-long-enough-32")
    from app.main import app

    with TestClient(app) as client:
        token = client.post("/v1/auth/register", json={"email": "validation@example.com", "password": "long-enough-password"}).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        unsupported = client.post("/v1/documents", files={"file": ("notes.exe", b"not a study document", "application/octet-stream")}, headers=headers)
        assert unsupported.status_code == 415
        empty = client.post("/v1/documents", files={"file": ("notes.txt", b"", "text/plain")}, headers=headers)
        assert empty.status_code == 422


def test_pdf_and_docx_uploads_are_extractable(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LEARNING_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.setenv("LEARNING_JWT_SECRET", "test-secret-that-is-long-enough-32")
    from app.main import app

    paragraph = "Cells are the fundamental units of life. Mitochondria release energy for cellular work. Ribosomes build proteins inside the cell. Cell membranes regulate material movement. Photosynthesis stores energy in plants."
    word = Document()
    word.add_paragraph(paragraph)
    word_bytes = BytesIO()
    word.save(word_bytes)
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), paragraph)
    pdf_bytes = pdf.tobytes()
    pdf.close()

    with TestClient(app) as client:
        token = client.post("/v1/auth/register", json={"email": "formats@example.com", "password": "long-enough-password"}).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        docx = client.post("/v1/documents", files={"file": ("biology.docx", word_bytes.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}, headers=headers)
        pdf_upload = client.post("/v1/documents", files={"file": ("biology.pdf", pdf_bytes, "application/pdf")}, headers=headers)
        assert docx.status_code == 201, docx.text
        assert pdf_upload.status_code == 201, pdf_upload.text
