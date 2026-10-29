import json

import httpx
import pytest

from study.provider import OpenAIProvider, bounded_context, configured_provider
from study.quizzes import GenerationError

PASSAGES = [{"id": "p0", "page": 2, "section_id": "s1", "text": "Mitochondria produce energy."}]
QUESTION = {"prompt": "Which structure produces energy?", "choices": ["Mitochondria", "Ribosomes", "Vacuoles", "Membranes"],
            "answer": 0, "type": "multiple_choice", "source_id": "p0", "quote": "Mitochondria produce energy.",
            "explanation": "The passage explicitly identifies mitochondria as the energy-producing structure.", "concept": "Cells", "difficulty": "easy"}


def completed(value):
    return {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(value)}]}]}


def test_provider_structured_generation_and_independent_review():
    requests = []
    def respond(request):
        body = json.loads(request.content)
        requests.append(body)
        assert request.url == "https://api.openai.com/v1/responses"
        assert body["store"] is False
        assert body["text"]["format"]["strict"] is True
        return httpx.Response(200, json=completed({"questions": [QUESTION]} if len(requests) == 1 else {"approved": [True]}))
    provider = OpenAIProvider("test-not-a-real-key", "configured-model", httpx.MockTransport(respond))
    result = provider.generate(PASSAGES, 1, "multiple_choice", "easy")
    assert result[0]["page"] == 2 and result[0]["id"] == "q0"
    assert len(requests) == 2


@pytest.mark.parametrize("status", [401, 429, 500])
def test_provider_errors_are_redacted(status):
    provider = OpenAIProvider("private", "model", httpx.MockTransport(lambda _: httpx.Response(status, text="secret server body")))
    with pytest.raises(GenerationError) as error:
        provider.generate(PASSAGES, 1, "multiple_choice", "easy")
    assert "secret" not in str(error.value) and "private" not in str(error.value)


@pytest.mark.parametrize("response", [{"status": "incomplete"}, {"status": "completed", "output": [{"content": [{"type": "refusal"}]}]}, completed({"questions": []})])
def test_incomplete_refusal_and_wrong_count(response):
    provider = OpenAIProvider("unused", "model", httpx.MockTransport(lambda _: httpx.Response(200, json=response)))
    with pytest.raises(GenerationError):
        provider.generate(PASSAGES, 1, "multiple_choice", "easy")


def test_review_rejects_ambiguous_questions():
    replies = iter([completed({"questions": [QUESTION]}), completed({"approved": [False]})])
    provider = OpenAIProvider("unused", "model", httpx.MockTransport(lambda _: httpx.Response(200, json=next(replies))))
    with pytest.raises(GenerationError, match="review"):
        provider.generate(PASSAGES, 1, "multiple_choice", "easy")


def test_local_mode_needs_no_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("STUDY_GENERATION_MODE", "local_practice")
    assert configured_provider() is None
    monkeypatch.setenv("STUDY_GENERATION_MODE", "openai")
    with pytest.raises(RuntimeError):
        configured_provider()


def test_context_is_bounded_and_only_contains_selected_sources():
    selected = [{"id": str(i), "text": "x" * 1000} for i in range(1000)]
    context = bounded_context(selected)
    assert sum(len(p["text"]) for p in context) <= 24000
    assert all(p in selected for p in context)
