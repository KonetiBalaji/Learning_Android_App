"""Small explicit live smoke: generated Grade 8 bank plus a deliberately wrong key."""
import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.diagnostic_quality import DiagnosticReviewRejected, ReviewFailure, review_diagnostic_answers
from app.mastery_service import FRACTION_DIAGNOSTIC
from app.tutor_provider import OpenAITutorProvider


def evaluate(provider):
    results = []
    start = time.monotonic()
    try:
        items = provider.diagnostic_bank(8, 'math', 'fractions')
        results.append({'case': 'generated_grade8_fractions', 'passed': True,
                        'questions': [asdict(item) for item in items]})
    except DiagnosticReviewRejected as error:
        results.append({'case': 'generated_grade8_fractions', 'passed': False,
                        'error_type': type(error).__name__, 'review_issues': error.safe_report()})
    except Exception as error:
        results.append({'case': 'generated_grade8_fractions', 'passed': False, 'error_type': type(error).__name__})
    results[-1]['elapsed_seconds'] = round(time.monotonic() - start, 2)
    # 3/4 + 1/4 is 1, not 3/8. Preserve valid schema while corrupting only the key.
    wrong = (replace(FRACTION_DIAGNOSTIC[0], correct_option='3/8'), *FRACTION_DIAGNOSTIC[1:])
    start = time.monotonic()
    try:
        review_diagnostic_answers(provider.client, provider.model, 8, 'math', 'fractions', wrong)
        result = {'case': 'incorrect_fraction_key', 'passed': False, 'outcome': 'incorrect_key_accepted'}
    except DiagnosticReviewRejected as error:
        issues = error.safe_report()
        detected = {'code': ReviewFailure.KEY.value, 'item_index': 0} in issues
        result = {'case': 'incorrect_fraction_key', 'passed': detected,
                  'outcome': 'corrupted_key_detected' if detected else 'unrelated_review_rejection',
                  'review_issues': issues}
    except Exception as error:
        result = {'case': 'incorrect_fraction_key', 'passed': False, 'error_type': type(error).__name__}
    result['elapsed_seconds'] = round(time.monotonic() - start, 2)
    results.append(result)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true', help='Allow up to three metered requests, no retries')
    args = parser.parse_args()
    if not args.live:
        parser.error('Supply --live to authorize the bounded metered smoke check')
    settings = get_settings()
    if not settings.openai_api_key:
        raise SystemExit('No server API key configured')
    provider = OpenAITutorProvider(settings.openai_api_key, settings.openai_model)
    provider.client = provider.client.with_options(timeout=60.0, max_retries=0)
    try:
        results = evaluate(provider)
    finally:
        provider.client.close()
    print(json.dumps({'model': settings.openai_model, 'grade': 8,
        'requires_human_quality_review': True, 'results': results}, indent=2))
    return 0 if all(result['passed'] for result in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
