"""Isolated localhost-only Android workflow fixture, never a production server.

Uses scripted grading to verify Android score display/recovery without API
charges. Real-provider scoring is tested separately by evaluate_rewrite.py.
Run: uv run python scripts/serve_qa.py --qa-only
"""
import argparse
import os
from pathlib import Path
import secrets
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def catalog_fixture_bank(grade, subject_id, chapter_id):
    """One reviewed, deterministic wrong-answer path for catalog UI QA only."""
    from app.learning_path import catalog_chapter
    from app.mastery_service import DiagnosticItem
    chapter = catalog_chapter(subject_id, chapter_id)
    if grade != 8 or chapter is None:
        raise ValueError('The catalog QA fixture supports current Grade 8 chapters only')
    return (DiagnosticItem(
        prompt=f'Which option should open the reviewed {chapter.title} teaching example?',
        options=('Needs another look', 'Ready for the example'),
        correct_option='Ready for the example',
        concept=f'{chapter.title} reviewed example',
        explanation=f'Use the interactive {chapter.title} explorer to examine this concept.',
        worked_example=f'Select each control in the {chapter.title} explorer and observe what changes.',
        hint='The explorer is for investigation and does not submit an assessment answer.',
        practice_prompt=f'Explain one observation from the {chapter.title} explorer.',
        practice_answers=('observation',),
    ),)


def scripted_tutor_answer(question):
    if question == 'QA unavailable':
        raise RuntimeError('Scripted QA tutor outage')
    return {'answer': 'Scripted QA reply: equal denominators describe equal-sized parts.', 'supported': True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--qa-only", action="store_true")
    parser.add_argument("--binary-fixtures", action="store_true")
    parser.add_argument("--science-fixture", action="store_true")
    parser.add_argument("--english-fixture", action="store_true")
    parser.add_argument("--social-fixture", action="store_true")
    parser.add_argument("--catalog-fixture", action="store_true")
    parser.add_argument("--upload-response-delay", type=int, choices=range(0, 21), default=0)
    parser.add_argument("--fail-saved-upload-response", action="store_true")
    args = parser.parse_args()
    if sum((args.binary_fixtures, args.science_fixture, args.english_fixture,
            args.social_fixture, args.catalog_fixture)) > 1:
        parser.error('Choose only one content fixture.')
    if not args.qa_only:
        parser.error("This scripted evaluator is only for QA; supply --qa-only")
    if args.fail_saved_upload_response and not args.upload_response_delay:
        parser.error("Upload response fault requires --upload-response-delay")
    os.environ["LEARNING_AI_MODE"] = "openai" if args.binary_fixtures else "deterministic"
    os.environ["LEARNING_RUNTIME_DIR"] = str(Path(__file__).resolve().parents[2] / "artifacts" / "qa-scripted-runtime")
    os.environ["LEARNING_JWT_SECRET"] = secrets.token_hex(32)
    import app.main as api
    from app.tutor_provider import DeterministicTutorProvider, RewriteAssessment
    from app.mastery_service import DiagnosticItem
    import uvicorn
    if args.binary_fixtures:
        # Replace the only document-provider entry point before serving requests.
        # This mode never falls back to an external provider.
        from scripts.qa_binary_questions import generate_binary_fixture
        api.generate_document_questions = generate_binary_fixture

    class ScriptedQAProvider(DeterministicTutorProvider):
        name = ("scripted-catalog-qa" if args.catalog_fixture else
                "scripted-social-qa" if args.social_fixture else
                "scripted-english-qa" if args.english_fixture else
                "scripted-science-qa" if args.science_fixture else
                "scripted-binary-qa" if args.binary_fixtures else "scripted-qa")

        def diagnostic_bank(self, grade, subject_id, chapter_id):
            if args.catalog_fixture:
                return catalog_fixture_bank(grade, subject_id, chapter_id)
            if args.science_fixture and (grade, subject_id, chapter_id) == (8, 'science', 'cells'):
                concepts = (
                    ('Where is most DNA stored in a eukaryotic cell?', ('Cell wall', 'Nucleus', 'Ribosome', 'Cytoplasm'), 'Nucleus', 'Nucleus'),
                    ('Which organelle releases usable energy from food?', ('Nucleus', 'Mitochondrion', 'Vacuole', 'Cell wall'), 'Mitochondrion', 'Mitochondrion'),
                    ('Which structure builds proteins?', ('Ribosome', 'Nucleus', 'Vacuole', 'Cell membrane'), 'Ribosome', 'Ribosome'),
                )
                return tuple(DiagnosticItem(
                    prompt=prompt, options=options, correct_option=answer,
                    concept=f'Cell organelles — {concept.lower()}',
                    explanation=f'The {concept.lower()} has a distinct job that supports the cell.',
                    worked_example=f'Use the cell diagram to locate the {concept.lower()} and connect it to its function.',
                    hint='Match the organelle name to the function shown in the lesson.',
                    practice_prompt=f'Name the organelle described in this {concept.lower()} example.',
                    practice_answers=(answer,),
                ) for prompt, options, answer, concept in concepts)
            if args.english_fixture and (grade, subject_id, chapter_id) == (8, 'english', 'grammar'):
                concepts = (
                    ('Which sentence part names who or what performs the action?', ('Subject', 'Verb', 'Object', 'Punctuation'), 'Subject', 'Subject'),
                    ('Which sentence part expresses the action?', ('Object', 'Adjective', 'Verb', 'Subject'), 'Verb', 'Verb'),
                    ('Which sentence part receives the action?', ('Verb', 'Object', 'Subject', 'Adverb'), 'Object', 'Object'),
                )
                return tuple(DiagnosticItem(
                    prompt=prompt, options=options, correct_option=answer,
                    concept=f'Sentence parts — {concept.lower()}',
                    explanation=f'The {concept.lower()} has a distinct grammatical job in a complete sentence.',
                    worked_example=f'Use the sentence explorer to locate the {concept.lower()} and connect it to its role.',
                    hint='Ask who acts, what action happens, and what receives that action.',
                    practice_prompt=f'Identify the {concept.lower()} in: The curious student solved the puzzle.',
                    practice_answers=("The curious student" if answer == 'Subject' else "solved" if answer == 'Verb' else "the puzzle",),
                ) for prompt, options, answer, concept in concepts)
            if args.social_fixture and (grade, subject_id, chapter_id) == (8, 'social', 'geography'):
                concepts = (
                    ('Which reference line is 0 degrees latitude?', ('Prime Meridian', 'Equator', 'Tropic of Cancer', 'International Date Line'), 'Equator', 'Equator'),
                    ('Which reference line is 0 degrees longitude?', ('Equator', 'Arctic Circle', 'Prime Meridian', 'Tropic of Capricorn'), 'Prime Meridian', 'Prime Meridian'),
                    ('In 20° N, 60° E, which coordinate is written first?', ('Longitude', 'Time zone', 'Latitude', 'Elevation'), 'Latitude', 'Coordinates'),
                )
                return tuple(DiagnosticItem(
                    prompt=prompt, options=options, correct_option=answer,
                    concept=f'Map coordinates — {concept.lower()}',
                    explanation=f'{concept} is a standard reference used to locate places on Earth.',
                    worked_example=f'Use the globe explorer to highlight {concept.lower()} and connect it to its coordinate role.',
                    hint='Latitude is written before longitude; connect each zero-degree line to its name.',
                    practice_prompt=f'Identify the requested map reference for {concept.lower()}.',
                    practice_answers=(answer,),
                ) for prompt, options, answer, concept in concepts)
            return super().diagnostic_bank(grade, subject_id, chapter_id)

        def answer_question(self, grade, item, question, history):
            return scripted_tutor_answer(question)

        def assess_rewrite(self, grade, item, response):
            base = super().assess_rewrite(grade, item, response)
            return RewriteAssessment(understood=base.understood, score=4 if base.understood else 1,
                                     feedback="Scripted QA feedback: the display and recovery contract are working.",
                                     coaching=base.coaching)

    api.tutor_provider = lambda settings, interests=(): ScriptedQAProvider()
    from scripts.qa_response_fault import install_response_fault
    install_response_fault(api.app)
    if args.upload_response_delay:
        from scripts.qa_upload_delay import install_upload_delay
        install_upload_delay(api.app, args.upload_response_delay, args.fail_saved_upload_response)
    uvicorn.run(api.app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
