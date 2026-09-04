from io import BytesIO
import time

import fitz
import pytest

from app import document_service


def pdf_bytes(text: str) -> bytes:
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), text)
    content = pdf.tobytes()
    pdf.close()
    return content


def test_isolated_parser_returns_real_pdf_text():
    assert 'isolated parser' in document_service.extract_text_isolated(
        pdf_bytes('Ordinary isolated parser content'), '.pdf', 10)


def test_isolated_parser_collapses_corrupt_input_without_child_details():
    with pytest.raises(ValueError, match='safety checks'):
        document_service.extract_text_isolated(b'private corrupt bytes', '.pdf', 10)


def test_isolated_parser_rejects_oversized_result(monkeypatch):
    monkeypatch.setattr(document_service, 'MAX_EXTRACTED_CHARACTERS', 20)
    # Spawned children do not inherit monkeypatches on Windows, so exercise the
    # worker protocol directly with a small fake pipe for the bound itself.
    class Pipe:
        result = None
        def send(self, value): self.result = value
        def close(self): pass
    pipe = Pipe()
    monkeypatch.setattr(document_service, 'extract_text', lambda *_: 'x' * 21)
    document_service._bounded_extract_worker(pipe, b'data', '.txt')
    assert pipe.result == ('limit', None)


def test_timeout_terminates_child(monkeypatch):
    monkeypatch.setattr(document_service, '_bounded_extract_worker', slow_worker)
    started = time.monotonic()
    with pytest.raises(TimeoutError, match='time limit'):
        document_service.extract_text_isolated(b'data', '.txt', 1)
    assert time.monotonic() - started < 4


def slow_worker(pipe, content, suffix):
    time.sleep(10)
