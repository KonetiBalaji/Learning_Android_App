from io import BytesIO
import asyncio
import multiprocessing
import os
import subprocess
import sys
import time

import fitz
import pytest

from app import document_service
from app.config import Settings
from app.database import initialize
from app.parser_capacity import ParserCapacityError, parser_slot
from fastapi import HTTPException, UploadFile


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


def test_parser_capacity_is_fail_fast_and_recovers_after_release():
    with parser_slot(2):
        with parser_slot(2):
            with pytest.raises(ParserCapacityError, match='capacity'):
                with parser_slot(2):
                    pass
    with parser_slot(2):
        pass


@pytest.mark.parametrize('limit', [0, 17])
def test_parser_capacity_rejects_unsafe_limits(limit):
    with pytest.raises(ValueError, match='Concurrent parser limit'):
        with parser_slot(limit):
            pass


@pytest.mark.parametrize('seconds', [0, 301])
def test_parser_capacity_rejects_unsafe_lease(seconds):
    with pytest.raises(ValueError, match='Parser lease'):
        with parser_slot(1, lease_seconds=seconds):
            pass


def hold_shared_parser_slot(database_path, ready, release, lease_seconds):
    with parser_slot(1, database_path, lease_seconds):
        ready.set()
        release.wait(10)


def test_parser_capacity_is_shared_across_processes_and_recovers_crashed_lease(tmp_path):
    database = tmp_path / 'shared.sqlite3'
    initialize(database)
    context = multiprocessing.get_context('spawn')

    ready, release = context.Event(), context.Event()
    process = context.Process(target=hold_shared_parser_slot,
                              args=(database, ready, release, 30))
    process.start()
    assert ready.wait(10)
    with pytest.raises(ParserCapacityError, match='capacity'):
        with parser_slot(1, database, 30):
            pass
    release.set()
    process.join(10)
    assert process.exitcode == 0
    with parser_slot(1, database, 30):
        pass

    crashed_ready, never_release = context.Event(), context.Event()
    crashed = context.Process(target=hold_shared_parser_slot,
                              args=(database, crashed_ready, never_release, 1))
    crashed.start()
    assert crashed_ready.wait(10)
    crashed.terminate()
    crashed.join(10)
    with pytest.raises(ParserCapacityError, match='capacity'):
        with parser_slot(1, database, 30):
            pass
    time.sleep(1.1)
    with parser_slot(1, database, 30):
        pass


def test_busy_upload_returns_retryable_error_without_saving(tmp_path):
    settings = Settings(runtime_dir=tmp_path, jwt_secret='test-secret',
                        max_concurrent_document_parsers=1)
    settings.uploads_dir.mkdir(parents=True)
    upload = UploadFile(filename='lesson.txt', file=BytesIO(b'x' * 100))
    with parser_slot(1):
        with pytest.raises(HTTPException) as raised:
            asyncio.run(document_service.validate_and_store(upload, settings))
    assert raised.value.status_code == 503
    assert raised.value.headers == {
        'X-Learning-Error': 'document_processing_busy', 'Retry-After': '2'}
    assert list(settings.uploads_dir.iterdir()) == []


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
