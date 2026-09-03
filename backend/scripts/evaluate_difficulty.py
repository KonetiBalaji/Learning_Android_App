"""Bounded live difficulty sample; automated acceptance is not a quality rating."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import get_settings
from app.document_question_provider import generate_document_questions
from app.schemas import Chapter

SOURCE = (
    'This is a synthetic water-storage exercise. All tanks start full and have no inflow. '
    'Tank A holds 80 litres and drains at a constant 4 litres per minute. '
    'Tank B holds 60 litres and drains at a constant 3 litres per minute. '
    'Tank C holds 90 litres and drains at a constant 3 litres per minute. '
    'Tank D holds 100 litres and drains at a constant 5 litres per minute. '
    'Remaining water equals starting volume minus drainage rate times elapsed minutes, until zero. '
    'Time to empty equals starting volume divided by drainage rate. '
    'A pump can transfer 2 litres per minute from a separate reservoir into a bucket. '
    'The bucket starts empty, holds 15 litres, and has no leaks. The pump stops when the bucket is full. '
    'A garden needs exactly 12 litres of water each day. Water can be divided between gardens without loss. '
    'One full container holds 6 litres. All volumes and rates in this exercise are exact. '
    'Only compare the stated quantities; the exercise provides no information about water quality or cost.'
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true', help='Enable up to eight metered synthetic requests')
    parser.add_argument('--levels', nargs='+', choices=['easy', 'medium', 'hard', 'mixed'],
                        default=['easy', 'medium', 'hard', 'mixed'])
    args = parser.parse_args()
    if not args.live:
        parser.error('Supply --live to enable metered requests')
    settings = get_settings()
    if not settings.openai_api_key:
        raise SystemExit('No server key configured')
    chapter = Chapter(id='tanks', title='Synthetic water storage', start_character=0,
                      end_character=len(SOURCE), confidence=1)

    def evaluate(level):
        try:
            items = generate_document_questions(SOURCE, [chapter], ['tanks'], 5, settings, level)
            return {'difficulty': level, 'accepted_by_existing_checks': True,
                    'questions': [asdict(item) for item in items]}
        except Exception as error:
            cause = error.__cause__
            known = {'Incorrect question count', 'Invalid choices', 'Ungrounded quote',
                     'Duplicate question', 'Independent review rejected questions'}
            return {'difficulty': level, 'accepted_by_existing_checks': False,
                    'error_type': type(error).__name__, 'cause_type': type(cause).__name__,
                    'validation_reason': str(cause) if type(cause) is ValueError and str(cause) in known else None}

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(evaluate, list(dict.fromkeys(args.levels))))
    report = {'model': settings.openai_model, 'source': SOURCE,
              'requires_content_review': True, 'results': results}
    folder = Path(__file__).resolve().parents[2] / 'artifacts'
    folder.mkdir(exist_ok=True)
    output = folder / ('difficulty-eval-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('Synthetic evaluation saved:', output)
    print(json.dumps(results, indent=2))
    return 0 if all(item['accepted_by_existing_checks'] for item in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
