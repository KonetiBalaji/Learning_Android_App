from dataclasses import asdict

from app.mastery_service import DiagnosticItem
from scripts.evaluate_catalog_diagnostics import CASES


def test_catalog_evaluator_covers_every_exposed_chapter_once():
    assert len(CASES) == 17
    assert len({(subject, chapter) for subject, chapter, _title in CASES}) == len(CASES)
    assert {subject for subject, _chapter, _title in CASES} == {'math', 'science', 'english', 'social'}
    assert all(chapter and title for _subject, chapter, title in CASES)


def test_diagnostic_items_use_dataclass_serialization():
    item = DiagnosticItem('Prompt?', ('A', 'B', 'C', 'D'), 'A', 'Concept',
                          'Explanation', 'Example', 'Hint', 'Practice?', ('Answer',))
    assert asdict(item)['practice_answers'] == ('Answer',)
