"""Metered cross-subject evaluation of generated and independently reviewed lessons."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.mastery_service import DiagnosticItem
from app.tutor_provider import OpenAITutorProvider


CASES = (
    ('math', 'sports', '9', DiagnosticItem(
        'Solve 3(x + 2) = 21.', ('3', '5', '7', '9'), '5', 'Solving linear equations',
        'Divide both sides by 3 to get x + 2 = 7, then subtract 2, so x = 5.',
        'For 2(y + 1) = 10, divide by 2 and subtract 1 to get y = 4.',
        'Undo multiplication before undoing addition.', 'Solve 4(z + 1) = 20.', ('4',), 'number')),
    ('science', 'nature', 'Cell wall', DiagnosticItem(
        'Which organelle releases usable energy from food?',
        ('Nucleus', 'Mitochondrion', 'Cell wall', 'Ribosome'), 'Mitochondrion',
        'Mitochondria and cellular respiration',
        'Mitochondria release usable energy through cellular respiration; a cell wall provides support.',
        'Muscle cells need usable energy and contain many mitochondria.',
        'Match each organelle to its job.', 'Which organelle builds proteins?', ('Ribosome',), 'exact')),
    ('english', 'music', 'Object', DiagnosticItem(
        'In “The careful musician tuned the guitar,” which words form the subject?',
        ('The careful musician', 'tuned', 'the guitar', 'musician tuned'), 'The careful musician',
        'Subjects and predicates',
        'The complete subject names who performs the action: “The careful musician.”',
        'In “The young artist painted a mural,” “The young artist” is the complete subject.',
        'Ask who or what performs the verb.',
        'Name the complete subject in “A bright star appeared.”', ('A bright star',), 'exact')),
    ('social', 'travel', 'Prime Meridian', DiagnosticItem(
        'Which reference line is 0 degrees latitude?',
        ('Equator', 'Prime Meridian', 'Tropic of Cancer', 'Arctic Circle'), 'Equator',
        'Latitude and longitude reference lines',
        'The Equator is 0 degrees latitude; the Prime Meridian is 0 degrees longitude.',
        'A location at 15 degrees north is measured north of the Equator.',
        'Decide whether the coordinate measures north/south or east/west.',
        'Which reference line is 0 degrees longitude?', ('Prime Meridian',), 'exact')),
)


def evaluate_case(settings, case):
    subject, interest, selected, item = case
    provider = OpenAITutorProvider(settings.openai_api_key, settings.openai_model, (interest,))
    provider.client = provider.client.with_options(timeout=60.0, max_retries=0)
    try:
        lesson = provider.explain(8, item, selected)
        return {'subject': subject, 'concept': item.concept, 'interest': interest,
                'practice_preserved': lesson.practice_prompt == item.practice_prompt,
                'lesson': lesson.model_dump()}
    except Exception as error:
        safe = error.safe_report() if hasattr(error, 'safe_report') else [type(error).__name__]
        result = {'subject': subject, 'concept': item.concept, 'interest': interest,
                  'practice_preserved': False, 'review_failure': safe}
        if getattr(error, 'lesson', None) is not None:
            result['rejected_lesson'] = error.lesson.model_dump()
        return result
    finally:
        provider.client.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true', help='Enable eight metered provider calls')
    args = parser.parse_args()
    if not args.live:
        parser.error('Supply --live to enable metered provider requests')
    settings = get_settings()
    if not settings.openai_api_key:
        raise SystemExit('No server API key configured')
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda case: evaluate_case(settings, case), CASES))
    print(json.dumps({'model': settings.openai_model, 'grade': 8,
                      'independent_runtime_review_required': True, 'results': results}, indent=2))
    return 0 if all(result['practice_preserved'] for result in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
