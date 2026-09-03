"""Current app prerequisite policy, not an authoritative curriculum mapping."""

# Mirror the four explicitly locked chapters in the existing Android catalog.
# Other catalog chapters remain open until a curriculum-specific path is agreed.
PREREQUISITES = {
    ('math', 'geometry'): 'algebra',
    ('science', 'ecosystems'): 'force-and-motion',
    ('english', 'writing'): 'vocabulary',
    ('social', 'economics'): 'civics',
}


def missing_prerequisite(db, owner_id: str, grade: int, subject_id: str, chapter_id: str) -> str | None:
    subject_id, chapter_id = subject_id.lower(), chapter_id.lower()
    required = PREREQUISITES.get((subject_id, chapter_id))
    if required is None:
        return None
    latest = db.execute(
        '''SELECT status FROM mastery_sessions
           WHERE owner_id = ? AND grade = ? AND subject_id = ? AND chapter_id = ?
           ORDER BY started_at DESC, rowid DESC LIMIT 1''',
        (owner_id, grade, subject_id, required),
    ).fetchone()
    return None if latest is not None and latest['status'] == 'mastered' else required
