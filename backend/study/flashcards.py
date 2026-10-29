"""Source-backed flashcards stored using the existing owner-scoped encrypted store."""
import hashlib
import time

from .spaced_repetition import ReviewState, schedule, state_dict


def from_question(document_id: str, question: dict) -> dict:
    identity = hashlib.sha256(f'{document_id}:{question["source_id"]}:{question["prompt"]}'.encode()).hexdigest()
    return {"id": f"card-{identity}", "document_id": document_id, "front": question["prompt"],
            "back": question["choices"][question["answer"]], "explanation": question["explanation"],
            "quote": question["quote"], "source_id": question["source_id"], "page": question["page"],
            "section_id": question.get("section_id", question["concept"]), "created": time.time(),
            "review": state_dict(ReviewState()), "last_review_request": None, "repeat_today": False}


def review(card: dict, quality: int, expected_version: int, request_id: str, now: float) -> dict:
    last = card.get("last_review_request")
    if last and last["id"] == request_id:
        if last["quality"] != quality or last["expected_version"] != expected_version:
            raise ValueError("A review request cannot be reused with a different rating.")
        return card
    state = ReviewState(**card["review"])
    if expected_version != state.version:
        raise ValueError("This flashcard changed. Refresh before rating it again.")
    next_state, repeat = schedule(state, quality, now)
    return {**card, "review": state_dict(next_state), "repeat_today": repeat,
            "last_review_request": {"id": request_id, "quality": quality, "expected_version": expected_version}}


def public_card(card: dict) -> dict:
    return {key: value for key, value in card.items() if key != "last_review_request"}
