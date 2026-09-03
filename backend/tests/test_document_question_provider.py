import json
from types import SimpleNamespace
import pytest

from app import document_question_provider as provider
from app.schemas import Chapter

TEXT = 'Mitochondria release usable energy for cellular work.'


def run(monkeypatch, item=None, review=None, difficulty=None, quality=None):
    item = item or dict(prompt='Which structure releases usable energy for cellular work?',
        options=['Mitochondria', 'Membrane', 'Ribosome', 'Cell wall'], correct_index=0,
        explanation=TEXT, chapter_id='cells', quote=TEXT)
    accepted = dict(item_index=0, demand_matches=True, assumptions_supported=True,
                    citation_complete=True, explanation_correct=True)
    outputs = iter([json.dumps({'questions': [item]}),
                    json.dumps({'answers': [0] if review is None else review}),
                    json.dumps({'items': [accepted] if quality is None else quality})])
    calls = []
    class Client:
        def __init__(self, **kwargs): self.responses = self
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(output_text=next(outputs))
    monkeypatch.setattr(provider, 'OpenAI', Client)
    result = provider.generate_document_questions(TEXT, [Chapter(id='cells', title='Cells', start_character=0,
        end_character=len(TEXT), confidence=1)], ['cells'], 1, SimpleNamespace(openai_api_key='synthetic', openai_model='synthetic'), difficulty)
    return result, calls


def test_generation_requires_grounding_and_separate_blind_review(monkeypatch):
    result, calls = run(monkeypatch)
    assert result[0].correct_option == 'Mitochondria'
    assert f'0-{len(TEXT)}' in result[0].source_reference
    assert all(call['store'] is False for call in calls)
    assert 'one exact continuous substring' in calls[0]['instructions']
    assert 'Never stitch separate excerpts together' in calls[0]['instructions']
    reviewed = json.loads(calls[1]['input'])['questions'][0]
    assert set(reviewed) == {'prompt', 'options'}
    assert len(calls) == 3
    assert calls[1]['timeout'] == calls[2]['timeout'] == 30.0
    audited = json.loads(calls[2]['input'])['questions'][0]
    assert audited['quote'] == TEXT
    assert audited['requested_demand'] is None
    assert audited['explanation'] == TEXT


@pytest.mark.parametrize('difficulty', ['easy', 'medium', 'hard', 'mixed'])
def test_difficulty_guidance_reaches_generation_without_changing_blind_review(monkeypatch, difficulty):
    from app.quiz_difficulty import DIFFICULTY_GUIDANCE
    _, calls = run(monkeypatch, difficulty=difficulty)
    payload = json.loads(calls[0]['input'])
    assert payload['requested_difficulty'] == difficulty
    assert payload['difficulty_guidance'] == DIFFICULTY_GUIDANCE[difficulty]
    assert len(payload['demand_plan']) == 1
    assert payload['difficulty_definitions'] == DIFFICULTY_GUIDANCE
    assert 'difficulty_guidance' not in json.loads(calls[1]['input'])
    assert json.loads(calls[2]['input'])['questions'][0]['requested_demand'] == (
        'easy' if difficulty == 'mixed' else difficulty)


@pytest.mark.parametrize('field', ['demand_matches', 'assumptions_supported', 'citation_complete', 'explanation_correct'])
def test_each_quality_failure_rejects_otherwise_accepted_answers(monkeypatch, field):
    verdict = dict(item_index=0, demand_matches=True, assumptions_supported=True,
                   citation_complete=True, explanation_correct=True)
    verdict[field] = False
    with pytest.raises(provider.QuestionGenerationUnavailable) as error:
        run(monkeypatch, quality=[verdict])
    assert str(error.value.__cause__) == 'Quality review rejected questions'


@pytest.mark.parametrize('quality', [[], [{}], [dict(item_index=1, demand_matches=True,
    assumptions_supported=True, citation_complete=True, explanation_correct=True)],
    [dict(item_index=0, demand_matches='true', assumptions_supported=True,
          citation_complete=True, explanation_correct=True)]])
def test_malformed_quality_review_fails_closed(monkeypatch, quality):
    with pytest.raises(provider.QuestionGenerationUnavailable):
        run(monkeypatch, quality=quality)


@pytest.mark.parametrize('review', [[-1], [1], [0, 0], []])
def test_reviewer_ambiguity_disagreement_or_bad_count_rejects_batch(monkeypatch, review):
    with pytest.raises(provider.QuestionGenerationUnavailable): run(monkeypatch, review=review)


def test_fabricated_quote_is_rejected(monkeypatch):
    item = dict(prompt='Which structure releases usable energy for cellular work?',
        options=['Mitochondria', 'Membrane', 'Ribosome', 'Cell wall'], correct_index=0,
        explanation=TEXT, chapter_id='cells', quote='This sentence does not exist in the source.')
    with pytest.raises(provider.QuestionGenerationUnavailable): run(monkeypatch, item=item)


def test_failed_provider_does_not_persist_a_quiz(monkeypatch, tmp_path):
    from test_mastery_loop import registered_client
    from app.config import get_settings
    from app.database import connection
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        doc = client.post('/v1/documents', headers=headers, files={'file': ('notes.txt', TEXT * 3)}).json()
        def fail(*args): raise provider.QuestionGenerationUnavailable('synthetic private upstream error')
        monkeypatch.setattr('app.main.generate_document_questions', fail)
        monkeypatch.setenv('LEARNING_AI_MODE', 'openai')
        response = client.post(f"/v1/documents/{doc['id']}/quizzes", headers=headers,
            json={'chapter_ids': [doc['chapters'][0]['id']], 'question_count': 5})
        assert response.status_code == 503
        assert 'private upstream' not in response.text
        with connection(get_settings().database_path) as db:
            assert db.execute('SELECT COUNT(*) FROM quizzes').fetchone()[0] == 0
    finally:
        client.__exit__(None, None, None)
