"""Limited curriculum reports shared through explicit, account-scoped invitations."""

import hashlib

from . import mastery


def digest(code):
    return hashlib.sha256(code.encode()).hexdigest()


def report(lessons, role, now):
    chapters = mastery.catalog(lessons)
    subjects = {}
    for chapter in chapters:
        key = (chapter["grade"], chapter["subject"])
        summary = subjects.setdefault(key, {"grade": key[0], "subject": key[1], "available": 0, "mastered": 0})
        summary["available"] += 1
        summary["mastered"] += int(chapter["mastered"])
    priorities = sorted((chapter for chapter in chapters if chapter["needs_practice"]),
                        key=lambda chapter: -chapter["review_events"])
    weak_areas = [{key: chapter[key] for key in ("grade", "subject", "title")} for chapter in priorities]
    cutoff = now - 7 * 86400
    recent = sum(cutoff <= lesson.get("last_activity", 0) <= now for lesson in lessons)
    mastered_recently = sum(cutoff <= lesson.get("mastered_at", 0) <= now for lesson in lessons)
    if weak_areas:
        recommendation = "Revisit a worked example and try the practice for " + weak_areas[0]["title"] + "."
    elif recent:
        recommendation = "Continue with the next available chapter in the student's curriculum."
    else:
        recommendation = "Start a lesson to gather progress for the weekly report."
    return {"role": role, "subjects": [subjects[key] for key in sorted(subjects)], "weak_areas": weak_areas,
            "week": {"chapters_active": recent, "chapters_mastered": mastered_recently},
            "recommendation": recommendation}
