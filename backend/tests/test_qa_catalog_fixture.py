import pytest

from scripts.serve_qa import catalog_fixture_bank


def test_catalog_fixture_is_deterministic_and_routes_every_current_chapter():
    from app.learning_path import CATALOG
    from app.mastery_service import parse_diagnostic_bank, serialize_diagnostic_bank
    for subject in CATALOG:
        for chapter in subject.chapters:
            first = catalog_fixture_bank(8, subject.id, chapter.id)
            second = catalog_fixture_bank(8, subject.id, chapter.id)
            assert first == second
            assert parse_diagnostic_bank(serialize_diagnostic_bank(first)) == first
            assert len(first) == 3
            assert first[0].options[0] != first[0].correct_option
            assert chapter.title in first[0].prompt


@pytest.mark.parametrize('grade,subject,chapter', [
    (7, 'math', 'fractions'),
    (8, 'unknown', 'fractions'),
    (8, 'math', 'unknown'),
])
def test_catalog_fixture_fails_closed_outside_current_grade_8_catalog(grade, subject, chapter):
    with pytest.raises(ValueError, match='Grade 8'):
        catalog_fixture_bank(grade, subject, chapter)
