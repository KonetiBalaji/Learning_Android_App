"""Opt-in two-call live regression for equivalent values versus required forms."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.diagnostic_quality import DiagnosticReviewRejected, review_diagnostic_answers
from app.mastery_service import FRACTION_DIAGNOSTIC
from app.practice_matching import response_matches
from app.tutor_provider import OpenAITutorProvider


def evaluate(provider):
    items = (
        replace(FRACTION_DIAGNOSTIC[0], practice_prompt='Find (4/7) divided by (8/21).',
                practice_answers=('3/2', '1 1/2')),
        FRACTION_DIAGNOSTIC[1],
        replace(FRACTION_DIAGNOSTIC[2], practice_prompt='Simplify 6/8 to lowest terms.', practice_answers=('3/4',)),
    )
    results = []
    try:
        reviewed = review_diagnostic_answers(provider.client, provider.model, 8, 'math', 'fractions', items)
        modes = [item.answer_mode for item in reviewed]
        checks = [response_matches(value, item.practice_answers, item.answer_mode)[0]
                  for item, value in zip(reviewed, ('1.5', '2/3', '6/8'))]
        results.append({'case': 'format_constraints', 'passed': modes == ['number', 'exact', 'exact']
                        and checks == [True, False, False], 'modes': modes, 'answer_checks': checks})
    except Exception as error:
        results.append({'case': 'format_constraints', 'passed': False, 'error_type': type(error).__name__})
        if isinstance(error, DiagnosticReviewRejected):
            results[-1]['review_issues'] = error.safe_report()
    invalid = (*items[:2], replace(items[2], practice_answers=('6/8',)))
    try:
        review_diagnostic_answers(provider.client, provider.model, 8, 'math', 'fractions', invalid)
        results.append({'case': 'unsimplified_key', 'passed': False})
    except DiagnosticReviewRejected as error:
        issues = error.safe_report()
        results.append({'case': 'unsimplified_key', 'passed':
                        {'code': 'practice_key_disagreement', 'item_index': 2} in issues,
                        'review_issues': issues})
    except Exception as error:
        results.append({'case': 'unsimplified_key', 'passed': False, 'error_type': type(error).__name__})
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true', help='Allow two metered review requests without retries')
    if not parser.parse_args().live:
        parser.error('Supply --live to authorize the bounded metered check')
    settings = get_settings()
    if not settings.openai_api_key:
        raise SystemExit('No server API key configured')
    provider = OpenAITutorProvider(settings.openai_api_key, settings.openai_model)
    provider.client = provider.client.with_options(max_retries=0)
    try:
        results = evaluate(provider)
    finally:
        provider.client.close()
    print(json.dumps({'model': provider.model, 'results': results, 'requires_human_quality_review': True}, indent=2))
    return 0 if all(result['passed'] for result in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
