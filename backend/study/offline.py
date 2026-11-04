"""Reconstruct device recall questions; never trust a client score or answer key."""
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .documents import retrieve
from .quizzes import GenerationError, validate


class OfflineSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    section_ids: list[str] = Field(default_factory=list, max_length=100)
    page_start: int | None = None
    page_end: int | None = None


class DeviceQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    source_id: str = Field(min_length=1, max_length=100)
    prompt: str = Field(min_length=1, max_length=50000)
    choices: list[str] = Field(min_length=2, max_length=4)
    type: Literal["multiple_choice", "true_false", "yes_no"]
    selected: int = Field(ge=0, le=3)


class OfflineAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    local_id: str = Field(min_length=8, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    source_fingerprint: str = Field(min_length=64, max_length=64, pattern=r"^[a-f0-9]+$")
    selection: OfflineSelection = Field(default_factory=OfflineSelection)
    questions: list[DeviceQuestion] = Field(min_length=1, max_length=50)


def reconstruct(document: dict, attempt: OfflineAttempt) -> tuple[list[dict], list[dict]]:
    passages = retrieve(document, attempt.selection.model_dump())
    sources = {p["id"]: p for p in passages}
    words = re.compile(r"\b[A-Za-z][A-Za-z-]{4,}\b")
    pool = {match.group().lower() for p in passages for match in words.finditer(p["text"])}
    questions, answers, seen_sources = [], [], set()
    for candidate in attempt.questions:
        source = sources.get(candidate.source_id)
        if source is None or source["text"].casefold() in seen_sources:
            raise GenerationError("Offline question repeats a passage or crosses the selected material.")
        quote = source["text"]
        matches = list(words.finditer(quote))
        if len(quote.split()) < 7 or not matches or len(pool) < 4:
            raise GenerationError("The source cannot support this offline question.")
        word = max(matches, key=lambda match: len(match.group()))
        actual = word.group()
        alternatives = pool - {actual.lower()}
        if any(len(choice) > 200 for choice in candidate.choices):
            raise GenerationError("Offline choice exceeds the supported length.")
        if candidate.type == "multiple_choice":
            expected = 'Which word completes this exact passage?\n“' + quote[:word.start()] + "_____" + quote[word.end():] + '”'
            if candidate.prompt != expected or len(candidate.choices) != 4 or candidate.choices.count(actual) != 1:
                raise GenerationError("Offline question does not match its original passage.")
            if any(choice != actual and choice not in alternatives for choice in candidate.choices):
                raise GenerationError("Offline distractors do not come from the selected material.")
            answer = candidate.choices.index(actual)
        else:
            prefix = 'Does this exactly match the source passage?\n“' if candidate.type == "yes_no" else 'True or false: this exactly matches the source passage.\n“'
            expected_choices = ["Yes", "No"] if candidate.type == "yes_no" else ["True", "False"]
            if candidate.choices != expected_choices or not candidate.prompt.startswith(prefix) or not candidate.prompt.endswith('”'):
                raise GenerationError("Offline binary question has invalid wording or choices.")
            shown = candidate.prompt[len(prefix):-1]
            answer = 0 if shown == quote else 1
            if answer == 1:
                before, after = quote[:word.start()], quote[word.end():]
                end = len(shown) - len(after) if after else len(shown)
                replacement = shown[len(before):end]
                if not shown.startswith(before) or not shown.endswith(after) or replacement not in alternatives:
                    raise GenerationError("Offline binary question alters unsupported source text.")
        if candidate.selected >= len(candidate.choices):
            raise GenerationError("Offline answer is outside the available choices.")
        question = {"id": f"q{len(questions)}", "prompt": candidate.prompt, "choices": candidate.choices,
                    "answer": answer, "type": candidate.type, "source_id": source["id"], "quote": quote,
                    "section_id": source["section_id"], "concept": source["section_id"], "page": source["page"],
                    "difficulty": "easy", "explanation": f'The original passage says: “{quote}” Read it again and connect the missing word to its context.'}
        questions.append(question)
        answers.append({"question_id": question["id"], "selected": candidate.selected, "correct": candidate.selected == answer,
                        "answer": answer, "explanation": question["explanation"], "quote": quote})
        seen_sources.add(quote.casefold())
    validate(questions, passages, len(attempt.questions))
    return questions, answers
