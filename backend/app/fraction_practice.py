"""Arithmetic-generated variants for the three existing Fractions concepts."""
from dataclasses import replace
from fractions import Fraction
from .mastery_service import DiagnosticItem


def next_fraction_practice(item: DiagnosticItem, round_number: int) -> DiagnosticItem | None:
    n = round_number + 2
    denominator = 2 * n + 3
    if item.concept == 'Adding like fractions':
        prompt = f'What is {n}/{denominator} + 2/{denominator}?'
        numerator = n + 2
        answer = f'{numerator}/{denominator}'
        hint = f'Add the numerators {n} and 2; keep the denominator {denominator}.'
    elif item.concept == 'Subtracting like fractions':
        prompt = f'What is {n + 2}/{denominator} - 1/{denominator}?'
        numerator = n + 1
        answer = f'{numerator}/{denominator}'
        hint = f'Subtract 1 from the numerator {n + 2}; keep the denominator {denominator}.'
    elif item.concept == 'Equivalent fractions':
        prompt = f'Name a fraction equivalent to {n}/{denominator} with denominator {denominator * 2}.'
        numerator, denominator = n * 2, denominator * 2
        answer = f'{numerator}/{denominator}'
        hint = 'The denominator was multiplied by 2. Multiply the numerator by 2 as well.'
    else:
        return None
    answers = (answer,) if item.concept == 'Equivalent fractions' else tuple(dict.fromkeys((answer, str(Fraction(numerator, denominator)))))
    return replace(item, practice_prompt=prompt, practice_answers=answers, hint=hint)
