from io import BytesIO
import zipfile

import pytest
from docx import Document

from app import document_limits as limits
from app import document_service
from app.config import get_settings
from app.database import connection
from test_mastery_loop import registered_client


def archive(entries):
    output = BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as zipped:
        for name, content in entries:
            zipped.writestr(name, content)
    return output.getvalue()


def test_normal_docx_passes_archive_checks():
    document = Document()
    document.add_paragraph('Ordinary learning material with enough readable text.')
    output = BytesIO()
    document.save(output)
    limits.validate_docx_archive(output.getvalue())


@pytest.mark.parametrize('name', ['../escape.xml', '/absolute.xml', 'word\\document.xml', 'C:private.xml'])
def test_rejects_ambiguous_archive_paths(name):
    content = archive([(name, 'synthetic')])
    if '\\' in name:
        # Windows ZIP writers normalize backslashes; craft the raw archive name
        # in both local and central headers to exercise an untrusted producer.
        content = content.replace(name.replace('\\', '/').encode(), name.encode())
    with pytest.raises(ValueError, match='archive path'):
        limits.validate_docx_archive(content)


def test_rejects_duplicate_members():
    with pytest.warns(UserWarning, match='Duplicate name'):
        content = archive([('same.xml', 'one'), ('same.xml', 'two')])
    with pytest.raises(ValueError, match='duplicate'):
        limits.validate_docx_archive(content)


@pytest.mark.parametrize('setting,limit,entries', [
    ('MAX_ARCHIVE_MEMBERS', 1, [('a', 'x'), ('b', 'y')]),
    ('MAX_MEMBER_BYTES', 10, [('a', 'x' * 11)]),
    ('MAX_ARCHIVE_BYTES', 10, [('a', '123456'), ('b', '123456')]),
    ('MAX_COMPRESSION_RATIO', 10, [('a', 'x' * 10000)]),
])
def test_rejects_resource_limit_breaches_before_parsing(monkeypatch, setting, limit, entries):
    monkeypatch.setattr(limits, setting, limit)
    with pytest.raises(ValueError):
        limits.validate_docx_archive(archive(entries))


def test_rejected_archive_leaves_no_file_or_document_and_no_parser_details(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        output = BytesIO()
        with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_BZIP2) as zipped:
            zipped.writestr('[Content_Types].xml', 'synthetic-content-types')
            zipped.writestr('word/document.xml', 'synthetic-private-name')
        content = output.getvalue()
        response = client.post('/v1/documents', headers=headers, files={'file': ('notes.docx', content)})
        assert response.status_code == 422
        assert 'synthetic-private-name' not in response.text
        assert 'Expanded archive' not in response.text
        assert list(get_settings().uploads_dir.iterdir()) == []
        with connection(get_settings().database_path) as db:
            assert db.execute('SELECT COUNT(*) FROM documents').fetchone()[0] == 0
    finally:
        client.__exit__(None, None, None)


def test_corrupt_member_crc_is_rejected_before_document_parser():
    output = BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_STORED) as zipped:
        zipped.writestr('[Content_Types].xml', 'synthetic-content-types')
        zipped.writestr('word/document.xml', 'synthetic-document-data')
    content = output.getvalue().replace(b'synthetic-document-data', b'synthetic-document-xxxx')
    with pytest.raises(zipfile.BadZipFile):
        limits.validate_docx_archive(content)


def test_non_docx_compression_is_rejected():
    output = BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_BZIP2) as zipped:
        zipped.writestr('[Content_Types].xml', 'synthetic')
        zipped.writestr('word/document.xml', 'synthetic')
    with pytest.raises(ValueError, match='Unsupported archive compression'):
        limits.validate_docx_archive(output.getvalue())


def test_parser_timeout_returns_stable_recovery_without_saving(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        monkeypatch.setattr(document_service, 'extract_text_isolated',
                            lambda *_: (_ for _ in ()).throw(TimeoutError('private parser detail')))
        response = client.post('/v1/documents', headers=headers,
                               files={'file': ('lesson.txt', b'ordinary lesson text ' * 10)})
        assert response.status_code == 422
        assert response.headers['X-Learning-Error'] == 'document_processing_limit'
        assert 'private parser detail' not in response.text
        assert list(get_settings().uploads_dir.iterdir()) == []
        with connection(get_settings().database_path) as db:
            assert db.execute('SELECT COUNT(*) FROM documents').fetchone()[0] == 0
    finally:
        client.__exit__(None, None, None)
