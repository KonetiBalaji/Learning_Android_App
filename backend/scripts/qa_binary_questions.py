"""Explicit UI fixtures, not a curriculum or an AI provider fallback."""
from app.document_selection import resolve_chapters
from app.quiz_service import GeneratedQuestion


def generate_binary_fixture(text, chapters, ids, count, settings, difficulty=None, question_type='multiple_choice'):
    if question_type not in {'true_false', 'yes_no'}:
        raise ValueError('This QA fixture requires a binary format')
    chapter = resolve_chapters(text, chapters, ids)[0]
    options = ['True', 'False'] if question_type == 'true_false' else ['Yes', 'No']
    return [GeneratedQuestion(
        prompt=f'QA fixture {index + 1}: select {options[index % 2]} to test the answer flow.',
        options=options.copy(), correct_option=options[index % 2],
        explanation=f'Scripted QA only. The expected test choice is {options[index % 2]}.',
        source_reference=f'{chapter.title} (QA scripted fixture, not a source assessment)',
    ) for index in range(count)]
