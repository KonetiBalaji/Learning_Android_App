from typing import Literal

from pydantic import BaseModel


class Section(BaseModel):
    id: str
    title: str
    parent_id: str | None = None


class DocumentMetadata(BaseModel):
    id: str
    title: str
    filename: str
    created: float
    page_count: int
    has_real_pages: bool
    structure_confidence: Literal["detected", "uncertain"]
    sections: list[Section]
    processing_state: Literal["ready", "needs_review"] = "ready"
    ocr_review_count: int = 0
    ocr_page_count: int = 0
    source_locked: bool = False


class PublicQuestion(BaseModel):
    id: str
    prompt: str
    choices: list[str]
    type: Literal["multiple_choice", "true_false", "yes_no"]
    source_id: str
    concept: str
    section_id: str
    difficulty: Literal["easy", "medium", "hard"]
    page: int


class Feedback(BaseModel):
    question_id: str
    selected: int
    correct: bool
    answer: int
    explanation: str
    quote: str


class QuizSnapshot(BaseModel):
    id: str
    document_id: str
    index: int
    count: int
    mode: Literal["local_practice", "openai"]
    complete: bool
    question: PublicQuestion | None
    feedback: Feedback | None


class ConceptResult(BaseModel):
    id: str
    correct: int
    total: int


class Mistake(BaseModel):
    question: PublicQuestion
    feedback: Feedback


class Results(BaseModel):
    id: str
    correct: int
    incorrect: int
    total: int
    accuracy: int
    concepts: list[ConceptResult]
    mistakes: list[Mistake]


class History(Results):
    document_id: str
    created: float


class SectionProgress(Section):
    questions_answered: int
    accuracy: int | None


class DocumentProgress(BaseModel):
    id: str
    title: str
    sections: list[SectionProgress]


class Progress(BaseModel):
    quizzes_completed: int
    questions_answered: int
    accuracy: int | None
    documents: list[DocumentProgress]
    history: list[History]
    in_progress: list[QuizSnapshot]


class Passage(BaseModel):
    id: str
    page: int
    section_id: str
    text: str
    extraction: Literal["native", "ocr"] = "native"
