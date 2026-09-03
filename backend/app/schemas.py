from __future__ import annotations
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from .quiz_difficulty import Difficulty
from .question_types import QuestionType


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


class ChapterPreview(BaseModel):
    document_id: str
    chapter_id: str
    title: str
    page: int
    total_pages: int
    start_character: int
    end_character: int
    text: str


class SourceRange(BaseModel):
    model_config = ConfigDict(extra='forbid')

    chapter_id: str = Field(min_length=1, max_length=200)
    start_character: int = Field(ge=0, strict=True)
    end_character: int = Field(gt=0, strict=True)


class SourceSearchRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    chapter_ids: list[str] = Field(min_length=1)
    query: str = Field(min_length=2, max_length=120)
    limit: int = Field(default=20, ge=1, le=20, strict=True)


class PdfPage(BaseModel):
    page: int
    start_character: int
    end_character: int
    has_text: bool


class PdfPageIndex(BaseModel):
    document_id: str
    pages: list[PdfPage]


class PdfPageRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    first_page: int = Field(ge=1, strict=True)
    last_page: int = Field(ge=1, strict=True)


class PdfPageSelection(BaseModel):
    document_id: str
    first_page: int
    last_page: int
    chapter_ids: list[str]
    source_ranges: list[SourceRange]
    empty_pages: list[int]


class SourceSearchHit(SourceRange):
    title: str
    text: str
    match_start: int
    match_end: int
    context_truncated: bool


class SourceSearchResults(BaseModel):
    document_id: str
    query: str
    matches: list[SourceSearchHit]
    has_more: bool
    match_mode: str = 'literal_case_insensitive'


class QuizRequest(BaseModel):
    request_id: UUID | None = None
    question_type: QuestionType = 'multiple_choice'
    difficulty: Difficulty | None = None
    chapter_ids: list[str] = Field(min_length=1)
    source_ranges: list[SourceRange] | None = Field(default=None, min_length=1, max_length=50)
    question_count: int = Field(default=10, ge=5, le=20)


class QuizQuestion(BaseModel):
    question_type: QuestionType = 'multiple_choice'
    id: str
    ordinal: int
    prompt: str
    options: list[str]
    source_reference: str


class QuizSummary(BaseModel):
    source_ranges: list[SourceRange] | None = None
    question_type: QuestionType = 'multiple_choice'
    difficulty: Difficulty | None = None
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


class DocumentQuizState(BaseModel):
    source_ranges: list[SourceRange] | None = None
    question_type: QuestionType = 'multiple_choice'
    difficulty: Difficulty | None = None
    id: str
    document: DocumentSummary
    total: int
    answered: int
    question: QuizQuestion | None
    last_feedback: Feedback | None


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
    state_token: str
    id: str
    status: str
    question: AdaptiveQuestion


class DiagnosticAnswerRequest(BaseModel):
    expected_state: str | None = Field(default=None, min_length=1, max_length=200)
    selected_option: str = Field(min_length=1, max_length=400)


class TutorIntervention(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    explanation: str
    worked_example: str
    hint: str
    practice_prompt: str


class DiagnosticOutcome(BaseModel):
    state_token: str
    correct: bool
    selected_option: str
    correct_option: str
    mastery_score: float
    next_action: str
    next_question: AdaptiveQuestion | None = None
    tutor: TutorIntervention | None = None


class PracticeRequest(BaseModel):
    fresh_practice: bool = False
    expected_state: str | None = Field(default=None, min_length=1, max_length=200)
    response: str = Field(min_length=1, max_length=400)


class PracticeOutcome(BaseModel):
    next_practice: TutorIntervention | None = None
    state_token: str
    correct: bool
    normalized_answer: str
    hint: str | None = None
    next_action: str


class RewriteRequest(BaseModel):
    fresh_practice: bool = False
    expected_state: str | None = Field(default=None, min_length=1, max_length=200)
    response: str = Field(min_length=1, max_length=4000)


class RewriteOutcome(BaseModel):
    next_practice: TutorIntervention | None = None
    state_token: str
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
    state_token: str
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


class StudyPresence(BaseModel):
    session_id: str
    observed_study_seconds: int = Field(ge=0)


class ProgressDashboard(BaseModel):
    observed_study_seconds: int = Field(default=0, ge=0)
    grade: int | None = None
    unlocked_chapter_ids: list[str] = Field(default_factory=list)
    subjects: dict[str, float]
    chapters: list[ChapterProgress]
    weak_areas: list[str]
    recommendations: list[str]


class UserProfile(BaseModel):
    id: str
    email: EmailStr
    created_at: str
    interests: list[str] = Field(default_factory=list)


class WeeklyReport(BaseModel):
    observed_study_seconds: int = Field(default=0, ge=0)
    period_days: int
    period_start: str
    period_end: str
    readiness_is_calibrated: bool = False
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
