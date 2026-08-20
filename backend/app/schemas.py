from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


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
