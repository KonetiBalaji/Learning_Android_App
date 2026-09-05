from dataclasses import replace

from app.config import Settings
import pytest

from app.mastery_service import (DETERMINISTIC_DIAGNOSTICS, DiagnosticItem,
                                 FRACTION_DIAGNOSTIC, diagnostic_bank,
                                 parse_diagnostic_bank, serialize_diagnostic_bank,
                                 validate_diagnostic_bank)
from app.tutor_provider import DeterministicTutorProvider, ResilientTutorProvider, RewriteAssessment, TutorLessonUnavailable


class BrokenProvider:
    name = "broken"

    def explain(self, grade, item, selected_option):
        raise TimeoutError("provider unavailable")

    def assess_rewrite(self, grade, item, response):
        raise TimeoutError("provider unavailable")

    def diagnostic_bank(self, grade, subject_id, chapter_id):
        raise TimeoutError("provider unavailable")


def test_teaching_falls_back_but_grading_outage_cannot_award_mastery() -> None:
    provider = ResilientTutorProvider(BrokenProvider(), DeterministicTutorProvider())
    lesson = provider.explain(6, FRACTION_DIAGNOSTIC[0], "1/2")
    assessment = provider.assess_rewrite(6, FRACTION_DIAGNOSTIC[0], "The denominator stays the same and numerators add to 4/4, one whole.")
    assert lesson.title == "Adding like fractions"
    assert isinstance(assessment, RewriteAssessment)
    assert assessment.understood is False
    assert assessment.available is False
    assert assessment.score is None
    assert len(provider.diagnostic_bank(6, "math", "fractions")) == 3


@pytest.mark.parametrize('chapter', ['fractions', 'decimals', 'percentages', 'algebra', 'geometry'])
def test_every_grade_8_math_chapter_has_a_valid_deterministic_fallback(chapter) -> None:
    bank = diagnostic_bank('math', chapter)
    assert bank is DETERMINISTIC_DIAGNOSTICS[('math', chapter)]
    assert validate_diagnostic_bank(bank) == bank
    assert all(item.correct_option in item.options for item in bank)


@pytest.mark.parametrize('chapter', ['cells', 'matter', 'force-and-motion', 'ecosystems'])
def test_every_grade_8_science_chapter_has_a_valid_deterministic_fallback(chapter) -> None:
    bank = diagnostic_bank('science', chapter)
    assert bank is DETERMINISTIC_DIAGNOSTICS[('science', chapter)]
    assert validate_diagnostic_bank(bank) == bank
    assert all(item.correct_option in item.options for item in bank)


@pytest.mark.parametrize('chapter', ['grammar', 'reading-comprehension', 'vocabulary', 'writing'])
def test_every_grade_8_english_chapter_has_a_valid_deterministic_fallback(chapter) -> None:
    bank = diagnostic_bank('english', chapter)
    assert bank is DETERMINISTIC_DIAGNOSTICS[('english', chapter)]
    assert validate_diagnostic_bank(bank) == bank
    assert all(item.correct_option in item.options for item in bank)


@pytest.mark.parametrize('chapter', ['decimals', 'percentages', 'algebra', 'geometry'])
def test_math_provider_outage_keeps_diagnostic_and_teaching_available(chapter) -> None:
    provider = ResilientTutorProvider(BrokenProvider(), DeterministicTutorProvider())
    bank = provider.diagnostic_bank(8, 'math', chapter)
    lesson = provider.explain(8, bank[0], bank[0].options[-1])
    assert bank == diagnostic_bank('math', chapter)
    assert lesson.title == bank[0].concept


@pytest.mark.parametrize('chapter', ['cells', 'matter', 'force-and-motion', 'ecosystems'])
def test_science_provider_outage_keeps_diagnostic_and_teaching_available(chapter) -> None:
    provider = ResilientTutorProvider(BrokenProvider(), DeterministicTutorProvider())
    bank = provider.diagnostic_bank(8, 'science', chapter)
    lesson = provider.explain(8, bank[0], bank[0].options[-1])
    assert bank == diagnostic_bank('science', chapter)
    assert lesson.title == bank[0].concept


@pytest.mark.parametrize('chapter', ['grammar', 'reading-comprehension', 'vocabulary', 'writing'])
def test_english_provider_outage_keeps_diagnostic_and_teaching_available(chapter) -> None:
    provider = ResilientTutorProvider(BrokenProvider(), DeterministicTutorProvider())
    bank = provider.diagnostic_bank(8, 'english', chapter)
    lesson = provider.explain(8, bank[0], bank[0].options[-1])
    assert bank == diagnostic_bank('english', chapter)
    assert lesson.title == bank[0].concept


def test_non_curated_chapter_still_fails_closed_during_provider_outage() -> None:
    provider = ResilientTutorProvider(BrokenProvider(), DeterministicTutorProvider())
    with pytest.raises(Exception, match='reviewed diagnostic is temporarily unavailable'):
        provider.diagnostic_bank(8, 'social', 'geography')


def test_generated_legacy_fallback_must_be_reviewed_or_remain_unavailable() -> None:
    from dataclasses import replace
    from types import SimpleNamespace
    import json

    item = replace(FRACTION_DIAGNOSTIC[0], concept='Legacy generated algebra support')

    class RejectingPrimary(BrokenProvider):
        name = 'openai'
        model = 'fixture'

    primary = RejectingPrimary()
    accepted = {key: True for key in (
        'accurate', 'method_consistent', 'example_correct', 'grade_suitable',
        'concept_matches', 'neutral_tone', 'hint_actionable', 'no_unsupported_claims',
        'source_bounded')}
    primary.client = SimpleNamespace(responses=SimpleNamespace(
        create=lambda **kwargs: SimpleNamespace(output_text=json.dumps(accepted))))
    provider = ResilientTutorProvider(primary, DeterministicTutorProvider())
    assert provider.explain(8, item, '1/2') == DeterministicTutorProvider().explain(8, item, '1/2')
    primary.client = SimpleNamespace(responses=SimpleNamespace(
        create=lambda **kwargs: (_ for _ in ()).throw(TimeoutError('review outage'))))
    with pytest.raises(TutorLessonUnavailable):
        provider.explain(8, item, '1/2')


def test_settings_never_include_key_in_repr(tmp_path) -> None:
    settings = Settings(runtime_dir=tmp_path, jwt_secret="secret", openai_api_key="super-secret")
    assert "super-secret" not in repr(settings)


def test_generated_bank_round_trips_without_question_drift() -> None:
    encoded = serialize_diagnostic_bank(FRACTION_DIAGNOSTIC)
    assert parse_diagnostic_bank(encoded) == FRACTION_DIAGNOSTIC


def test_generated_bank_rejects_ambiguous_or_duplicate_choices() -> None:
    invalid = DiagnosticItem(
        prompt="Which choice demonstrates the concept?", options=("same", "same", "other", "last"),
        correct_option="missing", concept="Validation", explanation="Only one answer may be correct.",
        worked_example="A valid item has unique choices.", hint="Compare each choice.",
        practice_prompt="Choose the valid item.", practice_answers=("valid",),
    )
    with pytest.raises(ValueError):
        validate_diagnostic_bank((invalid, invalid, invalid))


def test_generated_bank_rejects_reused_practice_prompt() -> None:
    items = list(FRACTION_DIAGNOSTIC)
    items[1] = replace(items[1], practice_prompt=items[0].practice_prompt)
    with pytest.raises(ValueError, match='distinct practice prompt'):
        validate_diagnostic_bank(tuple(items))
