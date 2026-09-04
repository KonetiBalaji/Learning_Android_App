import re
import pytest
from fractions import Fraction

from app.fraction_practice import next_fraction_practice
from app.mastery_service import FRACTION_DIAGNOSTIC, parse_diagnostic_bank
from app.config import get_settings
from app.database import connection
from test_mastery_loop import registered_client


@pytest.mark.parametrize('fresh', [False, True])
def test_rejected_rewrite_preserves_coaching_and_optionally_rotates_practice(monkeypatch, tmp_path, fresh):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        started = client.post('/v1/mastery/diagnostics', headers=headers,
            json={'grade': 8, 'subject_id': 'math', 'chapter_id': 'fractions'}).json()
        path = f"/v1/mastery/sessions/{started['id']}"
        wrong = client.post(path + '/diagnostic-answer', headers=headers, json={'selected_option': '1/2'}).json()
        correct = client.post(path + '/practice', headers=headers, json={'response': '6/8'}).json()
        body = {'response': 'I do not know', 'fresh_practice': fresh, 'expected_state': correct['state_token']}
        rejected = client.post(path + '/rewrite', headers=headers, json=body)
        assert rejected.status_code == 200
        result = rejected.json()
        assert result['understood'] is False and result['next_action'] == 'tutor'
        assert result['mastery_achieved'] is False and result['mastery_score'] == 0
        replay = client.post(path + '/rewrite', headers=headers, json=body)
        assert replay.status_code == 200 and replay.json() == result
        resumed = client.get(path, headers=headers).json()
        assert resumed['tutor']['explanation'] == result['coaching']
        if fresh:
            assert resumed['tutor'] == result['next_practice']
            assert resumed['tutor']['practice_prompt'] != wrong['tutor']['practice_prompt']
            with connection(get_settings().database_path) as db:
                bank = parse_diagnostic_bank(db.execute('SELECT questions_json FROM mastery_sessions WHERE id = ?', (started['id'],)).fetchone()[0])
                answer = bank[0].practice_answers[0]
            accepted = client.post(path + '/practice', headers=headers,
                json={'response': answer, 'fresh_practice': True, 'expected_state': result['state_token']})
            assert accepted.status_code == 200 and accepted.json()['correct'] is True
        else:
            assert result['next_practice'] is None
            assert resumed['tutor']['practice_prompt'] == wrong['tutor']['practice_prompt']
    finally:
        client.__exit__(None, None, None)


def test_fraction_variants_are_distinct_and_arithmetically_correct():
    for original in FRACTION_DIAGNOSTIC:
        prompts = set()
        for number in range(1, 31):
            item = next_fraction_practice(original, number)
            assert item.prompt == original.prompt and item.concept == original.concept
            assert item.practice_prompt not in prompts
            prompts.add(item.practice_prompt)
            terms = re.findall(r'\d+/\d+', item.practice_prompt)
            if original.concept == 'Equivalent fractions':
                assert Fraction(item.practice_answers[0]) == Fraction(terms[0])
                assert item.practice_answers[0].split('/')[1] == re.search(r'denominator (\d+)', item.practice_prompt).group(1)
            else:
                expected = Fraction(terms[0]) + Fraction(terms[1]) if ' + ' in item.practice_prompt else Fraction(terms[0]) - Fraction(terms[1])
                assert all(Fraction(answer) == expected for answer in item.practice_answers)


def test_wrong_practice_rotates_atomically_and_resume_preserves_variant(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        started = client.post('/v1/mastery/diagnostics', headers=headers,
            json={'grade': 8, 'subject_id': 'math', 'chapter_id': 'fractions'}).json()
        path = f"/v1/mastery/sessions/{started['id']}"
        wrong = client.post(path + '/diagnostic-answer', headers=headers, json={'selected_option': '1/2'}).json()
        original_prompt = wrong['tutor']['practice_prompt']
        body = {'response': 'wrong', 'fresh_practice': True, 'expected_state': wrong['state_token']}
        first = client.post(path + '/practice', headers=headers, json=body)
        assert first.status_code == 200
        result = first.json()
        assert result['correct'] is False and result['next_practice']['practice_prompt'] != original_prompt
        replay = client.post(path + '/practice', headers=headers, json=body)
        assert replay.status_code == 200 and replay.json() == result
        resumed = client.get(path, headers=headers).json()
        assert resumed['tutor']['practice_prompt'] == result['next_practice']['practice_prompt']
        with connection(get_settings().database_path) as db:
            row = db.execute('SELECT questions_json FROM mastery_sessions WHERE id = ?', (started['id'],)).fetchone()
            answer = parse_diagnostic_bank(row['questions_json'])[0].practice_answers[0]
            attempts = db.execute("SELECT prompt FROM mastery_attempts WHERE session_id = ? AND phase = 'practice'", (started['id'],)).fetchall()
            assert [row['prompt'] for row in attempts] == [original_prompt]
        correct = client.post(path + '/practice', headers=headers, json={'response': answer, 'fresh_practice': True, 'expected_state': result['state_token']})
        assert correct.status_code == 200 and correct.json()['correct'] is True
        assert correct.json()['next_practice'] is None
        assert correct.json()['next_action'] == 'rewrite'
    finally:
        client.__exit__(None, None, None)


def test_legacy_practice_request_does_not_silently_change_question(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        started = client.post('/v1/mastery/diagnostics', headers=headers,
            json={'grade': 8, 'subject_id': 'math', 'chapter_id': 'fractions'}).json()
        path = f"/v1/mastery/sessions/{started['id']}"
        wrong = client.post(path + '/diagnostic-answer', headers=headers, json={'selected_option': '1/2'}).json()
        outcome = client.post(path + '/practice', headers=headers, json={'response': 'wrong'}).json()
        assert outcome['next_practice'] is None
        assert client.get(path, headers=headers).json()['tutor']['practice_prompt'] == wrong['tutor']['practice_prompt']
    finally:
        client.__exit__(None, None, None)
