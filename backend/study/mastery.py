import re
from fractions import Fraction

from .starter_curriculum import STARTER_CHAPTERS


# Reviewed starter curriculum. The catalog advertises only chapters with authored material.
CHAPTERS = {
    "fractions": {
        "grade": 6, "subject": "Mathematics", "title": "Adding fractions", "requires": None,
        "prompt": "What is 3/4 + 1/4?", "choices": ["1/2", "1", "3/8", "2"], "answer": 1,
        "explanation": "The denominator tells you the size of the pieces. Both fractions use quarters, so add the numerators and keep the denominator: (3 + 1)/4 = 4/4 = 1.",
        "example": "2/5 + 3/5 = (2 + 3)/5 = 5/5 = 1.",
        "practice": [("What is 2/8 + 4/8?", "3/4"), ("What is 1/7 + 3/7?", "4/7")],
        "hint": "Add the top numbers. The pieces stay the same size. You can simplify your answer.",
        "rewrite": "Explain why 3/4 + 1/4 = 1. Say what happens to the numerators and denominator.",
        "checks": [r"\badd(?:ing)?\b.{0,25}\b(numerators?|top numbers?)\b",
                   r"\b(keep|same|unchanged|stays?)\b.{0,25}\bdenominator\b|\bdenominator\b.{0,20}\b(same|unchanged|stays? 4)\b"],
    },
    "decimals": {
        "grade": 6, "subject": "Mathematics", "title": "Adding decimals", "requires": "fractions",
        "prompt": "What is 0.30 + 0.45?", "choices": ["0.75", "0.48", "0.15", "7.5"], "answer": 0,
        "explanation": "Align the decimal points so you add digits with the same place value. Thirty hundredths plus forty-five hundredths is seventy-five hundredths.",
        "example": "0.2 + 0.35 = 0.20 + 0.35 = 0.55.",
        "practice": [("What is 0.4 + 0.28?", "0.68"), ("What is 0.06 + 0.2?", "0.26")],
        "hint": "Write both numbers with two decimal places and add matching place values.",
        "rewrite": "Explain how aligning decimal points helps you add 0.30 and 0.45.",
        "checks": [r"\b(align|line up|match)\b.{0,25}\bdecimal points?\b",
                   r"\b(place values?|hundredths|tenths)\b"],
    },
    **STARTER_CHAPTERS,
}


def catalog(lessons):
    progress = {lesson["chapter_id"]: lesson for lesson in lessons}
    mastered = {identifier for identifier, lesson in progress.items() if lesson["phase"] == "mastered"}
    result = []
    for identifier, chapter in CHAPTERS.items():
        lesson = progress.get(identifier, {})
        misses = lesson.get("practice_misses", 0)
        revisions = lesson.get("rewrite_revisions", 0)
        diagnostic_miss = lesson.get("correct") is False
        locked = chapter["requires"] is not None and chapter["requires"] not in mastered
        result.append({
            "id": identifier, "grade": chapter["grade"], "subject": chapter["subject"], "title": chapter["title"],
            "mastered": identifier in mastered, "locked": locked, "started": bool(lesson),
            "practice_misses": misses, "rewrite_revisions": revisions,
            "needs_practice": bool(lesson) and identifier not in mastered and (diagnostic_miss or misses > 0 or revisions > 0),
        })
    return result


def new_lesson(identifier, started):
    return {"chapter_id": identifier, "started": started, "phase": "diagnostic", "version": 0,
            "practice_index": 0, "correct": None, "feedback": ""}


def snapshot(lesson):
    chapter = CHAPTERS[lesson["chapter_id"]]
    phase = lesson["phase"]
    result = {key: lesson[key] for key in ("chapter_id", "phase", "version", "feedback")}
    if phase == "diagnostic":
        result.update(prompt=chapter["prompt"], choices=chapter["choices"])
    elif phase == "coach":
        result.update(explanation=chapter["explanation"], example=chapter["example"])
    elif phase == "practice":
        result.update(prompt=chapter["practice"][lesson["practice_index"]][0], hint=chapter["hint"])
    elif phase == "rewrite":
        result.update(prompt=chapter["rewrite"])
    elif phase == "mastered":
        result.update(elapsed_seconds=lesson["elapsed_seconds"], diagnostic_correct=lesson["correct"])
    return result


def advance(lesson, action, choice, response, now):
    chapter = CHAPTERS[lesson["chapter_id"]]
    phase = lesson["phase"]
    if phase == "diagnostic" and action == "diagnostic" and choice is not None and 0 <= choice < len(chapter["choices"]):
        lesson["correct"] = choice == chapter["answer"]
        lesson["phase"] = "practice" if lesson["correct"] else "coach"
        lesson["feedback"] = "Correct. Try a new example." if lesson["correct"] else "Review the worked example, then try again."
    elif phase == "coach" and action == "continue":
        lesson.update(phase="practice", feedback="")
    elif phase == "practice" and action == "practice":
        value = response.strip()
        expected = chapter["practice"][lesson["practice_index"]][1]
        if chapter.get("numeric", True):
            try:
                correct = bool(re.fullmatch(r"[0-9]{1,8}(?:[./][0-9]{1,8})?", value)) and (
                    Fraction(value) == Fraction(expected))
            except (ValueError, ZeroDivisionError):
                correct = False
        else:
            correct = value.casefold().rstrip(".") == expected
        if correct:
            lesson.update(phase="rewrite", feedback="Correct. Now explain the rule in your own words.")
        else:
            lesson["practice_misses"] = lesson.get("practice_misses", 0) + 1
            lesson.update(phase="coach", feedback="That answer needs another try. Review the example first.",
                          practice_index=(lesson["practice_index"] + 1) % len(chapter["practice"]))
    elif phase == "rewrite" and action == "rewrite":
        normalized = response.lower()
        # A narrow checklist, not a general evaluation of free-form writing.
        if (len(normalized.split()) >= 6 and not re.search(r"\b(not|never|wrong)\b", normalized)
                and all(re.search(pattern, normalized) for pattern in chapter["checks"])):
            lesson.update(phase="mastered", feedback="You completed the practice and explained the key rule.",
                          elapsed_seconds=max(0, int(now - lesson["started"])))
        else:
            lesson["rewrite_revisions"] = lesson.get("rewrite_revisions", 0) + 1
            lesson.update(feedback="Use the prompt to identify the key ideas, or return to the worked example.")
    elif phase == "rewrite" and action == "review":
        lesson.update(phase="coach", feedback="")
    else:
        raise ValueError("This action is not available at the current learning step.")
    lesson["version"] += 1
