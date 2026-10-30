"""Choose a next practice focus from recent, distinct answer evidence."""
from .documents import DocumentError
from .quizzes import local_capacity


def recommend(document: dict, quizzes: list[dict], *, ai_configured: bool) -> dict:
    groups = {}
    for passage in document["passages"]:
        groups.setdefault(passage["section_id"], []).append(passage)
    eligible = {section: len(passages) if ai_configured else local_capacity(passages) for section, passages in groups.items()}
    eligible = {section: count for section, count in eligible.items() if count > 0}
    if not eligible:
        raise DocumentError("This material is too short for a focused practice quiz. Add more source text.")
    evidence, seen = {}, set()
    completed = sorted((q for q in quizzes if q["document_id"] == document["id"] and q["index"] == len(q["questions"])), key=lambda q: q["created"], reverse=True)[:5]
    for quiz in completed:
        for question, answer in zip(quiz["questions"], quiz["answers"]):
            section = question.get("section_id", question["concept"])
            identity = (section, " ".join(question["prompt"].casefold().split()))
            if identity in seen:
                continue
            seen.add(identity)
            counts = evidence.setdefault(section, [0, 0])
            counts[0] += int(answer["correct"])
            counts[1] += 1
    candidates = []
    for section in document["sections"]:
        if section["id"] not in eligible:
            continue
        correct, total = evidence.get(section["id"], [0, 0])
        score = (correct + 1) / (total + 2)
        candidates.append((score, section, correct, total))
    _, section, correct, total = min(candidates, key=lambda candidate: candidate[0])
    accuracy = correct / total if total else None
    desired = "easy" if total < 5 or accuracy < 0.6 else "hard" if total >= 8 and accuracy >= 0.85 else "medium"
    level = desired if ai_configured else "easy"
    return {"document_id": document["id"], "section_ids": [section["id"]], "section_title": section["title"],
            "count": min(10, eligible[section["id"]]), "question_type": "multiple_choice", "difficulty": level,
            "recommended_difficulty": desired, "evidence": {"correct": correct, "answered": total, "distinct_questions": True},
            "reason": f"Your latest answers in this section: {correct} of {total} correct." if total else "This section has no completed practice evidence yet.",
            "notice": None if ai_configured else "Local practice checks exact recall at Easy difficulty. AI difficulty remains available after provider setup."}
