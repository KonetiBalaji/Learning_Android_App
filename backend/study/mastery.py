import re
from fractions import Fraction

from .starter_curriculum import STARTER_CHAPTERS


# Reviewed starter curriculum. The catalog advertises only chapters with authored material.
CHAPTERS = {
    "fractions": {
        "grade": 6, "subject": "Mathematics", "title": "Adding fractions", "requires": None,
        "prompt": "What is 3/4 + 1/4?", "choices": ["1/2", "1", "3/8", "2"], "answer": 1,
        "diagnostic_feedback": {
            0: "Adding one quarter to three quarters must give more than three quarters.",
            2: "The pieces are quarters throughout. Adding the fractions does not change them into eighths.",
            3: "Four quarters fill one whole. Two wholes would need eight quarters.",
        },
        "explanation": "The denominator tells you the size of the pieces. Both fractions use quarters, so add the numerators and keep the denominator: (3 + 1)/4 = 4/4 = 1.",
        "example": "2/5 + 3/5 = (2 + 3)/5 = 5/5 = 1.",
        "example_steps": [
            "Both fractions describe fifths, so the denominator stays 5.",
            "Combine the pieces: 2 fifths plus 3 fifths makes 5 fifths.",
            "Five fifths make one whole: 5/5 = 1.",
        ],
        "example_variants": {
            "Soccer": "A soccer player completed 2/5 of a drill, then completed another 3/5. In total, the player completed 5/5 of the drill.",
            "Gaming": "A quest meter fills by 2/5 for the first challenge and 3/5 for the second. Together they fill 5/5 of the meter.",
        },
        "practice": [("What is 2/8 + 4/8?", "3/4"), ("What is 1/7 + 3/7?", "4/7")],
        "hint": "Add the top numbers. The pieces stay the same size. You can simplify your answer.",
        "rewrite": "Explain why 3/4 + 1/4 = 1. Say what happens to the numerators and denominator.",
        "checks": [r"\badd(?:ing)?\b.{0,25}\b(numerators?|top numbers?)\b",
                   r"\b(keep|same|unchanged|stays?)\b.{0,25}\bdenominator\b|\bdenominator\b.{0,20}\b(same|unchanged|stays? 4)\b"],
    },
    "decimals": {
        "grade": 6, "subject": "Mathematics", "title": "Adding decimals", "requires": "fractions",
        "prompt": "What is 0.30 + 0.45?", "choices": ["0.75", "0.48", "0.15", "7.5"], "answer": 0,
        "diagnostic_feedback": {
            1: "The 3 in 0.30 counts tenths. It adds 30 hundredths, rather than 3 hundredths.",
            2: "Fifteen hundredths is the difference between 0.45 and 0.30. Adding should give more than 0.45.",
            3: "Seventy-five hundredths is less than one whole. Keep the decimal point aligned.",
        },
        "explanation": "Align the decimal points so you add digits with the same place value. Thirty hundredths plus forty-five hundredths is seventy-five hundredths.",
        "example": "0.2 + 0.35 = 0.20 + 0.35 = 0.55.",
        "example_steps": [
            "Rewrite 0.2 as 0.20 so both numbers show hundredths.",
            "Add the matching place values: 20 hundredths plus 35 hundredths is 55 hundredths.",
            "Write 55 hundredths as 0.55.",
        ],
        "example_variants": {
            "Soccer": "A player runs 0.20 km to warm up, then runs 0.35 km in a drill. The player runs 0.55 km in total.",
            "Gaming": "A game timer adds 0.20 seconds for one bonus and 0.35 seconds for another. The total bonus is 0.55 seconds.",
        },
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
        # Older lessons retain only whether any diagnostic answer was missed.
        diagnostic_misses = (lesson["diagnostic_index"] - lesson["diagnostic_hits"]
                             if "diagnostic_hits" in lesson else int(lesson.get("correct") is False))
        review_events = diagnostic_misses + misses + revisions
        locked = chapter["requires"] is not None and chapter["requires"] not in mastered
        result.append({
            "id": identifier, "grade": chapter["grade"], "subject": chapter["subject"], "title": chapter["title"],
            "mastered": identifier in mastered, "locked": locked, "started": bool(lesson),
            "practice_misses": misses, "rewrite_revisions": revisions,
            "review_events": review_events, "needs_practice": identifier not in mastered and review_events > 0,
        })
    return result


def new_lesson(identifier, started):
    return {"chapter_id": identifier, "started": started, "phase": "diagnostic", "version": 0,
            "practice_index": 0, "correct": None, "feedback": ""}


def diagnostic_items(chapter):
    return [(chapter["prompt"], chapter["choices"], chapter["answer"]), *chapter.get("diagnostics", ())]


def snapshot(lesson):
    chapter = CHAPTERS[lesson["chapter_id"]]
    phase = lesson["phase"]
    result = {key: lesson[key] for key in ("chapter_id", "phase", "version", "feedback")}
    if phase == "diagnostic":
        items = diagnostic_items(chapter)
        index = lesson.get("diagnostic_index", 0)
        prompt, choices, _ = items[index]
        result.update(prompt=prompt, choices=choices, diagnostic_index=index, diagnostic_total=len(items))
    elif phase == "coach":
        result.update(explanation=chapter["explanation"], example=chapter["example"],
                      diagnostic_remaining=0 < lesson.get("diagnostic_index", 0) < len(diagnostic_items(chapter)))
        if "example_steps" in chapter:
            result["example_steps"] = chapter["example_steps"]
        if "example_variants" in chapter:
            result["example_variants"] = chapter["example_variants"]
    elif phase == "practice":
        result.update(prompt=chapter["practice"][lesson["practice_index"]][0], hint=chapter["hint"])
    elif phase == "rewrite":
        result.update(prompt=chapter["rewrite"])
    elif phase == "mastered":
        result.update(elapsed_seconds=lesson["elapsed_seconds"], diagnostic_correct=lesson["correct"])
        if "diagnostic_hits" in lesson:
            result["diagnostic_score"] = {
                "correct": lesson["diagnostic_hits"],
                "total": lesson["diagnostic_index"],
            }
    return result


def advance(lesson, action, choice, response, now):
    chapter = CHAPTERS[lesson["chapter_id"]]
    phase = lesson["phase"]
    if phase == "diagnostic" and action == "diagnostic" and choice is not None and choice >= 0:
        items = diagnostic_items(chapter)
        index = lesson.get("diagnostic_index", 0)
        _, choices, answer = items[index]
        if choice >= len(choices):
            raise ValueError("This choice is not available for the diagnostic question.")
        correct = choice == answer
        lesson["correct"] = lesson["correct"] is not False and correct
        # Older attempts may have a partial diagnostic without a recorded count.
        if index == 0 or "diagnostic_hits" in lesson:
            lesson["diagnostic_hits"] = lesson.get("diagnostic_hits", 0) + int(correct)
        lesson["diagnostic_index"] = index + 1
        if correct:
            lesson["phase"] = "diagnostic" if index + 1 < len(items) else "practice"
            lesson["feedback"] = "Correct. Continue to the next question." if lesson["phase"] == "diagnostic" else "Correct. Try a new example."
        else:
            guidance = chapter.get("diagnostic_feedback", {}).get(choice) if index == 0 else None
            guidance = guidance or "Review the worked example, then continue."
            lesson.update(phase="coach", feedback=f"You chose {choices[choice]}. {guidance}")
    elif phase == "coach" and action == "continue":
        next_phase = "diagnostic" if 0 < lesson.get("diagnostic_index", 0) < len(diagnostic_items(chapter)) else "practice"
        lesson.update(phase=next_phase, feedback="")
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
                          elapsed_seconds=max(0, int(now - lesson["started"])), mastered_at=now)
        else:
            lesson["rewrite_revisions"] = lesson.get("rewrite_revisions", 0) + 1
            lesson.update(feedback="Use the prompt to identify the key ideas, or return to the worked example.")
    elif phase == "rewrite" and action == "review":
        lesson.update(phase="coach", feedback="")
    else:
        raise ValueError("This action is not available at the current learning step.")
    lesson["last_activity"] = now
    lesson["version"] += 1
