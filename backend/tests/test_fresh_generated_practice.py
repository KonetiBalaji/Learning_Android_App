import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from app.mastery_service import DiagnosticItem, FRACTION_DIAGNOSTIC
from app.tutor_provider import DeterministicTutorProvider, OpenAITutorProvider, ResilientTutorProvider
from app.tutor_provider import RewriteAssessment
from app.mastery_service import parse_diagnostic_bank, tutor_for
from app.config import get_settings
from app.database import connection
from test_mastery_loop import registered_client


SCIENCE = DiagnosticItem(
    prompt='Which organelle releases usable energy from food?',
    options=('Nucleus', 'Mitochondrion', 'Cell wall', 'Vacuole'),
    correct_option='Mitochondrion', concept='Cell organelles',
    explanation='Mitochondria release usable energy from food during cellular respiration.',
    worked_example='Active muscle cells contain many mitochondria.',
    hint='Think about the organelle associated with cellular respiration.',
    practice_prompt='Name the organelle that releases usable energy from food.',
    practice_answers=('mitochondrion',),
)


class Responses:
    def __init__(self, payloads):
        self.payloads = iter(payloads)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=json.dumps(next(self.payloads)))


def provider_with(*payloads):
    provider = OpenAITutorProvider('sk-test-placeholder', 'test-model', ('sports',))
    responses = Responses(payloads)
    provider.client = SimpleNamespace(responses=responses)
    return provider, responses


def test_general_variant_requires_blind_agreement_and_returns_reviewed_key():
    provider, responses = provider_with(
        {'practice_prompt': 'Which cell structure is the main site of cellular respiration?',
         'practice_answer': 'mitochondrion', 'hint': 'Recall where cells release usable energy.'},
        {'answers': ['Mitochondrion', 'Mitochondria'], 'valid': True, 'topic_matches': True,
         'grade_suitable': True, 'format_constraint': 'exact'},
    )
    item = provider.fresh_practice(8, 'science', 'cells', SCIENCE, 2, (SCIENCE.practice_prompt,))
    assert item.practice_prompt != SCIENCE.practice_prompt
    assert item.practice_answers == ('Mitochondrion', 'Mitochondria') and item.answer_mode == 'exact'
    generated_input, review_input = (json.loads(call['input']) for call in responses.calls)
    assert generated_input['optional_interests'] == ['sports']
    assert set(review_input) == {'grade', 'subject', 'chapter', 'concept', 'practice_prompt'}
    assert 'practice_answer' not in responses.calls[1]['input'] and 'hint' not in responses.calls[1]['input']


def test_numeric_review_accepts_equivalent_key_and_sets_number_mode():
    item = SCIENCE.__class__(**{**SCIENCE.__dict__, 'concept': 'Halves',
        'practice_prompt': 'Calculate one divided by two.', 'practice_answers': ('0.5',)})
    provider, _ = provider_with(
        {'practice_prompt': 'Calculate 3 divided by 6.', 'practice_answer': '0.5',
         'hint': 'Reduce the fraction by a common factor.'},
        {'answers': ['1/2', '0.5'], 'valid': True, 'topic_matches': True,
         'grade_suitable': True, 'format_constraint': 'none'},
    )
    generated = provider.fresh_practice(8, 'math', 'ratios', item, 1, (item.practice_prompt,))
    assert generated.practice_answers == ('1/2', '0.5') and generated.answer_mode == 'number'


@pytest.mark.parametrize('generated, reviewed, message', [
    ({'practice_prompt': SCIENCE.practice_prompt, 'practice_answer': 'mitochondrion',
      'hint': 'Think about respiration.'}, None, 'repeated'),
    ({'practice_prompt': 'Which organelle is called the powerhouse?', 'practice_answer': 'mitochondrion',
      'hint': 'Think about energy.'},
     {'answers': ['mitochondrion'], 'valid': False, 'topic_matches': True,
      'grade_suitable': True, 'format_constraint': 'exact'}, 'independent review'),
    ({'practice_prompt': 'Which organelle is called the powerhouse?', 'practice_answer': 'nucleus',
      'hint': 'Think about energy.'},
     {'answers': ['mitochondrion'], 'valid': True, 'topic_matches': True,
      'grade_suitable': True, 'format_constraint': 'exact'}, 'disagreed'),
    ({'practice_prompt': 'Which organelle is called the powerhouse?', 'practice_answer': 'mitochondrion',
      'hint': 'The answer is mitochondrion.'},
     {'answers': ['mitochondrion'], 'valid': True, 'topic_matches': True,
      'grade_suitable': True, 'format_constraint': 'exact'}, 'revealed'),
])
def test_unsafe_generated_practice_is_rejected(generated, reviewed, message):
    provider, _ = provider_with(*([generated] if reviewed is None else [generated, reviewed]))
    with pytest.raises(ValueError, match=message):
        provider.fresh_practice(8, 'science', 'cells', SCIENCE, 1, (SCIENCE.practice_prompt,))


class Primary:
    name = 'openai'
    def fresh_practice(self, *args):
        raise AssertionError('primary should not replace deterministic fraction variants')


def test_resilient_provider_preserves_deterministic_fractions():
    provider = ResilientTutorProvider(Primary(), DeterministicTutorProvider())
    generated = provider.fresh_practice(8, 'math', 'fractions', FRACTION_DIAGNOSTIC[0], 3,
                                        (FRACTION_DIAGNOSTIC[0].practice_prompt,))
    assert generated is not None and generated.practice_prompt != FRACTION_DIAGNOSTIC[0].practice_prompt


def test_non_fraction_generation_outage_keeps_current_question():
    provider = ResilientTutorProvider(Primary(), DeterministicTutorProvider())
    assert provider.fresh_practice(8, 'science', 'cells', SCIENCE, 3,
                                   (SCIENCE.practice_prompt,)) is None


def test_non_fraction_http_flow_persists_reviewed_fresh_practice(monkeypatch, tmp_path):
    bank = tuple(replace(SCIENCE, prompt=f'Cell organelle question {index}?',
                         practice_prompt=f'Original cell practice {index}?') for index in range(3))

    class Provider:
        name = 'reviewed-test-provider'
        def diagnostic_bank(self, grade, subject_id, chapter_id): return bank
        def explain(self, grade, item, selected_option): return tutor_for(item)
        def assess_rewrite(self, grade, item, response): return RewriteAssessment(understood=False)
        def fresh_practice(self, grade, subject_id, chapter_id, item, round_number, previous_prompts):
            assert (grade, subject_id, chapter_id, round_number) == (8, 'science', 'cells', 1)
            assert previous_prompts == (item.practice_prompt,)
            return replace(item, practice_prompt='Which organelle is the main site of cellular respiration?',
                           practice_answers=('Mitochondrion',), hint='Think about usable energy.')

    import app.main as api
    monkeypatch.setattr(api, 'tutor_provider', lambda settings, interests=(): Provider())
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        started = client.post('/v1/mastery/diagnostics', headers=headers,
            json={'grade': 8, 'subject_id': 'science', 'chapter_id': 'cells'}).json()
        path = f"/v1/mastery/sessions/{started['id']}"
        wrong = client.post(path + '/diagnostic-answer', headers=headers,
            json={'selected_option': 'Nucleus'}).json()
        result = client.post(path + '/practice', headers=headers, json={
            'response': 'wrong', 'fresh_practice': True,
            'expected_state': wrong['state_token'],
        })
        assert result.status_code == 200
        assert result.json()['next_practice']['practice_prompt'].startswith('Which organelle')
        resumed = client.get(path, headers=headers).json()
        assert resumed['tutor'] == result.json()['next_practice']
        with connection(get_settings().database_path) as db:
            saved = parse_diagnostic_bank(db.execute(
                'SELECT questions_json FROM mastery_sessions WHERE id = ?', (started['id'],)).fetchone()[0])[0]
            attempts = db.execute(
                "SELECT prompt FROM mastery_attempts WHERE session_id = ? AND phase = 'practice'", (started['id'],)).fetchall()
        assert saved.practice_answers == ('Mitochondrion',)
        assert [row['prompt'] for row in attempts] == [bank[0].practice_prompt]
    finally:
        client.__exit__(None, None, None)
