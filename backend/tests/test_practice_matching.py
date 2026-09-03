import json
from dataclasses import replace

import pytest

from app.mastery_service import FRACTION_DIAGNOSTIC, parse_diagnostic_bank, serialize_diagnostic_bank
from app.practice_matching import response_matches
from app.practice_matching import requires_exact_numeric_format
from app.fraction_practice import next_fraction_practice
from test_mastery_loop import registered_client


@pytest.mark.parametrize('prompt', ['Simplify 6/8.', 'Give lowest terms.',
    'Use denominator 6.', 'Use denominator of 12.', 'Round to 2 decimal places.',
    'Write as a mixed number.', 'Give 3 significant figures.'])
def test_explicit_format_safety_net(prompt):
    assert requires_exact_numeric_format(prompt)


@pytest.mark.parametrize('prompt', ['Find (4/7) divided by (8/21).', 'Calculate 3/4 + 1/6.'])
def test_plain_fraction_calculations_do_not_require_a_representation(prompt):
    assert not requires_exact_numeric_format(prompt)


@pytest.mark.parametrize('value,answer', [
    ('3+4', '34'), ('1 2', '12'), ('2*3', '23'), ('3^2', '32'),
    ('x+y', 'xy'), ('1,000', '1000'), ('1=2', '12'), ('3/0', '3'),
    ('0.75 kg', '0.75'), ('75%', '0.75'), ('1e3', '1000'), ('', ''),
])
@pytest.mark.parametrize('mode', ['exact', 'number'])
def test_never_erases_meaningful_content(value, answer, mode):
    assert response_matches(value, (answer,), mode)[0] is False


@pytest.mark.parametrize('value,answer', [
    ('1 3/20', '23/20'), ('-1 3/20', '-23/20'), ('+1 3/20', '1.15'),
    ('9/12', '0.75'), ('.75', '3/4'), ('0/7', '0'), ('−3 / 4', '-0.75'),
])
def test_explicit_numeric_mode_accepts_exact_rational_equivalence(value, answer):
    assert response_matches(value, (answer,), 'number')[0] is True
    assert response_matches(value, (answer,))[0] is False


@pytest.mark.parametrize('value', ['1/0', '1/-2', '1 4/3', '9' * 101, '1.2.3'])
def test_numeric_parser_rejects_invalid_or_unbounded_literals(value):
    assert response_matches(value, ('1',), 'number')[0] is False


def test_exact_preserves_requested_representation():
    assert response_matches(' 4 / 6 ', ('4/6',))[0] is True
    assert response_matches('2/3', ('4/6',))[0] is False
    assert response_matches('6/8', ('3/4',))[0] is False
    assert response_matches(' New   York ', ('new york',))[0] is True


def test_policy_persists_and_old_sessions_default_to_exact():
    encoded = serialize_diagnostic_bank(FRACTION_DIAGNOSTIC)
    assert parse_diagnostic_bank(encoded) == FRACTION_DIAGNOSTIC
    legacy = json.loads(encoded)
    for item in legacy:
        item.pop('answer_mode')
    assert all(item.answer_mode == 'exact' for item in parse_diagnostic_bank(json.dumps(legacy)))
    legacy[0]['answer_mode'] = 'anything'
    with pytest.raises(ValueError, match='answer mode'):
        parse_diagnostic_bank(json.dumps(legacy))


def test_variants_assign_policy_from_their_actual_prompt():
    for item in FRACTION_DIAGNOSTIC:
        variant = next_fraction_practice(replace(item, answer_mode='number'), 1)
        assert variant.answer_mode == ('exact' if item.concept == 'Equivalent fractions' else 'number')


@pytest.mark.parametrize('second_question,response,expected', [
    (False, '9/12', True), (False, '0.+75', False),
    (True, '2/3', False), (True, '4 / 6', True),
])
def test_http_practice_uses_persisted_answer_policy(monkeypatch, tmp_path, second_question, response, expected):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        started = client.post('/v1/mastery/diagnostics', headers=headers,
            json={'grade': 8, 'subject_id': 'math', 'chapter_id': 'fractions'})
        assert started.status_code == 201
        path = f"/v1/mastery/sessions/{started.json()['id']}"
        if second_question:
            assert client.post(path + '/diagnostic-answer', headers=headers,
                json={'selected_option': '1'}).status_code == 200
        assert client.post(path + '/diagnostic-answer', headers=headers,
            json={'selected_option': '2/6' if second_question else '1/2'}).status_code == 200
        result = client.post(path + '/practice', headers=headers, json={'response': response})
        assert result.status_code == 200
        assert result.json()['correct'] is expected
        assert result.json()['next_action'] == ('rewrite' if expected else 'more_practice')
    finally:
        client.__exit__(None, None, None)
