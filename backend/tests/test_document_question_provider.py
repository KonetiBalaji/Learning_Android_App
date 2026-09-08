import json
from types import SimpleNamespace
import pytest

from app import document_question_provider as provider
from app.ai_limits import DOCUMENT_GENERATION_OUTPUT_TOKENS, REVIEW_OUTPUT_TOKENS
from app.quiz_service import GeneratedQuestion
from app.schemas import Chapter

TEXT = 'Mitochondria release usable energy for cellular work.'


def run(monkeypatch, item=None, review=None, difficulty=None, quality=None, text=TEXT,
        question_type='multiple_choice', retry_feedback=None):
    item = item or dict(prompt='Which structure releases usable energy for cellular work?',
        options=['Mitochondria', 'Membrane', 'Ribosome', 'Cell wall'], correct_index=0,
        explanation=TEXT, chapter_id='cells', first_excerpt=0, last_excerpt=0)
    item.setdefault('concept', 'Mitochondria')
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
    result = provider.generate_document_questions(text, [Chapter(id='cells', title='Cells', start_character=0,
        end_character=len(text), confidence=1)], ['cells'], 1, SimpleNamespace(openai_api_key='synthetic', openai_model='synthetic'), difficulty, question_type,
        retry_feedback=retry_feedback)
    return result, calls


def test_generation_requires_grounding_and_separate_blind_review(monkeypatch):
    result, calls = run(monkeypatch)
    assert result[0].correct_option == 'Mitochondria'
    assert result[0].chapter_id == 'cells'
    assert result[0].concept == 'Mitochondria'
    assert f'0-{len(TEXT)}' in result[0].source_reference
    assert all(call['store'] is False for call in calls)
    assert 'timeout' not in calls[0]  # The client owns the generation boundary.
    assert 'server reconstructs the exact supporting quote' in calls[0]['instructions']
    assert json.loads(calls[0]['input'])['passages']['cells'] == [{'id': 0, 'text': TEXT}]
    reviewed = json.loads(calls[1]['input'])['questions'][0]
    assert set(reviewed) == {'prompt', 'options'}
    assert len(calls) == 3
    assert calls[0]['max_output_tokens'] == DOCUMENT_GENERATION_OUTPUT_TOKENS
    assert calls[1]['max_output_tokens'] == calls[2]['max_output_tokens'] == REVIEW_OUTPUT_TOKENS
    assert calls[1]['timeout'] == calls[2]['timeout'] == 30.0
    audited = json.loads(calls[2]['input'])['questions'][0]
    assert audited['quote'] == TEXT
    assert audited['requested_demand'] is None
    assert audited['explanation'] == TEXT


def test_repeated_source_text_keeps_selected_occurrence_offset(monkeypatch):
    item = dict(prompt='Which structure releases usable energy for cellular work?',
        options=['Mitochondria', 'Membrane', 'Ribosome', 'Cell wall'], correct_index=0,
        explanation=TEXT, chapter_id='cells', first_excerpt=1, last_excerpt=1)
    result, calls = run(monkeypatch, item=item, text=TEXT + '\n' + TEXT)
    start = len(TEXT) + 1
    assert f'{start}-{start + len(TEXT)}' in result[0].source_reference
    assert json.loads(calls[2]['input'])['questions'][0]['quote'] == TEXT


def test_invented_concept_label_fails_closed(monkeypatch):
    item = dict(prompt='Which structure releases usable energy for cellular work?',
        options=['Mitochondria', 'Membrane', 'Ribosome', 'Cell wall'], correct_index=0,
        explanation=TEXT, chapter_id='cells', concept='cellular respiration',
        first_excerpt=0, last_excerpt=0)
    with pytest.raises(provider.QuestionGenerationUnavailable) as error:
        run(monkeypatch, item=item)
    assert str(error.value.__cause__) == 'Ungrounded concept'
    assert error.value.safe_stage == 'concept_validation'


def test_generation_failure_logs_only_safe_stage_and_exception_class(monkeypatch, caplog):
    private_detail = 'private generated response must not reach logs'
    item = dict(prompt='Which structure releases usable energy for cellular work?',
        options=['Mitochondria', 'Membrane', 'Ribosome', 'Cell wall'], correct_index=0,
        explanation=TEXT, chapter_id='cells', concept=private_detail,
        first_excerpt=0, last_excerpt=0)

    with caplog.at_level('WARNING'), pytest.raises(provider.QuestionGenerationUnavailable):
        run(monkeypatch, item=item)

    assert 'stage=concept_validation reason=ValueError' in caplog.text
    assert private_detail not in caplog.text


@pytest.mark.parametrize('kind,options', [('true_false', ['True', 'False']), ('yes_no', ['Yes', 'No'])])
@pytest.mark.parametrize('answer', [0, 1])
def test_binary_choices_keep_canonical_order_and_answer(monkeypatch, kind, options, answer):
    item = dict(prompt='Do mitochondria release energy for cellular work?', options=options,
        correct_index=answer, explanation=TEXT, chapter_id='cells', first_excerpt=0, last_excerpt=0)
    result, calls = run(monkeypatch, item=item, question_type=kind, review=[answer])
    assert result[0].options == options
    assert result[0].correct_option == options[answer]
    assert json.loads(calls[0]['input'])['question_type'] == kind
    assert len(calls) == 3  # Includes both reviews; stubs test routing, not factual quality.


@pytest.mark.parametrize('kind,options,index', [
    ('true_false', ['False', 'True'], 0), ('yes_no', ['Yes', 'Maybe'], 0),
    ('multiple_choice', ['Yes', 'No'], 0), ('true_false', ['True', 'False'], 2),
    ('yes_no', ['Yes', 'No', 'Maybe'], 0)])
def test_invalid_type_options_fail_closed(monkeypatch, kind, options, index):
    item = dict(prompt='Does the source support this statement?', options=options,
        correct_index=index, explanation=TEXT, chapter_id='cells', first_excerpt=0, last_excerpt=0)
    with pytest.raises(provider.QuestionGenerationUnavailable):
        run(monkeypatch, item=item, question_type=kind)


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


def test_safe_quality_feedback_reaches_only_regeneration_prompt(monkeypatch):
    _, calls = run(monkeypatch, retry_feedback='citation_complete,demand_matches')
    assert json.loads(calls[0]['input'])['retry_feedback'] == 'citation_complete,demand_matches'
    assert 'a direct fact restatement or synonym swap is Easy, not Medium' in calls[0]['instructions']
    assert 'retry_feedback' not in json.loads(calls[1]['input'])
    assert 'retry_feedback' not in json.loads(calls[2]['input'])


@pytest.mark.parametrize('field', ['demand_matches', 'assumptions_supported', 'citation_complete', 'explanation_correct'])
def test_each_quality_failure_rejects_otherwise_accepted_answers(monkeypatch, field):
    verdict = dict(item_index=0, demand_matches=True, assumptions_supported=True,
                   citation_complete=True, explanation_correct=True)
    verdict[field] = False
    with pytest.raises(provider.QuestionGenerationUnavailable) as error:
        run(monkeypatch, quality=[verdict])
    assert str(error.value.__cause__) == 'Quality review rejected questions'


def test_quality_rejection_logs_only_bounded_failed_checks(monkeypatch, caplog):
    verdict = dict(item_index=0, demand_matches=False, assumptions_supported=True,
                   citation_complete=False, explanation_correct=True)
    with caplog.at_level('WARNING'), pytest.raises(provider.QuestionGenerationUnavailable):
        run(monkeypatch, quality=[verdict])
    assert 'stage=quality_review reason=citation_complete,demand_matches' in caplog.text
    assert TEXT not in caplog.text


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


@pytest.mark.parametrize('first,last,chapter', [(0, 4, 'cells'), (1, 0, 'cells'), (0, 0, 'unknown')])
def test_invalid_evidence_selection_is_rejected(monkeypatch, first, last, chapter):
    item = dict(prompt='Which structure releases usable energy for cellular work?',
        options=['Mitochondria', 'Membrane', 'Ribosome', 'Cell wall'], correct_index=0,
        explanation=TEXT, chapter_id=chapter, first_excerpt=first, last_excerpt=last)
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


def test_quiz_creation_regenerates_once_after_strict_review_rejection(monkeypatch, tmp_path):
    from test_mastery_loop import registered_client
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        doc = client.post('/v1/documents', headers=headers,
            files={'file': ('notes.txt', TEXT * 3)}).json()
        calls = 0

        feedback = []

        def generate(*args, **kwargs):
            nonlocal calls
            calls += 1
            feedback.append(kwargs.get('retry_feedback'))
            if calls == 1:
                try:
                    from app.document_quality import QuestionQualityRejected
                    raise QuestionQualityRejected(('citation_complete', 'demand_matches'))
                except ValueError as cause:
                    raise provider.QuestionGenerationUnavailable('rejected synthetic batch') from cause
            return [GeneratedQuestion(prompt=f'Question {index}: Which structure releases usable energy for cellular work?',
                options=['Mitochondria', 'Membrane', 'Ribosome', 'Cell wall'],
                correct_option='Mitochondria', explanation=TEXT,
                source_reference=f"{doc['chapters'][0]['title']} (source characters 0-{len(TEXT)})",
                chapter_id=doc['chapters'][0]['id'], concept='Mitochondria') for index in range(5)]

        monkeypatch.setattr('app.main.generate_document_questions', generate)
        monkeypatch.setenv('LEARNING_AI_MODE', 'openai')
        response = client.post(f"/v1/documents/{doc['id']}/quizzes", headers=headers,
            json={'chapter_ids': [doc['chapters'][0]['id']], 'question_count': 5})
        assert response.status_code == 201
        assert response.json()['question_count'] == 5
        assert calls == 2
        assert feedback == [None, 'citation_complete,demand_matches']
    finally:
        client.__exit__(None, None, None)


def test_quiz_creation_fails_closed_after_one_regeneration(monkeypatch, tmp_path):
    from test_mastery_loop import registered_client
    from app.config import get_settings
    from app.database import connection
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        doc = client.post('/v1/documents', headers=headers,
            files={'file': ('notes.txt', TEXT * 3)}).json()
        calls = 0

        def reject(*args, **kwargs):
            nonlocal calls
            calls += 1
            try:
                raise ValueError('strict review rejected questions')
            except ValueError as cause:
                raise provider.QuestionGenerationUnavailable('rejected synthetic batch') from cause

        monkeypatch.setattr('app.main.generate_document_questions', reject)
        monkeypatch.setenv('LEARNING_AI_MODE', 'openai')
        response = client.post(f"/v1/documents/{doc['id']}/quizzes", headers=headers,
            json={'chapter_ids': [doc['chapters'][0]['id']], 'question_count': 5})
        assert response.status_code == 503
        assert calls == 2
        with connection(get_settings().database_path) as db:
            assert db.execute('SELECT COUNT(*) FROM quizzes').fetchone()[0] == 0
    finally:
        client.__exit__(None, None, None)


def test_quiz_creation_does_not_repeat_transport_failure(monkeypatch, tmp_path):
    from test_mastery_loop import registered_client
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        doc = client.post('/v1/documents', headers=headers,
            files={'file': ('notes.txt', TEXT * 3)}).json()
        calls = 0

        def timeout(*args):
            nonlocal calls
            calls += 1
            try:
                raise TimeoutError('synthetic timeout')
            except TimeoutError as cause:
                raise provider.QuestionGenerationUnavailable('provider unavailable') from cause

        monkeypatch.setattr('app.main.generate_document_questions', timeout)
        monkeypatch.setenv('LEARNING_AI_MODE', 'openai')
        response = client.post(f"/v1/documents/{doc['id']}/quizzes", headers=headers,
            json={'chapter_ids': [doc['chapters'][0]['id']], 'question_count': 5})
        assert response.status_code == 503
        assert calls == 1
    finally:
        client.__exit__(None, None, None)
