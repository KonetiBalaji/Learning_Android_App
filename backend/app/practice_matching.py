"""Conservative literal matching, with explicitly opted-in rational equivalence."""
import re
from fractions import Fraction
from typing import Literal

AnswerMode = Literal["exact", "number"]


def requires_exact_numeric_format(prompt: str) -> bool:
    """High-confidence English constraints override a reviewer's 'none'.

    This is a safety net, not a general semantic classifier or curriculum parser.
    Unknown wording still depends on independent model review.
    """
    return bool(re.search(
        r"\b(?:simplify|simplest\s+(?:form|terms)|lowest\s+terms|reduce\s+to|"
        r"denominator\s+(?:of\s+)?[0-9]+|decimal\s+places?|significant\s+figures?|"
        r"round(?:ed|ing)?\s+(?:to|off)|as\s+(?:an?\s+)?(?:mixed\s+number|decimal|fraction|percentage))\b",
        prompt.casefold(),
    ))


def normalize_answer(value: str) -> str:
    # Preserve operators, punctuation and word boundaries. Never turn 3+4 into 34.
    value = " ".join(value.casefold().replace("−", "-").split())
    return re.sub(r"\s*/\s*", "/", value)


def rational_answer(value: str) -> Fraction | None:
    """Parse only bounded numeric literals; no expressions, units or evaluation."""
    if len(value) > 100:
        return None
    digit = r"[0-9]{1,24}"
    mixed = re.fullmatch(rf"([+-]?)({digit}) ({digit})/({digit})", value)
    if mixed:
        sign, whole, numerator, denominator = mixed.groups()
        n, d = int(numerator), int(denominator)
        if not 0 <= n < d:
            return None
        result = Fraction(int(whole)) + Fraction(n, d)
        return -result if sign == "-" else result
    fraction = re.fullmatch(rf"[+-]?{digit}/({digit})", value)
    if fraction:
        return Fraction(value) if int(fraction.group(1)) > 0 else None
    if re.fullmatch(rf"[+-]?(?:{digit}(?:\.[0-9]{{1,24}})?|\.[0-9]{{1,24}})", value):
        return Fraction(value)
    return None


def response_matches(value: str, acceptable_answers: tuple[str, ...],
                     mode: AnswerMode = "exact") -> tuple[bool, str]:
    if mode not in {"exact", "number"}:
        raise ValueError("Unsupported practice answer mode")
    normalized = normalize_answer(value)
    acceptable = {normalize_answer(answer) for answer in acceptable_answers}
    if normalized and normalized in acceptable:
        return True, normalized
    numeric = rational_answer(normalized) if mode == "number" else None
    return (numeric is not None and any(
        numeric == rational_answer(answer) for answer in acceptable
    )), normalized
