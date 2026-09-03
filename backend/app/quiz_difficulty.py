"""Requested cognitive demand, not a calibrated estimate of learner ability."""
from typing import Literal

Difficulty = Literal['easy', 'medium', 'hard', 'mixed']

DIFFICULTY_GUIDANCE = {
    'easy': 'Direct recall or recognition of one explicitly stated fact, using simple wording.',
    'medium': 'Explain a relationship or apply one explicitly supported principle in a short scenario.',
    'hard': 'Combine two or more supported facts to reason through an application or comparison; no outside knowledge.',
    'mixed': 'Include direct recall, one-step application, and multi-fact reasoning; distribute these as evenly as the count permits.',
}


def difficulty_guidance(value: Difficulty | None) -> str:
    return DIFFICULTY_GUIDANCE[value] if value is not None else 'Use foundational questions appropriate to the supplied material.'
