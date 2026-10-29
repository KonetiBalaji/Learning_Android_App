"""SM-2 scheduling, independent of HTTP, persistence, and model providers.

Reference: https://www.super-memory.com/english/ol/sm2.htm
Grades below four also request an immediate learning repeat; persisted due dates
control the next daily review, rather than pretending a failed card was learned.
"""
from dataclasses import asdict, dataclass
import math


@dataclass(frozen=True)
class ReviewState:
    repetitions: int = 0
    interval_days: int = 0
    ease: float = 2.5
    lapses: int = 0
    due_at: float = 0.0
    version: int = 0

    def __post_init__(self):
        if any(type(value) is not int or value < 0 for value in (self.repetitions, self.interval_days, self.lapses, self.version)):
            raise ValueError("Review counts must be nonnegative integers.")
        if not math.isfinite(self.ease) or self.ease < 1.3 or not math.isfinite(self.due_at):
            raise ValueError("Invalid review state.")


def schedule(state: ReviewState, quality: int, now: float) -> tuple[ReviewState, bool]:
    if type(quality) is not int or not 0 <= quality <= 5:
        raise ValueError("Rate recall from zero to five.")
    if not math.isfinite(now) or now < 0:
        raise ValueError("Review time must be a valid timestamp.")
    ease = max(1.3, state.ease + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    if quality < 3:
        repetitions, interval, lapses = 0, 1, state.lapses + 1
    else:
        repetitions = state.repetitions + 1
        interval = 1 if repetitions == 1 else 6 if repetitions == 2 else math.ceil(state.interval_days * state.ease)
        lapses = state.lapses
    return ReviewState(repetitions, interval, round(ease, 6), lapses, now + interval * 86400, state.version + 1), quality < 4


def state_dict(state: ReviewState) -> dict:
    return asdict(state)
