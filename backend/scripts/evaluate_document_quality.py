"""Known synthetic counterexamples; not a holdout or an educator evaluation."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from openai import OpenAI
from app.config import get_settings
from app.document_quality import review_question_quality
from app.document_question_provider import Item
from evaluate_difficulty import SOURCE


def cases():
    base = dict(prompt='After Tank A drains for 10 minutes, how many whole gardens can its remaining water supply for one day?',
        options=['3 gardens', '4 gardens', '6 gardens', '2 gardens'], correct_index=0,
        explanation='Remaining water is 80 - 4 * 10 = 40 litres. Collect that remaining water at this instant; '
                    'floor(40 / 12) = 3 whole gardens can be supplied.',
        chapter_id='tanks', quote=SOURCE)
    # Explicit collection removes the continuous-drainage ambiguity.
    base['prompt'] = ('After Tank A drains for 10 minutes, all remaining water is immediately collected '
                      'without loss. How many whole gardens can this collected water supply for one day?')
    return [
        ('linked_reasoning', True, Item(**base)),
        ('incomplete_citation', False, Item(**{**base,
            'quote': 'Tank A holds 80 litres and drains at a constant 4 litres per minute.'})),
        ('wrong_explanation', False, Item(**{**base,
            'explanation': 'Remaining water is 80 - 4 * 10 = 50 litres. Dividing 50 by 12 gives 3 gardens exactly.'})),
        ('weak_hard_demand', False, Item(**{**base,
            'prompt': 'How many whole gardens can the full 15-litre bucket supply for one day?',
            'options': ['1 garden', '0 gardens', '2 gardens', '3 gardens'],
            'explanation': 'The bucket holds 15 litres and one garden needs 12 litres, so it supplies one garden.'})),
        ('ignored_drainage', False, Item(**{**base,
            'prompt': 'Tanks B and C supply one garden needing 12 litres each day. How many full days will the tanks last?',
            'options': ['12 days', '13 days', '11 days', '10 days'],
            'explanation': 'The tanks hold 60 + 90 = 150 litres. floor(150 / 12) = 12 full days.'})),
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true', help='Enable five metered synthetic quality-review requests')
    if not parser.parse_args().live:
        parser.error('Supply --live to enable metered requests')
    settings = get_settings()
    if not settings.openai_api_key:
        raise SystemExit('No server key configured')

    def evaluate(case):
        name, expected, item = case
        accepted, failure = False, None
        try:
            with OpenAI(api_key=settings.openai_api_key, timeout=30.0, max_retries=0) as client:
                review_question_quality(client, settings.openai_model, {'tanks': SOURCE}, [item], 'hard')
            accepted = True
        except ValueError as error:
            if str(error) != 'Quality review rejected questions':
                failure = type(error).__name__
        except Exception as error:
            failure = type(error).__name__
        return dict(case=name, expected_acceptance=expected, accepted=accepted,
                    operational_failure=failure, passed=failure is None and accepted == expected)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(evaluate, cases()))
    report = dict(model=settings.openai_model, known_counterexamples=True, results=results)
    folder = Path(__file__).resolve().parents[2] / 'artifacts'
    folder.mkdir(exist_ok=True)
    path = folder / ('document-quality-eval-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('Synthetic evaluation saved:', path)
    print(json.dumps(report, indent=2))
    return 0 if all(result['passed'] for result in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
