import hashlib
import json
import re
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.config import get_settings
from app.database import connection, initialize
from app.document_selection import resolve_quiz_selection
from app.quiz_creation import creation_fingerprint
from app.quiz_service import generate_grounded_questions
from app.schemas import Chapter, QuizRequest, SourceRange
from test_mastery_loop import registered_client


def chapter(identifier, start, end):
    return Chapter(id=identifier, title=identifier, start_character=start, end_character=end, confidence=.8)


def span(identifier, start, end):
    return SourceRange(chapter_id=identifier, start_character=start, end_character=end)


def test_disjoint_excerpts_preserve_absolute_unicode_bounds_and_source_order():
    text = '😀abc OMIT def END ghi'
    chapters = [chapter('first', 0, 16), chapter('second', 16, len(text))]
    selected = resolve_quiz_selection(text, chapters, ['second', 'first'],
        [span('second', 18, 21), span('first', 10, 13), span('first', 0, 4)])
    assert [text[c.start_character:c.end_character] for c in selected] == ['😀abc', 'def', 'ghi']
    assert len({c.id for c in selected}) == 3
    assert all('selected excerpt' in c.title for c in selected)


@pytest.mark.parametrize('ranges', [
    [], [span('unknown', 0, 2)], [span('a', 0, 11)], [span('a', 5, 5)],
    [span('a', 5, 3)], [span('a', 0, 6), span('a', 5, 9)],
    [span('a', 0, 5), span('a', 0, 5)],
])
def test_invalid_ranges_are_not_silently_clipped(ranges):
    with pytest.raises(ValueError):
        resolve_quiz_selection('abcdefghij', [chapter('a', 0, 10)], ['a'], ranges)


def test_omitted_selected_chapter_and_blank_range_rejected():
    with pytest.raises(ValueError, match='every selected chapter'):
        resolve_quiz_selection('abcdefghij', [chapter('a', 0, 5), chapter('b', 5, 10)],
                               ['a', 'b'], [span('a', 0, 4)])
    with pytest.raises(ValueError, match='contain text'):
        resolve_quiz_selection('abc   ', [chapter('a', 0, 6)], ['a'], [span('a', 3, 6)])


@pytest.mark.parametrize('start', [True, 1.1, '1', -1])
def test_request_requires_nonnegative_integer_codepoint_offsets(start):
    with pytest.raises(ValidationError):
        SourceRange(chapter_id='a', start_character=start, end_character=5)


def test_legacy_fingerprint_stays_identical_and_excerpt_order_is_canonical():
    request = QuizRequest(chapter_ids=['a'], question_count=5)
    old_payload = {'document_id': 'doc', 'question_type': 'multiple_choice', 'difficulty': None,
                   'chapter_ids': ['a'], 'question_count': 5}
    old_hash = hashlib.sha256(json.dumps(old_payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    assert creation_fingerprint('doc', request) == old_hash
    first = request.model_copy(update={'source_ranges': [span('a', 0, 4), span('a', 6, 10)]})
    reversed_request = first.model_copy(update={'source_ranges': list(reversed(first.source_ranges))})
    assert creation_fingerprint('doc', first) == creation_fingerprint('doc', reversed_request)
    assert creation_fingerprint('doc', first) != old_hash


SOURCE = ('Chapter 1 Biology\nOUTSIDE_PREFIX secret not selected.\n'
    'Cells are the basic units of life in living organisms. '
    'Mitochondria release usable energy for cellular work. '
    'Ribosomes support protein synthesis inside cells. '
    'Cell membranes regulate what enters and leaves the cell. '
    'Photosynthesis converts light energy into chemical energy in plants. '
    '\nOUTSIDE_SUFFIX secret not selected.')


@pytest.mark.parametrize('mode', ['deterministic', 'openai'])
def test_excerpt_generation_resume_retry_and_owner_boundaries(monkeypatch, tmp_path, mode):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        document = client.post('/v1/documents', headers=headers, files={'file': ('notes.txt', SOURCE)}).json()
        path = f"/v1/documents/{document['id']}/quizzes"
        start, end = SOURCE.index('Cells are'), SOURCE.index('\nOUTSIDE_SUFFIX')
        ranges = [{'chapter_id': document['chapters'][0]['id'], 'start_character': start, 'end_character': end}]
        body = {'chapter_ids': [document['chapters'][0]['id']], 'source_ranges': ranges,
                'question_count': 5, 'request_id': str(uuid4())}
        calls = []
        def generate(text, chapters, selected_ids, count, *args):
            # Inspect exactly the passages the generator will retrieve, without any AI calls.
            passages = [text[c.start_character:c.end_character] for c in chapters if c.id in selected_ids]
            assert passages == [SOURCE[start:end]]
            assert 'OUTSIDE_' not in ''.join(passages)
            calls.append(1)
            return generate_grounded_questions(text, chapters, selected_ids, count)
        monkeypatch.setenv('LEARNING_AI_MODE', mode)
        monkeypatch.setattr('app.main.generate_document_questions' if mode == 'openai' else 'app.main.generate_grounded_questions', generate)
        response = client.post(path, headers=headers, json=body)
        assert response.status_code == 201, response.text
        quiz = response.json()
        assert quiz['source_ranges'] == ranges
        assert len(calls) == 1
        initialize(get_settings().database_path)
        assert client.post(path, headers=headers, json=body).json() == quiz
        assert len(calls) == 1
        resumed = client.get(f"/v1/quizzes/{quiz['id']}", headers=headers).json()
        assert resumed['source_ranges'] == ranges
        assert client.post(path, headers=headers, json={**body, 'source_ranges': None}).status_code == 409
        changed = [{**ranges[0], 'start_character': start + 1}]
        assert client.post(path, headers=headers, json={**body, 'source_ranges': changed}).status_code == 409
        assert len(calls) == 1
        with connection(get_settings().database_path) as db:
            rows = db.execute('SELECT prompt, explanation, source_reference FROM questions WHERE quiz_id = ?', (quiz['id'],)).fetchall()
            assert len(rows) == 5
            assert all('OUTSIDE_' not in row['prompt'] + row['explanation'] for row in rows)
            cited = [tuple(map(int, re.search(r'source characters (\d+)-(\d+)',
                                              row['source_reference']).groups())) for row in rows]
            assert all(start <= cited_start < cited_end <= end for cited_start, cited_end in cited)
            assert all(SOURCE[cited_start:cited_end].strip() in row['explanation']
                       for row, (cited_start, cited_end) in zip(rows, cited))
        other = client.post('/v1/auth/register', json={'email': 'excerpt-other@example.com', 'password': 'long-enough-password'}).json()
        other_headers = {'Authorization': f"Bearer {other['access_token']}"}
        assert client.post(path, headers=other_headers, json=body).status_code == 404
        assert client.get(f"/v1/quizzes/{quiz['id']}", headers=other_headers).status_code == 404
    finally:
        client.__exit__(None, None, None)


@pytest.mark.parametrize('mode', ['deterministic', 'openai'])
def test_invalid_excerpt_rejected_before_provider_and_without_rows(monkeypatch, tmp_path, mode):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        document = client.post('/v1/documents', headers=headers, files={'file': ('notes.txt', SOURCE)}).json()
        monkeypatch.setenv('LEARNING_AI_MODE', mode)
        def unexpected(*args):
            raise AssertionError('Invalid source ranges must never reach generation')
        monkeypatch.setattr('app.main.generate_document_questions', unexpected)
        monkeypatch.setattr('app.main.generate_grounded_questions', unexpected)
        body = {'chapter_ids': [document['chapters'][0]['id']], 'question_count': 5,
                'source_ranges': [{'chapter_id': document['chapters'][0]['id'], 'start_character': 0,
                                   'end_character': len(SOURCE) + 1}]}
        result = client.post(f"/v1/documents/{document['id']}/quizzes", headers=headers, json=body)
        assert result.status_code == 422
        with connection(get_settings().database_path) as db:
            assert db.execute('SELECT COUNT(*) FROM quizzes').fetchone()[0] == 0
            assert db.execute('SELECT COUNT(*) FROM questions').fetchone()[0] == 0
    finally:
        client.__exit__(None, None, None)
