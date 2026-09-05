"""Bounded malformed-document parser stress and recovery smoke."""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import gc
from io import BytesIO
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import warnings

warnings.filterwarnings('ignore', message='The `fitz` API is deprecated.*')

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import initialize
from app.config import Settings
from app.document_service import extract_text_isolated, validate_and_store
from fastapi import HTTPException, UploadFile


MALFORMED_INPUTS = (
    (b'%PDF-1.7\n1 0 obj\n<< /Length 999999999 >>\nstream\ntruncated', '.pdf'),
    (b'%PDF-1.4\nstartxref\n999999999\n%%EOF', '.pdf'),
    (b'PK\x03\x04not-a-valid-office-archive', '.docx'),
    (b'not an archive or document at all', '.docx'),
)


def run(attempts: int, concurrency: int, timeout_seconds: int) -> dict:
    if not 20 <= attempts <= 500 or not 2 <= concurrency <= 32 or concurrency > attempts:
        raise ValueError('Use 20-500 attempts and 2-32 workers, with workers no greater than attempts')
    if not 1 <= timeout_seconds <= 15:
        raise ValueError('Use a parser timeout from 1 to 15 seconds')
    with tempfile.TemporaryDirectory(prefix='learnsmart-parser-stress-') as directory:
        settings = Settings(runtime_dir=Path(directory), jwt_secret='synthetic-stress-secret',
                            max_concurrent_document_parsers=2,
                            document_parse_timeout_seconds=timeout_seconds)
        settings.uploads_dir.mkdir(exist_ok=True)
        database = settings.database_path
        initialize(database)

        def one(index: int) -> str:
            content, suffix = MALFORMED_INPUTS[index % len(MALFORMED_INPUTS)]
            try:
                upload = UploadFile(filename=f'hostile-{index}{suffix}', file=BytesIO(content))
                asyncio.run(validate_and_store(upload, settings))
            except HTTPException as error:
                if error.status_code == 503:
                    return 'busy'
                if error.status_code == 422:
                    return 'rejected'
                raise RuntimeError('Malformed upload returned an unexpected status') from error
            raise RuntimeError('Malformed parser input was unexpectedly accepted')

        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            outcomes = Counter(future.result() for future in as_completed(
                [pool.submit(one, index) for index in range(attempts)]))
        duration = time.perf_counter() - started
        if outcomes['timeout'] or outcomes['rejected'] < 1 or sum(outcomes.values()) != attempts:
            raise RuntimeError('Malformed parser stress did not fail in the expected bounded states')
        connection = sqlite3.connect(database)
        try:
            remaining_leases = connection.execute('SELECT COUNT(*) FROM document_parser_leases').fetchone()[0]
        finally:
            connection.close()
        if remaining_leases:
            raise RuntimeError('Parser leases remained after stress completion')
        if any(settings.uploads_dir.iterdir()):
            raise RuntimeError('Rejected malformed input left a stored upload')
        recovery_source = 'Chapter 1 Recovery\n' + ('Valid source text remains readable after malformed load. ' * 3)
        recovered = extract_text_isolated(recovery_source.encode(), '.txt', timeout_seconds, 2, database)
        if recovered != recovery_source:
            raise RuntimeError('Valid parser recovery changed source text')
        result = {'attempts': attempts, 'concurrency': concurrency,
                  'rejected': outcomes['rejected'], 'busy': outcomes['busy'],
                  'timeouts': outcomes['timeout'], 'remaining_leases': remaining_leases,
                  'recovery': 'exact', 'duration_seconds': round(duration, 3)}
        # Drop completed-future/exception cycles before deleting the temporary
        # SQLite file on Windows, where an unreachable connection still locks it.
        gc.collect()
        time.sleep(0.5)
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempts', type=int, default=100)
    parser.add_argument('--concurrency', type=int, default=12)
    parser.add_argument('--timeout-seconds', type=int, default=5)
    args = parser.parse_args()
    print('Parser stress smoke passed:', json.dumps(
        run(args.attempts, args.concurrency, args.timeout_seconds), sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
