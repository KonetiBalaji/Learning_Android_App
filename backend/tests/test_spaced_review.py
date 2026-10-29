import pytest

from study.flashcards import from_question, review
from study.spaced_repetition import ReviewState, schedule


def test_successful_review_intervals_and_ceiling():
    state = ReviewState()
    first, repeat = schedule(state, 4, 100)
    second, _ = schedule(first, 4, first.due_at)
    third, _ = schedule(second, 4, second.due_at)
    assert (first.interval_days, second.interval_days, third.interval_days) == (1, 6, 15)
    assert not repeat and third.ease == 2.5 and third.version == 3
    fractional, _ = schedule(ReviewState(2, 6, 1.31), 4, 100)
    assert fractional.interval_days == 8


def test_lapse_resets_repetition_and_keeps_ease_floor():
    state, repeat = schedule(ReviewState(8, 90, 1.3), 0, 100)
    assert state.repetitions == 0 and state.interval_days == 1
    assert state.ease == 1.3 and state.lapses == 1 and repeat
    next_day, _ = schedule(state, 4, state.due_at)
    assert next_day.repetitions == 1 and next_day.interval_days == 1


@pytest.mark.parametrize("quality", [-1, 6, True, 3.5])
def test_reject_invalid_recall_ratings(quality):
    with pytest.raises(ValueError):
        schedule(ReviewState(), quality, 100)


def test_flashcard_preserves_proof_and_idempotent_review():
    question = {"source_id": "p0", "prompt": "Which structure produces energy?", "choices": ["Mitochondria", "Ribosomes"],
                "answer": 0, "explanation": "The passage identifies mitochondria.", "quote": "Mitochondria produce energy.", "page": 1, "concept": "s1"}
    card = from_question("doc", question)
    assert from_question("doc", question)["id"] == card["id"]
    assert from_question("other-doc", question)["id"] != card["id"]
    rated = review(card, 4, 0, "request-1", 100)
    assert review(rated, 4, 0, "request-1", 200) == rated
    assert rated["quote"] == question["quote"]
    with pytest.raises(ValueError):
        review(rated, 5, 0, "request-1", 200)
    with pytest.raises(ValueError):
        review(rated, 4, 0, "request-2", 200)
