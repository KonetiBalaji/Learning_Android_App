"""Explicit live smoke test using synthetic educational text only."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import get_settings
from app.document_question_provider import generate_document_questions, QuestionGenerationUnavailable
from app.schemas import Chapter

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--difficulty', choices=['easy', 'medium', 'hard', 'mixed'])
    parser.add_argument('--question-type', choices=['multiple_choice', 'true_false', 'yes_no'],
                        default='multiple_choice')
    args = parser.parse_args()
    if not args.live: parser.error('Use --live to authorize two API requests with synthetic text')
    text = ('Cells are the basic units of life. The cell membrane controls what enters and leaves the cell. '
            'The nucleus contains genetic instructions. Mitochondria release usable energy during cellular respiration. '
            'Ribosomes produce proteins. Chloroplasts in plant cells absorb light for photosynthesis. '
            'The cell wall supports and protects plant cells. A large central vacuole stores water in plant cells.')
    try:
        questions = generate_document_questions(text, [Chapter(id='cells', title='Cells', start_character=0,
            end_character=len(text), confidence=1)], ['cells'], 5, get_settings(), args.difficulty,
            args.question_type)
    except QuestionGenerationUnavailable as error:
        cause = error.__cause__
        safe_reason = str(cause) if isinstance(cause, ValueError) else type(cause).__name__
        raise SystemExit(f'FAIL: strict validation category={safe_reason}') from None
    for index, item in enumerate(questions, 1):
        print(f'{index}. {item.prompt}\nOptions: {item.options}\nAnswer: {item.correct_option}\nSource: {item.source_reference}')
    print(f'PASS: {len(questions)} synthetic questions accepted by grounding and blind review; not a calibrated evaluation')
