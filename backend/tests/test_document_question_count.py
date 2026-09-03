import pytest

from app.quiz_service import generate_grounded_questions
from app.schemas import Chapter


def material(size):
    text = ' '.join(f'Example {index}: plants convert sunlight into stored chemical energy through photosynthesis.' for index in range(size))
    return text, [Chapter(id='a', title='Notes', start_character=0, end_character=len(text), confidence=1)]


@pytest.mark.parametrize('count', [5, 7, 10, 15, 20])
def test_requested_count_is_exact(count):
    text, chapters = material(20)
    questions = generate_grounded_questions(text, chapters, ['a'], count)
    assert len(questions) == count
    assert len({question.prompt for question in questions}) == count


def test_insufficient_material_does_not_return_a_shorter_quiz():
    text, chapters = material(5)
    with pytest.raises(ValueError, match='requested number'):
        generate_grounded_questions(text, chapters, ['a'], 10)
