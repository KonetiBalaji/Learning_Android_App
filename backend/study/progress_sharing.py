"""Limited curriculum reports shared through explicit, account-scoped invitations."""

import hashlib

from . import mastery


def digest(code):
    return hashlib.sha256(code.encode()).hexdigest()


def report(lessons, role, now):
    chapters = mastery.catalog(lessons)
    lessons_by_chapter = {lesson["chapter_id"]: lesson for lesson in lessons}
    cutoff = now - 7 * 86400
    subjects = {}
    for chapter in chapters:
        key = (chapter["grade"], chapter["subject"])
        summary = subjects.setdefault(key, {
            "grade": key[0], "subject": key[1], "available": 0, "mastered": 0,
            "week_active": 0, "week_mastered": 0,
        })
        lesson = lessons_by_chapter.get(chapter["id"], {})
        summary["week_active"] += int(cutoff <= lesson.get("last_activity", 0) <= now)
        summary["week_mastered"] += int(cutoff <= lesson.get("mastered_at", 0) <= now)
        summary["available"] += 1
        summary["mastered"] += int(chapter["mastered"])
    priorities = sorted((chapter for chapter in chapters if chapter["needs_practice"]),
                        key=lambda chapter: -chapter["review_events"])
    weak_areas = [{key: chapter[key] for key in ("grade", "subject", "title")} for chapter in priorities]
    recent = sum(subject["week_active"] for subject in subjects.values())
    mastered_recently = sum(subject["week_mastered"] for subject in subjects.values())
    if weak_areas:
        recommendation = "Revisit a worked example and try the practice for " + weak_areas[0]["title"] + "."
    elif recent:
        recommendation = "Continue with the next available chapter in the student's curriculum."
    else:
        recommendation = "Start a lesson to gather progress for the weekly report."
    return {"role": role, "subjects": [subjects[key] for key in sorted(subjects)], "weak_areas": weak_areas,
            "week": {"chapters_active": recent, "chapters_mastered": mastered_recently},
            "recommendation": recommendation}
