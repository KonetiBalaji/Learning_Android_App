from test_mastery_loop import registered_client


def test_authenticated_retention_policy_reports_enforced_configuration(monkeypatch, tmp_path):
    monkeypatch.setenv('LEARNING_GUARDIAN_INVITATION_RETENTION_DAYS', '14')
    monkeypatch.setenv('LEARNING_ORPHAN_UPLOAD_GRACE_HOURS', '6')
    monkeypatch.setenv('LEARNING_BACKUP_RETENTION_DAYS', '21')
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        response = client.get('/v1/privacy/retention', headers=headers)
        assert response.status_code == 200
        assert response.json() == {
            'active_learning_data': 'until_account_deletion',
            'uploaded_documents': 'until_document_or_account_deletion',
            'deleted_files': 'queued_for_immediate_cleanup',
            'guardian_invitation_days': 14,
            'crash_orphan_hours': 6,
            'backup_days': 21,
        }
        assert client.get('/v1/privacy/retention').status_code == 401
    finally:
        client.__exit__(None, None, None)
