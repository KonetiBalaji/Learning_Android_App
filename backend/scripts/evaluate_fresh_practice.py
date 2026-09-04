"""Narrow live smoke for reviewed non-Fractions practice; never prints credentials."""
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.mastery_service import DiagnosticItem
from app.tutor_provider import OpenAITutorProvider


CASES = (
    ('science', 'cells', DiagnosticItem(
        prompt='Which organelle releases usable energy from food?',
        options=('Nucleus', 'Mitochondrion', 'Cell wall', 'Vacuole'),
        correct_option='Mitochondrion', concept='Cell organelles',
        explanation='Mitochondria release usable energy from food during cellular respiration.',
        worked_example='Active muscle cells contain many mitochondria.',
        hint='Connect cellular respiration with the organelle where it occurs.',
        practice_prompt='Name the organelle where cellular respiration releases usable energy.',
        practice_answers=('mitochondrion',),
    )),
    ('english', 'grammar', DiagnosticItem(
        prompt='Choose the verb that agrees: The basket of apples ___ on the table.',
        options=('sit', 'sits', 'are sitting', 'have sat'), correct_option='sits',
        concept='Subject-verb agreement',
        explanation='A singular subject takes a singular present-tense verb. The subject is basket, not apples.',
        worked_example='The box of pencils belongs on the shelf.',
        hint='Find the main subject before choosing the verb.',
        practice_prompt='Complete with the agreeing verb: The group of students ___ quietly. (work/works)',
        practice_answers=('works',),
    )),
)


def main():
    settings = get_settings()
    if not settings.openai_api_key:
        raise SystemExit('No usable OPENAI_API_KEY is configured')
    provider = OpenAITutorProvider(settings.openai_api_key, settings.openai_model)
    results = []
    for subject, chapter, item in CASES:
        captured = []
        delegate = provider.client.responses

        class RecordingResponses:
            def create(self, **kwargs):
                response = delegate.create(**kwargs)
                captured.append(json.loads(response.output_text))
                return response

        provider.client.responses = RecordingResponses()
        started = time.monotonic()
        try:
            generated = provider.fresh_practice(8, subject, chapter, item, 2, (item.practice_prompt,))
        except Exception as failure:
            results.append({'subject': subject, 'chapter': chapter, 'accepted': False,
                            'reason': type(failure).__name__, 'structured_outputs': captured,
                            'elapsed_seconds': round(time.monotonic() - started, 2)})
            provider.client.responses = delegate
            continue
        provider.client.responses = delegate
        results.append({
            'subject': subject,
            'chapter': chapter,
            'accepted': True,
            'practice_prompt': generated.practice_prompt,
            'hint': generated.hint,
            'reviewed_answer': generated.practice_answers[0],
            'answer_mode': generated.answer_mode,
            'elapsed_seconds': round(time.monotonic() - started, 2),
        })
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
