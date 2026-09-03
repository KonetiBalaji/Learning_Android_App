from __future__ import annotations

import re
import json
from dataclasses import asdict
from dataclasses import dataclass

from .schemas import AdaptiveQuestion, TutorIntervention


@dataclass(frozen=True)
class DiagnosticItem:
    prompt: str
    options: tuple[str, ...]
    correct_option: str
    concept: str
    explanation: str
    worked_example: str
    hint: str
    practice_prompt: str
    practice_answers: tuple[str, ...]


FRACTION_DIAGNOSTIC = (
    DiagnosticItem(
        "What is 3/4 + 1/4?", ("1/2", "1", "3/8", "2"), "1", "Adding like fractions",
        "When denominators are the same, add the numerators and keep the denominator: (3 + 1) / 4 = 4/4 = 1.",
        "2/5 + 3/5 = 5/5 = 1.", "Keep the denominator 4 and add 3 + 1.",
        "What is 2/8 + 4/8?", ("6/8", "3/4", "0.75"),
    ),
    DiagnosticItem(
        "Which fraction is equal to 1/2?", ("2/6", "3/6", "4/6", "5/6"), "3/6", "Equivalent fractions",
        "Equivalent fractions name the same amount. Multiplying 1/2 by 3/3 gives 3/6.",
        "1/3 multiplied by 2/2 is 2/6.", "Multiply the numerator and denominator of 1/2 by the same number.",
        "Name a fraction equivalent to 2/3 with denominator 6.", ("4/6",),
    ),
    DiagnosticItem(
        "What is 5/8 - 1/8?", ("4/8", "4/16", "5/7", "6/8"), "4/8", "Subtracting like fractions",
        "With equal denominators, subtract the numerators and keep the denominator: (5 - 1) / 8 = 4/8.",
        "6/7 - 2/7 = 4/7.", "Keep the denominator 8 and subtract 1 from 5.",
        "What is 7/9 - 2/9?", ("5/9",),
    ),
)


def diagnostic_bank(subject_id: str, chapter_id: str) -> tuple[DiagnosticItem, ...]:
    if subject_id.lower() == "math" and chapter_id.lower() == "fractions":
        return FRACTION_DIAGNOSTIC
    raise ValueError("Adaptive diagnostics are currently available for Mathematics: Fractions")


def validate_diagnostic_bank(items: tuple[DiagnosticItem, ...]) -> tuple[DiagnosticItem, ...]:
    if len(items) != 3:
        raise ValueError("A diagnostic must contain exactly three questions")
    seen_prompts: set[str] = set()
    for item in items:
        prompt_key = item.prompt.strip().lower()
        if not prompt_key or prompt_key in seen_prompts:
            raise ValueError("Diagnostic questions must be present and unique")
        seen_prompts.add(prompt_key)
        if len(item.options) != 4 or len({option.strip().lower() for option in item.options}) != 4:
            raise ValueError("Every diagnostic question must have four unique choices")
        if item.correct_option not in item.options:
            raise ValueError("Every correct answer must exactly match one choice")
        if not all((item.concept, item.explanation, item.worked_example, item.hint, item.practice_prompt)) or not item.practice_answers:
            raise ValueError("Every diagnostic question must include complete teaching support")
    return items


def serialize_diagnostic_bank(items: tuple[DiagnosticItem, ...]) -> str:
    validate_diagnostic_bank(items)
    return json.dumps([asdict(item) for item in items], ensure_ascii=False)


def parse_diagnostic_bank(value: str) -> tuple[DiagnosticItem, ...]:
    decoded = json.loads(value)
    items = tuple(
        DiagnosticItem(
            **{
                **item,
                "options": tuple(item["options"]),
                "practice_answers": tuple(item["practice_answers"]),
            }
        )
        for item in decoded
    )
    return validate_diagnostic_bank(items)


def public_question(item: DiagnosticItem, ordinal: int, total: int) -> AdaptiveQuestion:
    return AdaptiveQuestion(ordinal=ordinal + 1, total=total, prompt=item.prompt, options=list(item.options), concept=item.concept)


def tutor_for(item: DiagnosticItem) -> TutorIntervention:
    return TutorIntervention(title=item.concept, explanation=item.explanation, worked_example=item.worked_example, hint=item.hint, practice_prompt=item.practice_prompt)


def normalize_fraction_response(value: str) -> str:
    compact = re.sub(r"\s+", "", value.lower())
    return "3/4" if compact in {"6/8", "3/4", "0.75"} else compact


def response_matches(value: str, acceptable_answers: tuple[str, ...]) -> tuple[bool, str]:
    normalized = re.sub(r"[^a-z0-9./%-]", "", value.casefold())
    acceptable = {re.sub(r"[^a-z0-9./%-]", "", answer.casefold()) for answer in acceptable_answers}
    return normalized in acceptable, normalized


def evaluate_rewrite(value: str, concept: str = "Adding like fractions") -> tuple[bool, str | None]:
    normalized = value.lower()
    words = re.findall(r"[a-z0-9]+", normalized)
    concept_terms = {"numerator", "denominator", "same", "equal", "fourths", "parts"}
    evidence_terms = {"add", "plus", "total", "sum", "4/4", "one"}
    if concept == "Adding like fractions":
        understood = len(words) >= 8 and bool(concept_terms.intersection(words)) and (bool(evidence_terms.intersection(words)) or "4/4" in normalized)
    else:
        concept_words = {word for word in re.findall(r"[a-z0-9]+", concept.lower()) if len(word) > 3}
        understood = len(words) >= 8 and bool(concept_words.intersection(words))
    if understood:
        return True, None
    return False, f"Explain the key idea behind {concept}, then connect it to the practice example."


def confidence_for(score: float) -> str:
    if score >= 0.85:
        return "high"
    if score >= 0.65:
        return "developing"
    return "needs_support"
