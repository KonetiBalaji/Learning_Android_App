from dataclasses import asdict
import json
from types import SimpleNamespace

import pytest

from app.diagnostic_quality import review_diagnostic_answers
from app.mastery_service import FRACTION_DIAGNOSTIC
from app.tutor_provider import OpenAITutorProvider, ResilientTutorProvider, DeterministicTutorProvider


def review():
    return {'items': [dict(item_index=i, answer_index=item.options.index(item.correct_option),
                          unambiguous=True, topic_matches=True, grade_suitable=True)
                      for i, item in enumerate(FRACTION_DIAGNOSTIC)]}


def fake_client(outputs, requests):
    def create(**kwargs):
        requests.append(kwargs)
        output = outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return SimpleNamespace(output_text=json.dumps(output))
    return SimpleNamespace(responses=SimpleNamespace(create=create))


def test_blind_review_does_not_receive_proposed_answers_or_teaching_support():
    requests = []
    review_diagnostic_answers(fake_client([review()], requests), 'fixture', 8, 'math', 'fractions', FRACTION_DIAGNOSTIC)
    request = requests[0]
    payload = json.loads(request['input'])
    assert payload['grade'] == 8 and payload['chapter'] == 'fractions'
    assert all(set(item) == {'item_index', 'prompt', 'options'} for item in payload['questions'])
    assert request['store'] is False
    assert request['text']['format']['strict'] is True


@pytest.mark.parametrize('field,value', [('answer_index', -1), ('answer_index', 0), ('unambiguous', False),
    ('topic_matches', False), ('grade_suitable', False), ('grade_suitable', 'true'), ('item_index', 1), ('answer_index', True)])
def test_rejects_disagreement_uncertainty_and_malformed_review(field, value):
    result = review()
    result['items'][0][field] = value
    with pytest.raises(ValueError):
        review_diagnostic_answers(fake_client([result], []), 'fixture', 8, 'math', 'fractions', FRACTION_DIAGNOSTIC)


def test_partial_review_and_outage_fail_closed():
    for result in [{'items': review()['items'][:2]}, TimeoutError('fixture outage')]:
        with pytest.raises((ValueError, TimeoutError)):
            review_diagnostic_answers(fake_client([result], []), 'fixture', 8, 'math', 'fractions', FRACTION_DIAGNOSTIC)


def test_provider_requires_review_before_returning_generated_bank():
    provider = OpenAITutorProvider.__new__(OpenAITutorProvider)
    provider.model = 'fixture'
    requests = []
    generated = {'questions': [asdict(item) for item in FRACTION_DIAGNOSTIC]}
    provider.client = fake_client([generated, review()], requests)
    assert provider.diagnostic_bank(8, 'math', 'fractions') == FRACTION_DIAGNOSTIC
    assert len(requests) == 2
    rejected = review()
    rejected['items'][0]['topic_matches'] = False
    provider.client = fake_client([generated, rejected], [])
    with pytest.raises(ValueError):
        provider.diagnostic_bank(8, 'math', 'fractions')


def test_rejected_off_topic_bank_cannot_fallback_to_fractions_for_another_chapter():
    provider = OpenAITutorProvider.__new__(OpenAITutorProvider)
    provider.model = 'fixture'
    rejected = review()
    rejected['items'][0]['topic_matches'] = False
    provider.client = fake_client([{'questions': [asdict(i) for i in FRACTION_DIAGNOSTIC]}, rejected], [])
    with pytest.raises(ValueError):
        ResilientTutorProvider(provider, DeterministicTutorProvider()).diagnostic_bank(8, 'math', 'geometry')


@pytest.mark.parametrize('accepted', [False, True])
def test_http_start_persists_only_a_reviewed_bank(monkeypatch, tmp_path, accepted):
    from test_mastery_loop import registered_client
    from app.config import get_settings
    from app.database import connection
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        provider = OpenAITutorProvider.__new__(OpenAITutorProvider)
        provider.model = 'fixture'
        result = review()
        result['items'][0]['unambiguous'] = accepted
        provider.client = fake_client([{'questions': [asdict(i) for i in FRACTION_DIAGNOSTIC]}, result], [])
        monkeypatch.setattr('app.main.tutor_provider', lambda settings: provider)
        response = client.post('/v1/mastery/diagnostics', headers=headers,
            json={'grade': 8, 'subject_id': 'math', 'chapter_id': 'fractions'})
        assert response.status_code == (201 if accepted else 422)
        with connection(get_settings().database_path) as db:
            assert db.execute('SELECT COUNT(*) FROM mastery_sessions').fetchone()[0] == int(accepted)
        if accepted:
            assert 'correct_option' not in response.text
    finally:
        client.__exit__(None, None, None)
