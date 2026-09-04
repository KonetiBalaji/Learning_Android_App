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
        prompt="Which organelle stores the cell's genetic information?",
        options=('Cell membrane', 'Nucleus', 'Ribosome', 'Cytoplasm'),
        correct_option='Nucleus', concept='Cell organelles — nucleus',
        explanation="The nucleus contains most of a eukaryotic cell's genetic information.",
        worked_example='A skin cell stores its chromosomes inside the nucleus.',
        hint="Think where the cell's genes are kept.",
        practice_prompt="Name the organelle that stores the cell's genetic information.",
        practice_answers=('nucleus',),
    )),
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
            generated_output = captured[0] if captured else {}
            review_output = captured[1] if len(captured) > 1 else {}
            results.append({
                'subject': subject, 'chapter': chapter, 'concept': item.concept,
                'accepted': False, 'reason': str(failure),
                'generated_prompt': generated_output.get('practice_prompt'),
                'generated_answer': generated_output.get('practice_answer'),
                'generated_hint': generated_output.get('hint'),
                'review_valid': review_output.get('valid'),
                'review_answers': review_output.get('answers', []),
                'review_format': review_output.get('format_constraint'),
                'elapsed_seconds': round(time.monotonic() - started, 2),
            })
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
