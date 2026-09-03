import pytest

from app.tutor_conversation import TutorAnswer
from scripts.serve_qa import scripted_tutor_answer


def test_scripted_reply_is_labelled_and_matches_wire_contract():
    reply = TutorAnswer.model_validate(scripted_tutor_answer('Why keep the denominator?'))
    assert reply.answer.startswith('Scripted QA reply:')
    assert reply.supported is True


def test_explicit_qa_question_injects_unavailability():
    with pytest.raises(RuntimeError, match='Scripted QA tutor outage'):
        scripted_tutor_answer('QA unavailable')
