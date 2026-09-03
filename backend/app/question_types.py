"""Document question formats; cognitive difficulty is a separate setting."""
from typing import Literal

QuestionType = Literal['multiple_choice', 'true_false', 'yes_no']

TYPE_GUIDANCE = {
    'multiple_choice': 'Ask a multiple-choice question with exactly four distinct options and one correct answer.',
    'true_false': 'Present one unambiguous statement to judge, with options exactly True and False in that order.',
    'yes_no': 'Ask one unambiguous yes/no question, with options exactly Yes and No in that order.',
}


def valid_type_options(question_type: QuestionType, options: list[str], correct_index: int) -> bool:
    if not 0 <= correct_index < len(options):
        return False
    if question_type == 'multiple_choice':
        return len(options) == 4
    return options == (['True', 'False'] if question_type == 'true_false' else ['Yes', 'No'])
