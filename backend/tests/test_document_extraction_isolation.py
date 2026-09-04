from io import BytesIO
import os
import subprocess
import sys
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


@pytest.mark.skipif(os.name != 'nt', reason='Windows Job Object enforcement')
def test_windows_worker_can_install_fail_closed_memory_job():
    result = subprocess.run([
        sys.executable, '-c',
        'from app.document_service import apply_parser_memory_limit; '
        'apply_parser_memory_limit(); print("WINDOWS_PARSER_MEMORY_LIMIT_ACTIVE")',
    ], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[-1] == 'WINDOWS_PARSER_MEMORY_LIMIT_ACTIVE'


@pytest.mark.skipif(os.name != 'nt', reason='Windows Job Object enforcement')
def test_windows_job_blocks_allocation_beyond_process_memory_limit():
    program = (
        'import app.document_service as service; '
        'service.PARSER_MEMORY_BYTES = 256 * 1024 * 1024; '
        'service.apply_parser_memory_limit(); '
        '\ntry:\n bytearray(512 * 1024 * 1024); raise SystemExit(3)'
        '\nexcept MemoryError:\n print("WINDOWS_PARSER_ALLOCATION_BLOCKED")'
    )
    result = subprocess.run([sys.executable, '-c', program], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[-1] == 'WINDOWS_PARSER_ALLOCATION_BLOCKED'


def slow_worker(pipe, content, suffix):
    time.sleep(10)
