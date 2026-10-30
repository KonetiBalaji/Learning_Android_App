import pytest

from study.document_tutor import NO_SUPPORT, TutorDraft, reply
from study.provider import Review
from study.quizzes import GenerationError

HITS = [{"source_id": "p1", "quote": "Mitochondria produce energy.", "page": 2, "section_id": "s1", "start": 10, "end": 38, "score": 0.8}]


class Provider:
    def __init__(self, draft, approved=True):
        self.draft = draft
        self.approved = approved

    def structured(self, instruction, payload, output):
        return self.draft if output is TutorDraft else Review(approved=[self.approved])


def test_below_threshold_never_calls_provider_or_invents_citations():
    class MustNotCall:
        def structured(self, *args):
            raise AssertionError("No source support must avoid provider calls")
    result = reply("unsupported question", [], MustNotCall())
    assert result["answer"] == NO_SUPPORT and not result["has_support"] and result["citations"] == []


def test_local_tutor_quotes_source_without_claiming_a_generated_explanation():
    result = reply("Which structure produces energy?", HITS)
    assert result["mode"] == "source_excerpt"
    assert HITS[0]["quote"] in result["answer"]
    assert result["citations"][0]["source_id"] == "p1"


def test_grounded_reviewed_answer_preserves_exact_source_offsets():
    draft = TutorDraft(has_support=True, answer="The passage identifies mitochondria as producing energy.",
                       citations=[{"source_id": "p1", "quote": "produce energy."}])
    result = reply("What produces energy?", HITS, Provider(draft))
    assert result["mode"] == "openai"
    assert result["citations"][0]["start"] == 23 and result["citations"][0]["end"] == 38


@pytest.mark.parametrize("citation,approved", [({"source_id": "invented", "quote": "Mitochondria"}, True),
                                            ({"source_id": "p1", "quote": "Mitochondria cause cancer."}, True),
                                            ({"source_id": "p1", "quote": "produce energy."}, False)])
def test_invalid_or_contradictory_ai_answer_is_discarded(citation, approved):
    draft = TutorDraft(has_support=True, answer="An unchecked answer must not be displayed.", citations=[citation])
    result = reply("question", HITS, Provider(draft, approved))
    assert result["mode"] == "source_excerpt" and "unchecked" not in result["answer"]
    assert result["notice"]


def test_provider_failure_exposes_only_safe_source_fallback():
    class Unavailable:
        def structured(self, *args):
            raise GenerationError("private upstream failure")
    result = reply("question", HITS, Unavailable())
    assert result["mode"] == "source_excerpt" and "private" not in result["notice"]
