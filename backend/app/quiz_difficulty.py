"""Requested cognitive demand, not a calibrated estimate of learner ability."""
from typing import Literal

Difficulty = Literal['easy', 'medium', 'hard', 'mixed']

DIFFICULTY_GUIDANCE = {
    'easy': 'Direct recall or recognition of one explicitly stated fact, using simple wording.',
    'medium': 'Explain a relationship or apply one explicitly supported principle in a short scenario.',
    'hard': 'Require at least two dependent reasoning steps, such as calculating remaining water then comparing supply with demand. Merely adding given values or dividing volume by rate is not Hard. No outside knowledge.',
    'mixed': 'Include direct recall, one-step application, and multi-fact reasoning; distribute these as evenly as the count permits.',
}


def difficulty_guidance(value: Difficulty | None) -> str:
    return DIFFICULTY_GUIDANCE[value] if value is not None else 'Use foundational questions appropriate to the supplied material.'


def difficulty_plan(value: Difficulty | None, count: int) -> list[str]:
    if value is None:
        return []
    levels = ['easy', 'medium', 'hard'] if value == 'mixed' else [value]
    return [levels[index % len(levels)] for index in range(count)]
