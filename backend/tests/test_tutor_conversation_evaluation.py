from types import SimpleNamespace

import pytest

from scripts.evaluate_tutor_conversation import CASES, evaluate


def test_contract_check_preserves_replies_for_separate_quality_review():
    values = iter(expected for _, _, expected in CASES)
    def answer(*args):
        return {'answer': 'Text that still needs quality review.', 'supported': next(values)}
    results = evaluate(SimpleNamespace(answer_question=answer))
    assert all(item['contract_passed'] for item in results)
    assert all(item['reply']['answer'] == 'Text that still needs quality review.' for item in results)
    assert all(item['elapsed_seconds'] >= 0 for item in results)


@pytest.mark.parametrize('error', [TimeoutError('private transport'), ValueError('private malformed')])
def test_outage_and_malformed_results_cannot_pass_or_leak_error_details(error):
    def fail(*args):
        raise error
    results = evaluate(SimpleNamespace(answer_question=fail))
    assert not any(item['contract_passed'] for item in results)
    assert 'private' not in str(results)


def test_wrong_scope_flag_fails_contract_check():
    results = evaluate(SimpleNamespace(answer_question=lambda *args: {'answer': 'Unreviewed response', 'supported': True}))
    assert [item['contract_passed'] for item in results] == [True, False, False]


def test_selected_cases_bound_the_provider_calls():
    calls = []
    def answer(*args):
        calls.append(args)
        return {'answer': 'Return to subject selection for that topic.', 'supported': False}
    results = evaluate(SimpleNamespace(answer_question=answer), CASES[1:])
    assert len(calls) == 2 and len(results) == 2
    assert [result['case'] for result in results] == ['off_topic', 'bypass_request']
