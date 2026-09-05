"""Opt-in live diagnostic-bank evaluation for every exposed Grade 8 chapter."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.learning_path import CATALOG, CATALOG_VERSION
from app.tutor_provider import OpenAITutorProvider


CASES = tuple((subject.id, chapter.id, chapter.title)
              for subject in CATALOG for chapter in subject.chapters)


def evaluate_case(settings, case):
    subject, chapter, title = case
    provider = OpenAITutorProvider(settings.openai_api_key, settings.openai_model)
    provider.client = provider.client.with_options(timeout=90.0, max_retries=0)
    started = time.monotonic()
    try:
        items = provider.diagnostic_bank(8, subject, chapter)
        return {
            'subject': subject,
            'chapter': chapter,
            'title': title,
            'accepted': True,
            'item_count': len(items),
            'items': [asdict(item) for item in items],
            'elapsed_seconds': round(time.monotonic() - started, 2),
        }
    except Exception as error:
        safe = error.safe_report() if hasattr(error, 'safe_report') else [type(error).__name__]
        return {
            'subject': subject,
            'chapter': chapter,
            'title': title,
            'accepted': False,
            'failure': safe,
            'elapsed_seconds': round(time.monotonic() - started, 2),
        }
    finally:
        provider.client.close()


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true', help='Enable two metered provider requests per selected chapter without retries')
    parser.add_argument('--workers', type=int, choices=range(1, 5), default=2)
    parser.add_argument('--chapters', nargs='*', help='Optional chapter IDs for a bounded follow-up run')
    args = parser.parse_args(argv)
    if not args.live:
        parser.error('Supply --live to enable the bounded metered evaluation')
    settings = get_settings()
    if not settings.openai_api_key:
        raise SystemExit('No server API key configured')
    selected = CASES
    if args.chapters:
        requested = set(args.chapters)
        known = {chapter for _subject, chapter, _title in CASES}
        unknown = requested - known
        if unknown:
            parser.error('Unknown chapter IDs: ' + ', '.join(sorted(unknown)))
        selected = tuple(case for case in CASES if case[1] in requested)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda case: evaluate_case(settings, case), selected))
    payload = {
        'model': settings.openai_model,
        'grade': 8,
        'catalog_version': CATALOG_VERSION,
        'runtime_review_required': True,
        'educator_reviewed': False,
        'results': results,
    }
    folder = Path(__file__).resolve().parents[2] / 'artifacts'
    folder.mkdir(exist_ok=True)
    output = folder / ('catalog-diagnostic-eval-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    output.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    accepted = sum(result['accepted'] for result in results)
    print(f'CATALOG_DIAGNOSTICS={accepted}/{len(results)}')
    print(f'EVIDENCE={output}')
    return 0 if accepted == len(results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
