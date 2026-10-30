import io
from types import SimpleNamespace

from PIL import Image, ImageDraw
import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from study.documents import DocumentError
from study.processing import analyze, recognize
from test_learning_flow import MATERIAL, account, client, upload


def scanned_pdf():
    image = Image.new("RGB", (900, 900), "white")
    ImageDraw.Draw(image).multiline_text((20, 20), MATERIAL, fill="black", spacing=8)
    output = io.BytesIO()
    image.save(output, format="PDF", resolution=100)
    image.close()
    return output.getvalue()


def test_low_confidence_scan_requires_owner_confirmation_before_quiz(client, monkeypatch):
    monkeypatch.setattr("study.api.analyze_upload", lambda filename, content: analyze(filename, content, recognition=lambda image: (MATERIAL, 0.42)))
    first = account(client, "scan-owner")
    other = account(client, "scan-other")
    response = client.post("/documents", headers=first, files={"file": ("scan.pdf", scanned_pdf(), "application/pdf")})
    assert response.status_code == 201, response.text
    document = response.json()
    assert document["processing_state"] == "needs_review" and document["ocr_review_count"] == 1
    assert "_pages" not in document and "_ocr_pages" not in document
    root = f'/documents/{document["id"]}'
    assert client.post(root + "/quizzes", headers=first, json={"count": 5}).status_code == 409
    assert client.get(root + "/ocr-pages", headers=other).status_code == 404
    assert "image_base64" not in client.get(root + "/ocr-pages", headers=first).json()[0]
    page = client.get(root + "/ocr-pages/1", headers=first).json()
    assert page["text"] == MATERIAL and page["image_base64"] and not page["human_reviewed"]
    approval = client.post(root + "/ocr-pages/1/review", headers=first, json={"text": MATERIAL})
    assert approval.status_code == 200, approval.text
    assert approval.json()["processing_state"] == "ready" and approval.json()["ocr_review_count"] == 0
    assert client.post(root + "/ocr-pages/1/review", headers=first, json={"text": MATERIAL}).status_code == 200
    assert client.post(root + "/ocr-pages/1/review", headers=first, json={"text": "Changed source"}).status_code == 409
    assert client.post(root + "/quizzes", headers=first, json={"count": 5}).status_code == 201
    payload = client.app.state.store.db.execute("SELECT payload FROM records WHERE id=?", (document["id"],)).fetchone()[0]
    assert b"Mitochondria" not in payload and page["image_base64"].encode() not in payload
    assert client.delete(root, headers=first).status_code == 204
    assert client.get(root + "/ocr-pages/1", headers=first).status_code == 404


def test_high_confidence_ocr_is_usable_but_source_is_immutable_after_quiz(client, monkeypatch):
    monkeypatch.setattr("study.api.analyze_upload", lambda filename, content: analyze(filename, content, recognition=lambda image: (MATERIAL, 0.995)))
    headers = account(client)
    document = client.post("/documents", headers=headers, files={"file": ("scan.pdf", scanned_pdf())}).json()
    root = f'/documents/{document["id"]}'
    assert document["processing_state"] == "ready"
    assert client.post(root + "/quizzes", headers=headers, json={"count": 5}).status_code == 201
    assert client.post(root + "/ocr-pages/1/review", headers=headers, json={"text": "Altered text"}).status_code == 409


def test_confirmed_transcription_preserves_document_size_limit(client, monkeypatch):
    monkeypatch.setattr("study.api.analyze_upload", lambda filename, content: analyze(filename, content, recognition=lambda image: (MATERIAL, 0.2)))
    headers = account(client)
    document = client.post("/documents", headers=headers, files={"file": ("scan.pdf", scanned_pdf())}).json()
    root = f'/documents/{document["id"]}'
    monkeypatch.setattr("study.api.MAX_TEXT", 50)
    response = client.post(root + "/ocr-pages/1/review", headers=headers, json={"text": MATERIAL})
    assert response.status_code == 422
    assert not client.get(root + "/ocr-pages/1", headers=headers).json()["human_reviewed"]


def test_excessive_ocr_pages_are_bounded_before_recognition():
    writer = PdfWriter()
    for _ in range(51):
        writer.add_blank_page(width=100, height=100)
    content = io.BytesIO()
    writer.write(content)
    with pytest.raises(DocumentError, match="50 pages"):
        analyze("many.pdf", content.getvalue())


def test_unreadable_scan_never_invents_passages():
    document = analyze("unclear.pdf", scanned_pdf(), recognition=lambda image: ("", 0.0))
    assert document["processing_state"] == "needs_review"
    assert document["passages"] == [] and document["_ocr_pages"][0]["image_base64"]


def test_native_header_does_not_hide_a_scanned_body():
    writer = PdfWriter()
    page = writer.add_page(PdfReader(io.BytesIO(scanned_pdf())).pages[0])
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
    page["/Resources"][NameObject("/Font")] = DictionaryObject({NameObject("/F1"): font})
    stream = DecodedStreamObject()
    stream.set_data(page.get_contents().get_data() + b"\nBT /F1 12 Tf 10 10 Td (Chapter 1 Cells) Tj ET")
    page[NameObject("/Contents")] = stream
    content = io.BytesIO()
    writer.write(content)
    document = analyze("mixed.pdf", content.getvalue(), recognition=lambda image: (MATERIAL, 0.5))
    assert len(document["_ocr_pages"]) == 1
    assert "Ribosomes" in document["_pages"][0]


@pytest.mark.parametrize("scores", [[float("nan")], [1.1], [-0.1], []])
def test_invalid_ocr_confidence_is_rejected(scores):
    with pytest.raises(DocumentError):
        recognize(None, engine=lambda image: SimpleNamespace(txts=["recognized text"], scores=scores))


def test_source_change_during_generation_does_not_persist_stale_quiz(client, monkeypatch):
    headers = account(client)
    document = upload(client, headers)
    store = client.app.state.store
    owner = store.db.execute("SELECT id FROM users").fetchone()[0]
    import study.api as api
    original = api.generate_local

    def change_source_then_generate(*args):
        with store.lock:
            changed = store.get(document["id"], owner, "document")
            changed["source_revision"] += 1
            store.save(changed["id"], owner, "document", changed["id"], changed["created"], changed)
        return original(*args)

    monkeypatch.setattr(api, "generate_local", change_source_then_generate)
    response = client.post(f'/documents/{document["id"]}/quizzes', headers=headers, json={"count": 5})
    assert response.status_code == 409
    assert store.all(owner, "quiz") == []
