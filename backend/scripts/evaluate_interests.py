"""Three synthetic live cases; contract checks do not replace example review."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.mastery_service import FRACTION_DIAGNOSTIC
from app.tutor_provider import OpenAITutorProvider


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true', help='Enable three metered synthetic provider requests')
    args = parser.parse_args()
    if not args.live:
        parser.error('Supply --live to enable metered requests')
    settings = get_settings()
    if not settings.openai_api_key:
        raise SystemExit('No server API key configured')
    cases = [(0, 'sports', '1/2'), (1, 'music', '2/6'), (2, 'nature', '4/16')]

    def evaluate(case):
        index, interest, selected = case
        item = FRACTION_DIAGNOSTIC[index]
        provider = OpenAITutorProvider(settings.openai_api_key, settings.openai_model, (interest,))
        provider.client = provider.client.with_options(timeout=60.0, max_retries=0)
        try:
            lesson = provider.explain(8, item, selected)
            return {'concept': item.concept, 'interest': interest,
                    'practice_preserved': lesson.practice_prompt == item.practice_prompt,
                    'lesson': lesson.model_dump()}
        except Exception as error:
            return {'concept': item.concept, 'interest': interest, 'practice_preserved': False,
                    'error_type': type(error).__name__}
        finally:
            provider.client.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(evaluate, cases))
    print(json.dumps({'model': settings.openai_model, 'requires_human_quality_review': True,
                      'results': results}, indent=2))
    return 0 if all(result['practice_preserved'] for result in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
