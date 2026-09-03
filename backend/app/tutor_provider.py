from __future__ import annotations

import json
from typing import Protocol

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .config import Settings
from .mastery_service import DiagnosticItem, diagnostic_bank, evaluate_rewrite, tutor_for, validate_diagnostic_bank
from .schemas import TutorIntervention
from .rewrite_grading import FULL_MARKS, GradeResult, grading_prompts, learner_feedback
from .diagnostic_quality import review_diagnostic_answers


class RewriteAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    understood: bool
    coaching: str | None = Field(default=None, max_length=500)
    score: int | None = Field(default=None, ge=0, le=FULL_MARKS)
    feedback: str | None = Field(default=None, max_length=500)
    available: bool = True


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

    def __init__(self, api_key: str, model: str, interests: tuple[str, ...] = ()) -> None:
        self.client = OpenAI(api_key=api_key, timeout=20.0, max_retries=1)
        self.model = model
        self.interests = interests

    def explain(self, grade: int, item: DiagnosticItem, selected_option: str) -> TutorIntervention:
        schema = TutorIntervention.model_json_schema()
        response = self.client.responses.create(
            model=self.model,
            store=False,
            instructions=(
                "You are a patient school tutor. Return only the requested structured response. "
                "Use short, accurate, age-appropriate language. Never shame the learner. "
                "Address the learner directly and explain the next step neutrally; avoid verdicts such as "
                "'You added wrong' or referring to 'the student'. Do not assume how they made the error. "
                "Do not introduce facts beyond the supplied concept and verified correct method. "
                "When relevant, frame the worked example using one supplied interest. Do not force an analogy, "
                "infer personal traits, change the mathematical method, or change the practice question. "
                "In fraction examples explicitly identify the same whole and equal-sized parts throughout. "
                "Keep units consistent: an area fraction cannot become a fraction of a count of flowers. "
                "A changed denominator changes part size, not necessarily the whole. "
                "Use everyday contexts without unsupported domain facts: for music use equal portions "
                "of listening time, not note values, time signatures or beat definitions. "
                "State what quantity is added or removed, and use simple plausible hypothetical scenarios."
            ),
            input=(
                f"Grade: {grade}\nConcept: {item.concept}\nQuestion: {item.prompt}\n"
                f"Student answer: {selected_option}\nCorrect answer: {item.correct_option}\n"
                f"Verified method: {item.explanation}\nVerified example: {item.worked_example}\n"
                f"Optional learner interests: {json.dumps(getattr(self, 'interests', ()))}\n"
                f"Unchanged practice question: {item.practice_prompt}"
            ),
            text={"format": {"type": "json_schema", "name": "tutor_intervention", "strict": True, "schema": schema}},
        )
        return TutorIntervention.model_validate(json.loads(response.output_text)).model_copy(update={'practice_prompt': item.practice_prompt})

    def assess_rewrite(self, grade: int, item: DiagnosticItem, response_text: str) -> RewriteAssessment:
        schema = GradeResult.model_json_schema()
        system, payload = grading_prompts(grade, item, response_text)
        response = self.client.responses.create(
            model=self.model,
            store=False,
            instructions=system,
            input=payload,
            text={"format": {"type": "json_schema", "name": "rewrite_assessment", "strict": True, "schema": schema}},
        )
        result = GradeResult.model_validate_json(response.output_text)
        feedback = learner_feedback(result)
        return RewriteAssessment(
            understood=result.score == FULL_MARKS, score=result.score, feedback=feedback,
            coaching=feedback if result.score < FULL_MARKS else None,
        )

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
        validate_diagnostic_bank(items)
        review_diagnostic_answers(self.client, self.model, grade, subject_id, chapter_id, items)
        return items


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
            # An outage is not evidence of understanding. Never grant fallback credit.
            return RewriteAssessment(understood=False, available=False)

    def diagnostic_bank(self, grade: int, subject_id: str, chapter_id: str) -> tuple[DiagnosticItem, ...]:
        try:
            return self.primary.diagnostic_bank(grade, subject_id, chapter_id)
        except Exception:
            return self.fallback.diagnostic_bank(grade, subject_id, chapter_id)


def tutor_provider(settings: Settings, interests: tuple[str, ...] = ()) -> TutorProvider:
    deterministic = DeterministicTutorProvider()
    if settings.ai_mode != "openai" or not settings.openai_api_key:
        return deterministic
    return ResilientTutorProvider(OpenAITutorProvider(settings.openai_api_key, settings.openai_model, interests), deterministic)
