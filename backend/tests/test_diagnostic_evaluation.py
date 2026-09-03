from types import SimpleNamespace

import pytest

from app.diagnostic_quality import DiagnosticReviewRejected, ReviewIssue, ReviewFailure
from app.mastery_service import FRACTION_DIAGNOSTIC
from scripts.evaluate_diagnostic import evaluate


@pytest.mark.parametrize('error,passed', [(DiagnosticReviewRejected('rejected'), False),
    (DiagnosticReviewRejected(issues=[ReviewIssue(ReviewFailure.KEY, 0)]), True),
    (DiagnosticReviewRejected(issues=[ReviewIssue(ReviewFailure.KEY, 1)]), False),
    (DiagnosticReviewRejected(issues=[ReviewIssue(ReviewFailure.PRACTICE_KEY, 0)]), False),
    (DiagnosticReviewRejected(issues=[ReviewIssue(ReviewFailure.UNSOLVED, 0)]), False),
    (ValueError('malformed'), False), (TimeoutError('unavailable'), False), (None, False)])
def test_live_eval_does_not_count_outages_or_malformed_outputs_as_correct_rejection(monkeypatch, error, passed):
    def review(client, model, grade, subject, chapter, items):
        assert items[0].correct_option == '3/8'
        assert items[0].prompt == FRACTION_DIAGNOSTIC[0].prompt
        if error:
            raise error
    monkeypatch.setattr('scripts.evaluate_diagnostic.review_diagnostic_answers', review)
    provider = SimpleNamespace(client=None, model='fixture', diagnostic_bank=lambda *args: FRACTION_DIAGNOSTIC)
    results = evaluate(provider)
    assert results[0]['passed'] is True
    assert results[1]['passed'] is passed
    assert all(result['elapsed_seconds'] >= 0 for result in results)


def test_generation_exception_is_redacted_and_never_counts_as_success(monkeypatch):
    def fail(*args):
        raise RuntimeError('private transport details')
    monkeypatch.setattr('scripts.evaluate_diagnostic.review_diagnostic_answers', fail)
    result = evaluate(SimpleNamespace(client=None, model='fixture', diagnostic_bank=fail))
    assert all(not item['passed'] for item in result)
    assert all(item['error_type'] == 'RuntimeError' for item in result)
    assert 'private' not in str(result)


def test_safe_report_never_emits_exception_text_or_unrecognized_codes(monkeypatch):
    def fail(*args):
        raise DiagnosticReviewRejected('private content', issues=[
            ReviewIssue(ReviewFailure.PRACTICE_KEY, 2), ReviewIssue('private content', 0),
            ReviewIssue(ReviewFailure.KEY, 1000), ReviewIssue(ReviewFailure.KEY, True)])
    monkeypatch.setattr('scripts.evaluate_diagnostic.review_diagnostic_answers', fail)
    results = evaluate(SimpleNamespace(client=None, model='fixture', diagnostic_bank=fail))
    assert results[0]['review_issues'] == [{'code': 'practice_key_disagreement', 'item_index': 2}]
    assert 'private' not in str(results)
    assert not results[1]['passed']
