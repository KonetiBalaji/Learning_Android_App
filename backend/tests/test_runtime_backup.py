from contextlib import closing
import json
from pathlib import Path
import sqlite3

import pytest

from app.database import initialize
from app.runtime_backup import (
    DATABASE, RecoveryError, create_backup, restore_backup, verify_backup,
)


@pytest.fixture
def runtime(tmp_path):
    root = tmp_path / "runtime"
    root.mkdir()
    (root / "uploads").mkdir()
    initialize(root / DATABASE)
    live = root / "uploads" / "live-document.txt"
    live.write_text("Learner supplied source material", encoding="utf-8")
    deleted = root / "uploads" / "deleted-document.txt"
    deleted.write_text("Deleted file awaiting cleanup", encoding="utf-8")
    (root / "uploads" / "orphan.txt").write_text("Not a live document")
    (root / ".env.local").write_text("TEST_SECRET=must-not-be-copied")
    with closing(sqlite3.connect(root / DATABASE)) as db, db:
        db.execute("INSERT INTO users VALUES ('owner', 'fixture@example.com', 'hashed-password', '2026-09-03')")
        db.execute("INSERT INTO users VALUES ('other', 'other@example.com', 'other-hash', '2026-09-03')")
        db.execute("""INSERT INTO documents
            (id, owner_id, original_name, media_type, stored_path, extracted_text, chapters_json, created_at, stored_bytes)
            VALUES ('document', 'owner', 'source.txt', 'text/plain', ?, 'source text', '[]', '2026-09-03', ?)""",
            (str(live), live.stat().st_size))
        db.execute("INSERT INTO pending_file_deletions VALUES (?, 2, 'filesystem_error')", (str(deleted),))
        db.execute("INSERT INTO quizzes (id,document_id,owner_id,title,created_at) VALUES ('quiz','document','owner','Quiz','2026-09-03')")
        db.execute("""INSERT INTO questions
            (id, quiz_id, ordinal, prompt, options_json, correct_option, explanation,
             source_reference, answered_option, answered_at, question_type)
            VALUES ('question','quiz',0,'Prompt','{}','A','Explanation','source',
                    'B','2026-09-03','multiple_choice')""")
        db.execute("INSERT INTO quiz_creation_requests VALUES ('owner','request','fingerprint','quiz')")
        db.execute("INSERT INTO mastery_sessions (id,owner_id,grade,subject_id,chapter_id,status,tutor_json,questions_json,started_at) VALUES ('session','owner',8,'math','fractions','rewrite','{}','[]','2026-09-03')")
        db.execute("INSERT INTO mastery_attempts VALUES ('attempt','session','practice','question','answer',1,'Adding like fractions','2026-09-03',NULL)")
        db.execute("INSERT INTO study_time_intervals VALUES (1,'session','2026-09-03T00:00:00Z','2026-09-03T00:00:15Z',15)")
    return root


def backup(runtime, tmp_path):
    bundle = tmp_path / "bundle"
    create_backup(runtime, bundle, offline_confirmed=True)
    return bundle


def test_round_trip_preserves_learning_ownership_and_remaps_only_paths(runtime, tmp_path):
    bundle = backup(runtime, tmp_path)
    assert verify_backup(bundle) == {"documents": 1, "upload_files": 1, "pending_deletions": 1}
    assert {p.name for p in (bundle / "uploads").iterdir()} == {"live-document.txt"}
    assert not (bundle / ".env.local").exists()
    restored = tmp_path / "restored"
    restore_backup(bundle, restored, offline_confirmed=True)
    assert (restored / "RESTORE_COMPLETE").is_file()
    assert (restored / "uploads/live-document.txt").read_bytes() == (runtime / "uploads/live-document.txt").read_bytes()
    assert not (restored / "uploads/deleted-document.txt").exists()
    with closing(sqlite3.connect(runtime / DATABASE)) as source, closing(sqlite3.connect(restored / DATABASE)) as target:
        tables = [r[0] for r in source.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        for table in tables:
            if table not in {"documents", "pending_file_deletions"}:
                assert target.execute(f'SELECT * FROM "{table}"').fetchall() == source.execute(f'SELECT * FROM "{table}"').fetchall()
        assert target.execute("SELECT stored_path FROM documents").fetchone()[0] == str(restored / "uploads/live-document.txt")
        assert target.execute("SELECT stored_path, attempts, last_error FROM pending_file_deletions").fetchone() == (str(restored / "uploads/deleted-document.txt"), 2, 'filesystem_error')
        assert source.execute("SELECT stored_path FROM documents").fetchone()[0] == str(runtime / "uploads/live-document.txt")
    assert (runtime / "uploads/deleted-document.txt").exists()


def test_wal_commits_are_included(runtime, tmp_path):
    # An idle connection can keep WAL pages uncheckpointed. No worker is writing.
    with closing(sqlite3.connect(runtime / DATABASE)) as source:
        source.execute("PRAGMA journal_mode=WAL")
        source.execute("INSERT INTO learner_preferences VALUES ('owner', '[\"space\"]')")
        source.commit()
        assert Path(str(runtime / DATABASE) + "-wal").stat().st_size > 0
        bundle = backup(runtime, tmp_path)
    with closing(sqlite3.connect(bundle / DATABASE)) as target:
        assert target.execute("SELECT interests_json FROM learner_preferences").fetchone()[0] == '["space"]'


def test_requires_offline_ack_and_never_overwrites(runtime, tmp_path):
    with pytest.raises(RecoveryError, match="Stop all"):
        create_backup(runtime, tmp_path / "bundle")
    assert not (tmp_path / "bundle").exists()
    bundle = backup(runtime, tmp_path)
    with pytest.raises(RecoveryError, match="Stop all"):
        restore_backup(bundle, tmp_path / "restored")
    original = (runtime / DATABASE).read_bytes()
    with pytest.raises(RecoveryError, match="already exist"):
        restore_backup(bundle, runtime, offline_confirmed=True)
    assert (runtime / DATABASE).read_bytes() == original
    with pytest.raises(RecoveryError, match="already exist"):
        create_backup(runtime, bundle, offline_confirmed=True)


@pytest.mark.parametrize("operation", [create_backup, restore_backup])
def test_refuses_nested_destination(runtime, tmp_path, operation):
    source = runtime if operation == create_backup else backup(runtime, tmp_path)
    with pytest.raises(RecoveryError, match="overlap"):
        operation(source, source / "nested", offline_confirmed=True)


@pytest.mark.parametrize("damaged", [DATABASE, "uploads/live-document.txt", "manifest.json"])
def test_corruption_fails_before_restore_creates_target(runtime, tmp_path, damaged):
    bundle = backup(runtime, tmp_path)
    (bundle / damaged).write_bytes(b"corrupted")
    with pytest.raises((RecoveryError, ValueError)):
        restore_backup(bundle, tmp_path / "restored", offline_confirmed=True)
    assert not (tmp_path / "restored").exists()


@pytest.mark.parametrize("unsafe", ["../outside.txt", "uploads/../outside.txt", "uploads/CON", "uploads/sub/file.txt", "uploads/file:stream"])
def test_manifest_traversal_rejected(runtime, tmp_path, unsafe):
    bundle = backup(runtime, tmp_path)
    path = bundle / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["files"][unsafe] = {"bytes": 0, "sha256": ""}
    path.write_text(json.dumps(manifest))
    with pytest.raises(RecoveryError):
        restore_backup(bundle, tmp_path / "restored", offline_confirmed=True)
    assert not (tmp_path / "restored").exists()


def test_unlisted_file_rejected(runtime, tmp_path):
    bundle = backup(runtime, tmp_path)
    (bundle / "unexpected.txt").write_text("Unexpected")
    with pytest.raises(RecoveryError, match="unlisted"):
        verify_backup(bundle)


@pytest.mark.parametrize("failure", ["missing", "outside", "foreign_key", "live_deletion", "missing_table"])
def test_inconsistent_runtime_leaves_no_valid_manifest(runtime, tmp_path, failure):
    if failure == "missing":
        (runtime / "uploads/live-document.txt").unlink()
    else:
        with closing(sqlite3.connect(runtime / DATABASE)) as db, db:
            if failure == "outside":
                db.execute("UPDATE documents SET stored_path = ?", (str(tmp_path / "private.txt"),))
            elif failure == "foreign_key":
                db.execute("UPDATE documents SET owner_id = 'missing-owner'")
            elif failure == "missing_table":
                db.execute("DROP TABLE learner_preferences")
            else:
                db.execute("INSERT INTO pending_file_deletions (stored_path) SELECT stored_path FROM documents")
    with pytest.raises(RecoveryError):
        backup(runtime, tmp_path)
    assert not (tmp_path / "bundle/manifest.json").exists()


def test_cli_failure_does_not_print_sensitive_paths(tmp_path):
    import subprocess
    import sys
    result = subprocess.run([sys.executable, '-m', 'app.runtime_backup', 'verify',
                             str(tmp_path / 'private-learner-name')], capture_output=True, text=True)
    assert result.returncode == 1
    assert 'private-learner-name' not in result.stdout + result.stderr
    assert 'Traceback' not in result.stdout + result.stderr
    assert 'Do not use an incomplete destination' in result.stdout


def test_cli_backup_verify_restore(runtime, tmp_path):
    import subprocess
    import sys
    bundle = tmp_path / 'cli-bundle'
    restored = tmp_path / 'cli-restored'
    commands = [
        ['backup', str(runtime), '--destination', str(bundle), '--offline-confirmed'],
        ['verify', str(bundle)],
        ['restore', str(bundle), '--destination', str(restored), '--offline-confirmed'],
    ]
    for command in commands:
        result = subprocess.run([sys.executable, '-m', 'app.runtime_backup', *command], capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
        assert 'fixture@example.com' not in result.stdout + result.stderr
        assert 'must-not-be-copied' not in result.stdout + result.stderr
    assert (restored / 'RESTORE_COMPLETE').is_file()


def test_symlink_upload_rejected(runtime, tmp_path):
    file = runtime / "uploads/live-document.txt"
    file.unlink()
    outside = tmp_path / "private.txt"
    outside.write_text("Private")
    try:
        file.symlink_to(outside)
    except OSError:
        pytest.skip("Creating a symlink is not permitted on this host")
    with pytest.raises(RecoveryError, match="Linked"):
        backup(runtime, tmp_path)


def test_restored_api_login_resume_owner_isolation_and_deletion(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from app.main import app
    from test_mastery_loop import registered_client

    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        text = ('Cells are the basic units of life in living organisms. Mitochondria release usable energy for cellular work. '
                'Ribosomes support protein synthesis inside cells. Cell membranes regulate what enters and leaves the cell. '
                'Photosynthesis converts light energy into chemical energy in plants.')
        uploaded = client.post('/v1/documents', headers=headers, files={'file': ('notes.txt', text)})
        assert uploaded.status_code == 201
        document = uploaded.json()
        document_path = f"/v1/documents/{document['id']}"
        quiz = client.post(document_path + '/quizzes', headers=headers,
            json={'chapter_ids': [document['chapters'][0]['id']], 'question_count': 5}).json()
        quiz_path = f"/v1/quizzes/{quiz['id']}"
        question = quiz['first_question']
        assert client.post(quiz_path + f"/questions/{question['id']}/answer", headers=headers,
            json={'selected_option': question['options'][0]}).status_code == 200
        quiz_before = client.get(quiz_path, headers=headers).json()
        session = client.post('/v1/mastery/diagnostics', headers=headers,
            json={'grade': 8, 'subject_id': 'math', 'chapter_id': 'fractions'}).json()
        session_path = f"/v1/mastery/sessions/{session['id']}"
        assert client.post(session_path + '/diagnostic-answer', headers=headers,
            json={'selected_option': '1/2'}).status_code == 200
        before = client.get(session_path, headers=headers).json()
    finally:
        client.__exit__(None, None, None)
    # Both backup and restore happen after the source app and its cleanup job stop.
    original = tmp_path / 'runtime'
    bundle = backup(original, tmp_path)
    restored = tmp_path / 'restored'
    restore_backup(bundle, restored, offline_confirmed=True)
    monkeypatch.setenv('LEARNING_RUNTIME_DIR', str(restored))
    with TestClient(app) as client:
        login = client.post('/v1/auth/login', json={
            'email': f'student-{tmp_path.name}@example.com', 'password': 'long-enough-password'})
        assert login.status_code == 200
        restored_headers = {'Authorization': f"Bearer {login.json()['access_token']}"}
        assert client.get(session_path, headers=restored_headers).json() == before
        assert client.get(quiz_path, headers=restored_headers).json() == quiz_before
        assert client.get(document_path, headers=restored_headers).json() == document
        other = client.post('/v1/auth/register', json={'email': 'recovery-other@example.com', 'password': 'long-enough-password'})
        other_headers = {'Authorization': f"Bearer {other.json()['access_token']}"}
        for path in (session_path, quiz_path, document_path):
            assert client.get(path, headers=other_headers).status_code == 404
        with closing(sqlite3.connect(restored / DATABASE)) as db:
            restored_upload = Path(db.execute('SELECT stored_path FROM documents').fetchone()[0])
        assert client.delete(document_path, headers=restored_headers).status_code == 204
        assert not restored_upload.exists()
        assert client.get(quiz_path, headers=restored_headers).status_code == 404
    assert len(list((original / 'uploads').iterdir())) == 1
    assert verify_backup(bundle)['documents'] == 1
