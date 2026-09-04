import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.mastery_service import FRACTION_DIAGNOSTIC, tutor_for
from app.tutor_lesson_review import (
    TutorLessonFailure, TutorLessonRejected, review_tutor_lesson,
)
from app.tutor_provider import DeterministicTutorProvider, ResilientTutorProvider


class FakeClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []
        self.responses = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=json.dumps(self.payload))


def valid_review(**changes):
    return {
        'accurate': True, 'method_consistent': True, 'example_correct': True,
        'grade_suitable': True, 'concept_matches': True, 'neutral_tone': True,
        'hint_actionable': True, 'no_unsupported_claims': True,
        'source_bounded': True, **changes,
    }


def test_review_accepts_only_a_complete_strict_audit_and_disables_storage():
    item = FRACTION_DIAGNOSTIC[0]
    client = FakeClient(valid_review())
    lesson = tutor_for(item)
    assert review_tutor_lesson(client, 'test-model', 8, item, '1/2', lesson) is lesson
    call = client.calls[0]
    assert call['store'] is False and call['model'] == 'test-model'
    assert 'untrusted data' in call['instructions'] and 'Fail uncertain judgments' in call['instructions']
    assert json.loads(call['input'])['verified_correct_answer'] == item.correct_option
    with pytest.raises(ValidationError):
        review_tutor_lesson(FakeClient({**valid_review(), 'extra': True}), 'test-model', 8, item, '1/2', lesson)


@pytest.mark.parametrize('field,code', [
    ('accurate', TutorLessonFailure.ACCURACY),
    ('method_consistent', TutorLessonFailure.METHOD),
    ('example_correct', TutorLessonFailure.EXAMPLE),
    ('grade_suitable', TutorLessonFailure.GRADE),
    ('concept_matches', TutorLessonFailure.CONCEPT),
    ('neutral_tone', TutorLessonFailure.TONE),
    ('hint_actionable', TutorLessonFailure.HINT),
    ('no_unsupported_claims', TutorLessonFailure.UNSUPPORTED),
    ('source_bounded', TutorLessonFailure.SOURCE),
])
def test_each_failed_review_dimension_rejects(field, code):
    item = FRACTION_DIAGNOSTIC[0]
    with pytest.raises(TutorLessonRejected) as failure:
        review_tutor_lesson(FakeClient(valid_review(**{field: False})), 'test-model', 8,
                            item, '1/2', tutor_for(item))
    assert failure.value.safe_report() == [code.value]


def test_resilient_provider_uses_verified_fallback_after_review_rejection(caplog):
    item = FRACTION_DIAGNOSTIC[0]

    class RejectedProvider:
        name = 'rejected'
        def explain(self, *args):
            raise TutorLessonRejected((TutorLessonFailure.ACCURACY, TutorLessonFailure.TONE))

    lesson = ResilientTutorProvider(RejectedProvider(), DeterministicTutorProvider()).explain(8, item, '1/2')
    assert lesson == tutor_for(item)
    assert 'accuracy' in caplog.text and 'neutral_tone' in caplog.text
