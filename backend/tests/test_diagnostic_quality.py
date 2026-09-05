from dataclasses import asdict, replace
import json
from types import SimpleNamespace

import pytest

from app.diagnostic_quality import review_diagnostic_answers, DiagnosticReviewRejected
from app.mastery_service import FRACTION_DIAGNOSTIC
from app.tutor_provider import OpenAITutorProvider, ResilientTutorProvider, DeterministicTutorProvider


def review():
    return {'items': [dict(item_index=i, answer_index=item.options.index(item.correct_option),
                          unambiguous=True, topic_matches=True, grade_suitable=True,
                          practice_answers=list(item.practice_answers), practice_valid=True,
                          practice_concept_matches=True,
                          explanation_accurate=True, worked_example_accurate=True,
                          hint_valid=True, teaching_grade_suitable=True, teaching_source_bounded=True,
                          practice_format_constraint='none' if item.answer_mode == 'number' else 'denominator')
                      for i, item in enumerate(FRACTION_DIAGNOSTIC)]}


def generated_bank():
    # Matching policy belongs to trusted server content, not the model schema.
    questions = [{key: value for key, value in asdict(item).items()
                  if key != 'answer_mode'} for item in FRACTION_DIAGNOSTIC]
    for question in questions:
        question['practice_answers'] = question['practice_answers'][:1]
    return {'questions': questions}


def fake_client(outputs, requests):
    def create(**kwargs):
        requests.append(kwargs)
        output = outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return SimpleNamespace(output_text=json.dumps(output))
    return SimpleNamespace(responses=SimpleNamespace(create=create))


def test_blind_review_hides_keys_but_independently_checks_teaching_support():
    requests = []
    review_diagnostic_answers(fake_client([review()], requests), 'fixture', 8, 'math', 'fractions', FRACTION_DIAGNOSTIC)
    request = requests[0]
    payload = json.loads(request['input'])
    assert payload['grade'] == 8 and payload['chapter'] == 'fractions'
    assert all(set(item) == {'item_index', 'prompt', 'options', 'concept', 'practice_prompt',
                             'explanation', 'worked_example', 'hint'} for item in payload['questions'])
    assert all('correct_option' not in item and 'practice_answers' not in item for item in payload['questions'])
    assert request['store'] is False
    assert request['text']['format']['strict'] is True


@pytest.mark.parametrize('field,value', [('answer_index', -1), ('answer_index', 0), ('unambiguous', False),
    ('topic_matches', False), ('grade_suitable', False), ('grade_suitable', 'true'), ('item_index', 1), ('answer_index', True),
    ('explanation_accurate', False), ('worked_example_accurate', False), ('hint_valid', False),
    ('teaching_grade_suitable', False), ('teaching_source_bounded', False),
    ('practice_concept_matches', False)])
def test_rejects_disagreement_uncertainty_and_malformed_review(field, value):
    result = review()
    result['items'][0][field] = value
    with pytest.raises(ValueError):
        review_diagnostic_answers(fake_client([result], []), 'fixture', 8, 'math', 'fractions', FRACTION_DIAGNOSTIC)


def test_partial_review_and_outage_fail_closed():
    for result in [{'items': review()['items'][:2]}, TimeoutError('fixture outage')]:
        with pytest.raises((ValueError, TimeoutError)):
            review_diagnostic_answers(fake_client([result], []), 'fixture', 8, 'math', 'fractions', FRACTION_DIAGNOSTIC)


@pytest.mark.parametrize('field,value', [('practice_answers', ['2/7']),
    ('practice_valid', False), ('practice_valid', 'true'), ('practice_format_constraint', 'anything'),
    ('practice_answers', []), ('practice_answers', ['three quarters'])])
def test_practice_review_rejects_disagreement_invalid_policy_and_unparseable_number(field, value):
    result = review()
    result['items'][0][field] = value
    with pytest.raises(ValueError):
        review_diagnostic_answers(fake_client([result], []), 'fixture', 8, 'math', 'fractions', FRACTION_DIAGNOSTIC)


def test_reviewed_answers_replace_untrusted_extra_generated_keys():
    items = (replace(FRACTION_DIAGNOSTIC[0], practice_answers=('3/4', '3+4')), *FRACTION_DIAGNOSTIC[1:])
    reviewed = review_diagnostic_answers(fake_client([review()], []), 'fixture', 8, 'math', 'fractions', items)
    assert reviewed[0].practice_answers == FRACTION_DIAGNOSTIC[0].practice_answers
    assert '3+4' not in reviewed[0].practice_answers


def test_review_reports_all_fixed_reasons_without_raw_content():
    result = review()
    result['items'][0].update(answer_index=0, practice_valid=False)
    result['items'][1].update(practice_answers=['private wrong answer'])
    with pytest.raises(DiagnosticReviewRejected) as caught:
        review_diagnostic_answers(fake_client([result], []), 'fixture', 8, 'math', 'fractions', FRACTION_DIAGNOSTIC)
    assert caught.value.safe_report() == [
        {'code': 'diagnostic_key_disagreement', 'item_index': 0},
        {'code': 'practice_invalid', 'item_index': 0},
        {'code': 'practice_key_disagreement', 'item_index': 1}]
    assert 'private' not in str(caught.value.safe_report())


def test_misordered_and_unsolved_reviews_do_not_establish_key_disagreement():
    result = review()
    result['items'][0].update(item_index=2, answer_index=0)
    result['items'][1].update(answer_index=-1)
    with pytest.raises(DiagnosticReviewRejected) as caught:
        review_diagnostic_answers(fake_client([result], []), 'fixture', 8, 'math', 'fractions', FRACTION_DIAGNOSTIC)
    assert caught.value.safe_report() == [
        {'code': 'review_order', 'item_index': 0}, {'code': 'diagnostic_unsolved', 'item_index': 1}]


def test_requested_denominator_cannot_be_replaced_by_equivalent_simplified_key():
    items = (FRACTION_DIAGNOSTIC[0], replace(FRACTION_DIAGNOSTIC[1], practice_answers=('2/3',)), FRACTION_DIAGNOSTIC[2])
    with pytest.raises(ValueError, match='Practice answer review'):
        review_diagnostic_answers(fake_client([review()], []), 'fixture', 8, 'math', 'fractions', items)


@pytest.mark.parametrize('constraint', ['simplest_terms', 'denominator', 'representation',
    'units_or_percent', 'named_choice', 'text', 'other'])
def test_explicit_format_constraints_never_opt_into_numeric_equivalence(constraint):
    result = review()
    result['items'][0].update(practice_answers=['3/4'], practice_format_constraint=constraint)
    items = (replace(FRACTION_DIAGNOSTIC[0], practice_answers=('6/8',)), *FRACTION_DIAGNOSTIC[1:])
    with pytest.raises(DiagnosticReviewRejected):
        review_diagnostic_answers(fake_client([result], []), 'fixture', 8, 'math', 'fractions', items)


def test_observed_division_regression_accepts_both_proposed_representations():
    result = review()
    result['items'][0].update(practice_answers=['3/2', '1 1/2'], practice_format_constraint='none')
    items = (replace(FRACTION_DIAGNOSTIC[0], practice_prompt='Find (4/7) divided by (8/21).',
                     practice_answers=('3/2', '1 1/2')), *FRACTION_DIAGNOSTIC[1:])
    reviewed = review_diagnostic_answers(fake_client([result], []), 'fixture', 8, 'math', 'fractions', items)
    assert reviewed[0].answer_mode == 'number'


def test_nonnumeric_review_answers_override_an_observed_none_misclassification():
    result = review()
    result['items'][0].update(practice_answers=['Mitochondrion', 'Mitochondria'],
                              practice_format_constraint='none')
    items = (replace(FRACTION_DIAGNOSTIC[0],
                     practice_prompt='Name the organelle that releases usable energy from food.',
                     practice_answers=('Mitochondrion',)), *FRACTION_DIAGNOSTIC[1:])
    reviewed = review_diagnostic_answers(fake_client([result], []), 'fixture', 8, 'science', 'cells', items)
    assert reviewed[0].answer_mode == 'exact'
    assert reviewed[0].practice_answers == ('Mitochondrion', 'Mitochondria')


def test_denominator_guard_overrides_observed_reviewer_omission():
    result = review()
    result['items'][1]['practice_format_constraint'] = 'none'
    bank = review_diagnostic_answers(fake_client([result], []), 'fixture', 8, 'math', 'fractions', FRACTION_DIAGNOSTIC)
    assert bank[1].answer_mode == 'exact'
    invalid = (FRACTION_DIAGNOSTIC[0], replace(FRACTION_DIAGNOSTIC[1], practice_answers=('2/3',)), FRACTION_DIAGNOSTIC[2])
    with pytest.raises(DiagnosticReviewRejected):
        review_diagnostic_answers(fake_client([result], []), 'fixture', 8, 'math', 'fractions', invalid)


def test_numeric_review_accepts_mixed_answer_but_simplest_terms_remains_exact():
    from app.practice_matching import response_matches
    items = (replace(FRACTION_DIAGNOSTIC[0], practice_prompt='Compute 3/4 + 2/5.',
                     practice_answers=('23/20',)), *FRACTION_DIAGNOSTIC[1:])
    result = review()
    result['items'][0]['practice_answers'] = ['1 3/20', '23/20']
    bank = review_diagnostic_answers(fake_client([result], []), 'fixture', 8, 'math', 'fractions', items)
    assert response_matches('1.15', bank[0].practice_answers, bank[0].answer_mode)[0]
    simplified = (replace(items[0], practice_prompt='Simplify 6/8 to lowest terms.', practice_answers=('3/4',)), *items[1:])
    result['items'][0].update(practice_answers=['3/4'], practice_format_constraint='simplest_terms')
    bank = review_diagnostic_answers(fake_client([result], []), 'fixture', 8, 'math', 'fractions', simplified)
    assert not response_matches('6/8', bank[0].practice_answers, bank[0].answer_mode)[0]


def test_provider_requires_review_before_returning_generated_bank():
    provider = OpenAITutorProvider.__new__(OpenAITutorProvider)
    provider.model = 'fixture'
    requests = []
    generated = generated_bank()
    provider.client = fake_client([generated, review()], requests)
    assert provider.diagnostic_bank(8, 'math', 'fractions') == FRACTION_DIAGNOSTIC
    assert len(requests) == 2
    rejected = review()
    rejected['items'][0]['topic_matches'] = False
    provider.client = fake_client([generated, rejected], [])
    with pytest.raises(ValueError):
        provider.diagnostic_bank(8, 'math', 'fractions')


def test_generation_prompt_requires_self_solved_source_bounded_teaching():
    provider = OpenAITutorProvider.__new__(OpenAITutorProvider)
    provider.model = 'fixture'
    requests = []
    provider.client = fake_client([generated_bank(), review()], requests)
    provider.diagnostic_bank(8, 'math', 'fractions')
    instructions = requests[0]['instructions']
    assert 'independently solve every question and practice prompt' in instructions
    assert 'every factual premise needed to solve a question' in instructions
    assert 'strictly to those premises and the verified solution' in instructions
    assert 'self-contained parallel problem' in instructions


def test_model_cannot_opt_itself_into_numeric_grading():
    provider = OpenAITutorProvider.__new__(OpenAITutorProvider)
    provider.model = 'fixture'
    generated = generated_bank()
    generated['questions'][0]['answer_mode'] = 'number'
    provider.client = fake_client([generated], [])
    with pytest.raises(ValueError):
        provider.diagnostic_bank(8, 'math', 'fractions')


@pytest.mark.parametrize('prompt', [
    'Draw and label one organelle.',
    'Write one sentence explaining respiration.',
    'Name any example of a cell organelle.',
])
def test_generated_diagnostic_rejects_non_objective_app_practice(prompt):
    provider = OpenAITutorProvider.__new__(OpenAITutorProvider)
    provider.model = 'fixture'
    generated = generated_bank()
    generated['questions'][0]['practice_prompt'] = prompt
    provider.client = fake_client([generated], [])
    with pytest.raises(ValueError, match='objective text answer'):
        provider.diagnostic_bank(8, 'science', 'cells')


def test_rejected_off_topic_bank_uses_only_the_matching_curated_chapter():
    provider = OpenAITutorProvider.__new__(OpenAITutorProvider)
    provider.model = 'fixture'
    rejected = review()
    rejected['items'][0]['topic_matches'] = False
    provider.client = fake_client([generated_bank(), rejected], [])
    fallback = ResilientTutorProvider(provider, DeterministicTutorProvider()).diagnostic_bank(8, 'math', 'geometry')
    assert fallback[0].concept == 'Triangle angle sum'
    assert fallback != FRACTION_DIAGNOSTIC


@pytest.mark.parametrize('accepted', [False, True])
@pytest.mark.parametrize('review_field', ['unambiguous', 'practice_valid'])
def test_http_start_persists_only_a_reviewed_bank(monkeypatch, tmp_path, accepted, review_field):
    from test_mastery_loop import registered_client
    from app.config import get_settings
    from app.database import connection
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        provider = OpenAITutorProvider.__new__(OpenAITutorProvider)
        provider.model = 'fixture'
        result = review()
        result['items'][0][review_field] = accepted
        provider.client = fake_client([generated_bank(), result], [])
        monkeypatch.setattr('app.main.tutor_provider', lambda settings: provider)
        response = client.post('/v1/mastery/diagnostics', headers=headers,
            json={'grade': 8, 'subject_id': 'math', 'chapter_id': 'fractions'})
        assert response.status_code == (201 if accepted else 422)
        with connection(get_settings().database_path) as db:
            assert db.execute('SELECT COUNT(*) FROM mastery_sessions').fetchone()[0] == int(accepted)
            if accepted:
                from app.mastery_service import parse_diagnostic_bank
                saved = parse_diagnostic_bank(db.execute('SELECT questions_json FROM mastery_sessions').fetchone()[0])
                assert [item.answer_mode for item in saved] == ['number', 'exact', 'number']
        if accepted:
            assert 'correct_option' not in response.text
    finally:
        client.__exit__(None, None, None)


def test_reviewed_provider_failure_uses_matching_curated_fallback(monkeypatch, tmp_path):
    from test_mastery_loop import registered_client
    from app.config import get_settings
    from app.database import connection
    provider = OpenAITutorProvider.__new__(OpenAITutorProvider)
    provider.model = 'fixture'
    rejected = review()
    rejected['items'][0]['topic_matches'] = False
    provider.client = fake_client([generated_bank(), rejected], [])
    resilient = ResilientTutorProvider(provider, DeterministicTutorProvider())
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        monkeypatch.setattr('app.main.tutor_provider', lambda settings: resilient)
        response = client.post('/v1/mastery/diagnostics', headers=headers,
            json={'grade': 8, 'subject_id': 'science', 'chapter_id': 'cells'})
        assert response.status_code == 201
        assert response.json()['question']['concept'] == 'Cell membrane function'
        with connection(get_settings().database_path) as db:
            saved = db.execute('SELECT subject_id, chapter_id FROM mastery_sessions').fetchone()
            assert tuple(saved) == ('science', 'cells')
    finally:
        client.__exit__(None, None, None)
