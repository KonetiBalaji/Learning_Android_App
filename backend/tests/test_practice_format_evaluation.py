from types import SimpleNamespace

import pytest

from scripts.evaluate_practice_format import evaluate
from test_diagnostic_quality import fake_client, review


def format_review():
    result = review()
    result['items'][0].update(practice_answer='3/2', practice_format_constraint='none')
    result['items'][2].update(practice_answer='3/4', practice_format_constraint='simplest_terms')
    return result


def test_live_fixture_checks_numeric_acceptance_and_targeted_constraint_rejection():
    provider = SimpleNamespace(model='fixture', client=fake_client([format_review(), format_review()], []))
    results = evaluate(provider)
    assert all(result['passed'] for result in results)
    assert results[0]['answer_checks'] == [True, False, False]


@pytest.mark.parametrize('error', [TimeoutError('private transport'), ValueError('private malformed')])
def test_live_fixture_cannot_pass_on_outage_or_malformed_output(error):
    results = evaluate(SimpleNamespace(model='fixture', client=fake_client([error, error], [])))
    assert not any(result['passed'] for result in results)
    assert 'private' not in str(results)


def test_server_safeguard_preserves_lowest_terms_despite_reviewer_omission():
    bad = format_review()
    bad['items'][2]['practice_format_constraint'] = 'none'
    results = evaluate(SimpleNamespace(model='fixture', client=fake_client([bad, bad], [])))
    assert all(result['passed'] for result in results)
