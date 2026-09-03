from __future__ import annotations

import json
from typing import Protocol

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .config import Settings
from .mastery_service import DiagnosticItem, diagnostic_bank, evaluate_rewrite, tutor_for, validate_diagnostic_bank
from .schemas import TutorIntervention


class RewriteAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    understood: bool
    coaching: str | None = Field(default=None, max_length=500)


class GeneratedDiagnosticItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=10, max_length=500)
    options: list[str] = Field(min_length=4, max_length=4)
    correct_option: str = Field(min_length=1, max_length=200)
    concept: str = Field(min_length=2, max_length=100)
    explanation: str = Field(min_length=10, max_length=700)
    worked_example: str = Field(min_length=5, max_length=500)
    hint: str = Field(min_length=5, max_length=300)
    practice_prompt: str = Field(min_length=5, max_length=500)
    practice_answers: list[str] = Field(min_length=1, max_length=5)

    @field_validator("options")
    @classmethod
    def choices_are_unique(cls, value: list[str]) -> list[str]:
        if len({choice.strip().lower() for choice in value}) != 4:
            raise ValueError("choices must be unique")
        return value

    @model_validator(mode="after")
    def answer_is_a_choice(self):
        if self.correct_option not in self.options:
            raise ValueError("correct_option must exactly match one option")
        return self


class GeneratedDiagnosticBank(BaseModel):
    model_config = ConfigDict(extra="forbid")

    questions: list[GeneratedDiagnosticItem] = Field(min_length=3, max_length=3)


class TutorProvider(Protocol):
    name: str

    def explain(self, grade: int, item: DiagnosticItem, selected_option: str) -> TutorIntervention: ...

    def assess_rewrite(self, grade: int, item: DiagnosticItem, response: str) -> RewriteAssessment: ...

    def diagnostic_bank(self, grade: int, subject_id: str, chapter_id: str) -> tuple[DiagnosticItem, ...]: ...


class DeterministicTutorProvider:
    name = "deterministic"

    def explain(self, grade: int, item: DiagnosticItem, selected_option: str) -> TutorIntervention:
        return tutor_for(item)

    def assess_rewrite(self, grade: int, item: DiagnosticItem, response: str) -> RewriteAssessment:
        understood, coaching = evaluate_rewrite(response, item.concept)
        return RewriteAssessment(understood=understood, coaching=coaching)

    def diagnostic_bank(self, grade: int, subject_id: str, chapter_id: str) -> tuple[DiagnosticItem, ...]:
        return diagnostic_bank(subject_id, chapter_id)


class OpenAITutorProvider:
    name = "openai"

    def __init__(self, api_key: str, model: str) -> None:
        self.client = OpenAI(api_key=api_key, timeout=20.0, max_retries=1)
        self.model = model

    def explain(self, grade: int, item: DiagnosticItem, selected_option: str) -> TutorIntervention:
        schema = TutorIntervention.model_json_schema()
        response = self.client.responses.create(
            model=self.model,
            store=False,
            instructions=(
                "You are a patient school tutor. Return only the requested structured response. "
                "Use short, accurate, age-appropriate language. Never shame the learner. "
                "Do not introduce facts beyond the supplied concept and verified correct method."
            ),
            input=(
                f"Grade: {grade}\nConcept: {item.concept}\nQuestion: {item.prompt}\n"
                f"Student answer: {selected_option}\nCorrect answer: {item.correct_option}\n"
                f"Verified method: {item.explanation}\nVerified example: {item.worked_example}"
            ),
            text={"format": {"type": "json_schema", "name": "tutor_intervention", "strict": True, "schema": schema}},
        )
        return TutorIntervention.model_validate(json.loads(response.output_text))

    def assess_rewrite(self, grade: int, item: DiagnosticItem, response_text: str) -> RewriteAssessment:
        schema = RewriteAssessment.model_json_schema()
        response = self.client.responses.create(
            model=self.model,
            store=False,
            instructions=(
                "Evaluate conceptual understanding for a school learner. Return only the requested structure. "
                "Accept accurate wording variations that demonstrate the supplied concept and connect it to the "
                "verified example. If incomplete, give one actionable hint without supplying a full answer."
            ),
            input=(f"Grade: {grade}\nConcept: {item.concept}\nOriginal question: {item.prompt}\n"
                   f"Correct answer: {item.correct_option}\nVerified explanation: {item.explanation}\n"
                   f"Student response: {response_text}"),
            text={"format": {"type": "json_schema", "name": "rewrite_assessment", "strict": True, "schema": schema}},
        )
        return RewriteAssessment.model_validate(json.loads(response.output_text))

    def diagnostic_bank(self, grade: int, subject_id: str, chapter_id: str) -> tuple[DiagnosticItem, ...]:
        schema = GeneratedDiagnosticBank.model_json_schema()
        response = self.client.responses.create(
            model=self.model,
            store=False,
            instructions=(
                "Create a short school diagnostic and return only the requested structured response. "
                "Write exactly three distinct multiple-choice questions with exactly four short, unique options. "
                "There must be one unambiguous correct option that exactly matches an option. Questions must be "
                "factually accurate, age-appropriate, curriculum-neutral, and test foundational understanding. "
                "Include one short reinforcement practice prompt and one to five concise acceptable answers. "
                "Explanations, examples, and hints must teach without shaming. Do not mention being an AI."
            ),
            input=f"Grade: {grade}\nSubject: {subject_id}\nChapter or topic: {chapter_id}",
            text={"format": {"type": "json_schema", "name": "diagnostic_bank", "strict": True, "schema": schema}},
        )
        generated = GeneratedDiagnosticBank.model_validate(json.loads(response.output_text))
        items = tuple(
            DiagnosticItem(
                prompt=item.prompt, options=tuple(item.options), correct_option=item.correct_option,
                concept=item.concept, explanation=item.explanation,
                worked_example=item.worked_example, hint=item.hint,
                practice_prompt=item.practice_prompt, practice_answers=tuple(item.practice_answers),
            ) for item in generated.questions
        )
        return validate_diagnostic_bank(items)


class ResilientTutorProvider:
    def __init__(self, primary: TutorProvider, fallback: TutorProvider) -> None:
        self.primary = primary
        self.fallback = fallback
        self.name = primary.name

    def explain(self, grade: int, item: DiagnosticItem, selected_option: str) -> TutorIntervention:
        try:
            return self.primary.explain(grade, item, selected_option)
        except Exception:
            return self.fallback.explain(grade, item, selected_option)

    def assess_rewrite(self, grade: int, item: DiagnosticItem, response: str) -> RewriteAssessment:
        try:
            return self.primary.assess_rewrite(grade, item, response)
        except Exception:
            return self.fallback.assess_rewrite(grade, item, response)

    def diagnostic_bank(self, grade: int, subject_id: str, chapter_id: str) -> tuple[DiagnosticItem, ...]:
        try:
            return self.primary.diagnostic_bank(grade, subject_id, chapter_id)
        except Exception:
            return self.fallback.diagnostic_bank(grade, subject_id, chapter_id)


def tutor_provider(settings: Settings) -> TutorProvider:
    deterministic = DeterministicTutorProvider()
    if settings.ai_mode != "openai" or not settings.openai_api_key:
        return deterministic
    return ResilientTutorProvider(OpenAITutorProvider(settings.openai_api_key, settings.openai_model), deterministic)
