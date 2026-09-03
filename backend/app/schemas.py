from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class Chapter(BaseModel):
    id: str
    title: str
    start_character: int
    end_character: int
    confidence: float


class DocumentSummary(BaseModel):
    id: str
    original_name: str
    chapters: list[Chapter]


class QuizRequest(BaseModel):
    chapter_ids: list[str] = Field(min_length=1)
    question_count: int = Field(default=10, ge=5, le=20)


class QuizQuestion(BaseModel):
    id: str
    ordinal: int
    prompt: str
    options: list[str]
    source_reference: str


class QuizSummary(BaseModel):
    id: str
    title: str
    question_count: int
    first_question: QuizQuestion | None


class AnswerRequest(BaseModel):
    selected_option: str = Field(min_length=1, max_length=4000)


class Feedback(BaseModel):
    correct: bool
    selected_option: str
    correct_option: str
    explanation: str
    source_reference: str
    next_question: QuizQuestion | None


class QuizResults(BaseModel):
    quiz_id: str
    answered: int
    total: int
    correct: int
    accuracy: float
    mistakes: list[QuizQuestion]


class DiagnosticStartRequest(BaseModel):
    grade: int = Field(ge=1, le=12)
    subject_id: str = Field(min_length=1, max_length=80)
    chapter_id: str = Field(min_length=1, max_length=80)


class AdaptiveQuestion(BaseModel):
    ordinal: int
    total: int
    prompt: str
    options: list[str]
    concept: str


class DiagnosticSession(BaseModel):
    id: str
    status: str
    question: AdaptiveQuestion


class DiagnosticAnswerRequest(BaseModel):
    selected_option: str = Field(min_length=1, max_length=400)


class TutorIntervention(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    explanation: str
    worked_example: str
    hint: str
    practice_prompt: str


class DiagnosticOutcome(BaseModel):
    correct: bool
    selected_option: str
    correct_option: str
    mastery_score: float
    next_action: str
    next_question: AdaptiveQuestion | None = None
    tutor: TutorIntervention | None = None


class PracticeRequest(BaseModel):
    response: str = Field(min_length=1, max_length=400)


class PracticeOutcome(BaseModel):
    correct: bool
    normalized_answer: str
    hint: str | None = None
    next_action: str


class RewriteRequest(BaseModel):
    response: str = Field(min_length=1, max_length=4000)


class RewriteOutcome(BaseModel):
    understood: bool
    mastery_achieved: bool
    mastery_score: float
    confidence: str
    coaching: str | None = None
    next_chapter_unlocked: bool
    next_action: str
    next_question: AdaptiveQuestion | None = None
    assessment_points: int | None = None
    assessment_max_points: int | None = None
    assessment_feedback: str | None = None


class MasterySessionState(BaseModel):
    id: str
    grade: int
    subject_id: str
    chapter_id: str
    status: str
    question: AdaptiveQuestion | None
    tutor: TutorIntervention | None
    selected_option: str | None
    mastery_score: float
    coaching_rounds: int
    started_at: str
    assessment_points: int | None = None
    assessment_feedback: str | None = None


class ChapterProgress(BaseModel):
    grade: int
    subject_id: str
    chapter_id: str
    mastery: float
    attempts: int
    status: str


class ProgressDashboard(BaseModel):
    subjects: dict[str, float]
    chapters: list[ChapterProgress]
    weak_areas: list[str]
    recommendations: list[str]


class UserProfile(BaseModel):
    id: str
    email: EmailStr
    created_at: str


class WeeklyReport(BaseModel):
    period_days: int
    questions_answered: int
    correct_answers: int
    accuracy: float
    mastered_chapters: int
    active_subjects: int
    strongest_concepts: list[str]
    weak_areas: list[str]
    estimated_exam_readiness: float
    readiness_label: str
    recommendations: list[str]
