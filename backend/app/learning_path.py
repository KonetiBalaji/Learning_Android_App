"""Current product catalog and prerequisite policy, not a board curriculum mapping."""

from dataclasses import dataclass


CATALOG_VERSION = 'foundation-2026-09'
SUPPORTED_GRADES = frozenset({8})


@dataclass(frozen=True)
class CatalogChapter:
    id: str
    title: str
    prerequisite_id: str | None = None


@dataclass(frozen=True)
class CatalogSubject:
    id: str
    title: str
    chapters: tuple[CatalogChapter, ...]


CATALOG = (
    CatalogSubject('math', 'Mathematics', (
        CatalogChapter('fractions', 'Fractions'), CatalogChapter('decimals', 'Decimals'),
        CatalogChapter('percentages', 'Percentages'), CatalogChapter('algebra', 'Algebra'),
        CatalogChapter('geometry', 'Geometry', 'algebra'),
    )),
    CatalogSubject('science', 'Science', (
        CatalogChapter('cells', 'Cells and Living Things'), CatalogChapter('matter', 'Matter and Materials'),
        CatalogChapter('force-and-motion', 'Force and Motion'),
        CatalogChapter('ecosystems', 'Ecosystems', 'force-and-motion'),
    )),
    CatalogSubject('english', 'English', (
        CatalogChapter('grammar', 'Grammar'), CatalogChapter('reading-comprehension', 'Reading Comprehension'),
        CatalogChapter('vocabulary', 'Vocabulary'), CatalogChapter('writing', 'Writing', 'vocabulary'),
    )),
    CatalogSubject('social', 'Social Studies', (
        CatalogChapter('geography', 'Geography'), CatalogChapter('history', 'History'),
        CatalogChapter('civics', 'Civics'), CatalogChapter('economics', 'Economics', 'civics'),
    )),
)


def catalog_chapter(subject_id: str, chapter_id: str) -> CatalogChapter | None:
    subject_id, chapter_id = subject_id.strip().lower(), chapter_id.strip().lower()
    return next((chapter for subject in CATALOG if subject.id == subject_id
                 for chapter in subject.chapters if chapter.id == chapter_id), None)

# Mirror the four explicitly locked chapters in the existing Android catalog.
# Other catalog chapters remain open until a curriculum-specific path is agreed.
PREREQUISITES = {(subject.id, chapter.id): chapter.prerequisite_id
                 for subject in CATALOG for chapter in subject.chapters
                 if chapter.prerequisite_id is not None}


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


def unlocks_dependent_chapter(subject_id: str, mastered_chapter_id: str) -> bool:
    """Return whether this catalog chapter is a prerequisite for a gated sibling."""
    subject_id, mastered_chapter_id = subject_id.lower(), mastered_chapter_id.lower()
    return any(subject == subject_id and required == mastered_chapter_id
               for (subject, _chapter), required in PREREQUISITES.items())
