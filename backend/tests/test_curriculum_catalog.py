from __future__ import annotations

from test_mastery_loop import registered_client


def test_offline_grade_8_math_diagnostics_start_without_provider_credentials(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        for chapter in ('fractions', 'decimals', 'percentages', 'algebra'):
            response = client.post('/v1/mastery/diagnostics', headers=headers,
                                   json={'grade': 8, 'subject_id': 'math', 'chapter_id': chapter})
            assert response.status_code == 201
            question = response.json()['question']
            assert question['ordinal'] == 1 and question['total'] == 3
            assert 'correct_option' not in question
    finally:
        client.__exit__(None, None, None)


def test_authenticated_catalog_is_versioned_grade_scoped_and_internally_consistent(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        response = client.get('/v1/catalog?grade=8', headers=headers)
        assert response.status_code == 200
        catalog = response.json()
        assert catalog['version'] == 'foundation-2026-09'
        assert catalog['grade'] == 8
        assert catalog['board'] == 'unconfirmed'
        assert [(subject['id'], subject['title']) for subject in catalog['subjects']] == [
            ('math', 'Mathematics'), ('science', 'Science'),
            ('english', 'English'), ('social', 'Social Studies'),
        ]
        assert sum(len(subject['chapters']) for subject in catalog['subjects']) == 17
        for subject in catalog['subjects']:
            ids = [chapter['id'] for chapter in subject['chapters']]
            assert len(ids) == len(set(ids))
            for chapter in subject['chapters']:
                prerequisite = chapter['prerequisite_id']
                if prerequisite is not None:
                    assert prerequisite in ids
                    assert ids.index(prerequisite) < ids.index(chapter['id'])
        for grade in (1, 7, 9, 12):
            unsupported = client.get(f'/v1/catalog?grade={grade}', headers=headers)
            assert unsupported.status_code == 422
            assert unsupported.json()['detail'] == 'The reviewed curriculum catalog currently starts with Grade 8'
        assert client.get('/v1/catalog?grade=0', headers=headers).status_code == 422
        assert client.get('/v1/catalog?grade=13', headers=headers).status_code == 422
        assert client.get('/v1/catalog?grade=8').status_code == 401
    finally:
        client.__exit__(None, None, None)


def test_diagnostic_rejects_non_catalog_selection_before_provider_work(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        import app.main as api
        calls = []
        monkeypatch.setattr(api, 'tutor_provider', lambda settings: calls.append(settings) or (_ for _ in ()).throw(AssertionError('provider called')))
        response = client.post('/v1/mastery/diagnostics', headers=headers,
                               json={'grade': 8, 'subject_id': 'invented', 'chapter_id': 'anything'})
        assert response.status_code == 422
        assert response.json()['detail'] == 'This subject or chapter is not in the current catalog'
        assert calls == []
    finally:
        client.__exit__(None, None, None)


def test_catalog_lookup_normalizes_only_known_identifiers():
    from app.learning_path import catalog_chapter
    assert catalog_chapter(' MATH ', ' FRACTIONS ').title == 'Fractions'
    assert catalog_chapter('math', 'fraction') is None
    assert catalog_chapter('mathematics', 'fractions') is None


def test_diagnostic_rejects_unsupported_grade_before_provider_work(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        import app.main as api
        calls = []
        monkeypatch.setattr(api, 'tutor_provider', lambda settings: calls.append(settings))
        response = client.post('/v1/mastery/diagnostics', headers=headers,
                               json={'grade': 7, 'subject_id': 'math', 'chapter_id': 'fractions'})
        assert response.status_code == 422
        assert response.json()['detail'] == 'Diagnostics currently start with Grade 8'
        assert calls == []
    finally:
        client.__exit__(None, None, None)
