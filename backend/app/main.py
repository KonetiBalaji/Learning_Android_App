from __future__ import annotations

import sqlite3
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, get_settings
from .database import connection, initialize, json_value, parse_json
from .document_service import detect_chapters, validate_and_store
from .quiz_service import generate_grounded_questions, question_id
from .schemas import (
    AnswerRequest,
    Chapter,
    Credentials,
    DocumentSummary,
    Feedback,
    QuizQuestion,
    QuizRequest,
    QuizResults,
    QuizSummary,
    Token,
)
from .security import create_token, current_user_id, hash_password, verify_password

@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize(get_settings().database_path)
    yield


app = FastAPI(title="Learning API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://10.0.2.2", "http://localhost", "http://127.0.0.1"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


def now() -> str:
    return datetime.now(UTC).isoformat()


def owned_document(document_id: str, user_id: str, settings: Settings) -> sqlite3.Row:
    with connection(settings.database_path) as db:
        row = db.execute("SELECT * FROM documents WHERE id = ? AND owner_id = ?", (document_id, user_id)).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return row


def question_payload(row: sqlite3.Row) -> QuizQuestion:
    return QuizQuestion(id=row["id"], ordinal=row["ordinal"], prompt=row["prompt"], options=parse_json(row["options_json"]), source_reference=row["source_reference"])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/auth/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(credentials: Credentials, settings: Settings = Depends(get_settings)) -> Token:
    user_id = str(uuid.uuid4())
    try:
        with connection(settings.database_path) as db:
            db.execute("INSERT INTO users (id, email, password_hash, created_at) VALUES (?, ?, ?, ?)", (user_id, credentials.email.lower(), hash_password(credentials.password), now()))
    except sqlite3.IntegrityError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with that email already exists") from error
    return Token(access_token=create_token(user_id, settings))


@app.post("/v1/auth/login", response_model=Token)
def login(credentials: Credentials, settings: Settings = Depends(get_settings)) -> Token:
    with connection(settings.database_path) as db:
        user = db.execute("SELECT * FROM users WHERE email = ?", (credentials.email.lower(),)).fetchone()
    if user is None or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return Token(access_token=create_token(user["id"], settings))


@app.post("/v1/documents", response_model=DocumentSummary, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Depends(current_user_id),
    settings: Settings = Depends(get_settings),
) -> DocumentSummary:
    stored, filename, extracted_text = await validate_and_store(file, settings)
    chapters = detect_chapters(extracted_text)
    document_id = str(uuid.uuid4())
    with connection(settings.database_path) as db:
        db.execute(
            """INSERT INTO documents (id, owner_id, original_name, media_type, stored_path, extracted_text, chapters_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (document_id, user_id, filename, file.content_type or "application/octet-stream", str(stored), extracted_text, json_value([chapter.model_dump() for chapter in chapters]), now()),
        )
    return DocumentSummary(id=document_id, original_name=filename, chapters=chapters)


@app.get("/v1/documents", response_model=list[DocumentSummary])
def list_documents(user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> list[DocumentSummary]:
    with connection(settings.database_path) as db:
        rows = db.execute("SELECT id, original_name, chapters_json FROM documents WHERE owner_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
    return [DocumentSummary(id=row["id"], original_name=row["original_name"], chapters=[Chapter.model_validate(item) for item in parse_json(row["chapters_json"])]) for row in rows]


@app.delete("/v1/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str, user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> None:
    row = owned_document(document_id, user_id, settings)
    with connection(settings.database_path) as db:
        db.execute("DELETE FROM documents WHERE id = ? AND owner_id = ?", (document_id, user_id))
    Path(row["stored_path"]).unlink(missing_ok=True)


@app.post("/v1/documents/{document_id}/quizzes", response_model=QuizSummary, status_code=status.HTTP_201_CREATED)
def create_quiz(document_id: str, request: QuizRequest, user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> QuizSummary:
    document = owned_document(document_id, user_id, settings)
    chapters = [Chapter.model_validate(item) for item in parse_json(document["chapters_json"])]
    try:
        generated = generate_grounded_questions(document["extracted_text"], chapters, request.chapter_ids, request.question_count)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    quiz_id = str(uuid.uuid4())
    with connection(settings.database_path) as db:
        db.execute("INSERT INTO quizzes (id, document_id, owner_id, title, created_at) VALUES (?, ?, ?, ?, ?)", (quiz_id, document_id, user_id, f"Quiz: {document['original_name']}", now()))
        for ordinal, question in enumerate(generated, start=1):
            db.execute(
                """INSERT INTO questions (id, quiz_id, ordinal, prompt, options_json, correct_option, explanation, source_reference)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (question_id(), quiz_id, ordinal, question.prompt, json_value(question.options), question.correct_option, question.explanation, question.source_reference),
            )
        first = db.execute("SELECT * FROM questions WHERE quiz_id = ? ORDER BY ordinal LIMIT 1", (quiz_id,)).fetchone()
    return QuizSummary(id=quiz_id, title=f"Quiz: {document['original_name']}", question_count=len(generated), first_question=question_payload(first) if first else None)


@app.post("/v1/quizzes/{quiz_id}/questions/{question_id}/answer", response_model=Feedback)
def answer_question(quiz_id: str, question_id: str, request: AnswerRequest, user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> Feedback:
    with connection(settings.database_path) as db:
        question = db.execute(
            """SELECT questions.* FROM questions JOIN quizzes ON quizzes.id = questions.quiz_id
               WHERE questions.id = ? AND questions.quiz_id = ? AND quizzes.owner_id = ?""",
            (question_id, quiz_id, user_id),
        ).fetchone()
        if question is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        if question["answered_option"] is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This question has already been answered")
        options = parse_json(question["options_json"])
        if request.selected_option not in options:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="The selected answer is not one of this question's options")
        db.execute("UPDATE questions SET answered_option = ?, answered_at = ? WHERE id = ?", (request.selected_option, now(), question_id))
        next_row = db.execute("SELECT * FROM questions WHERE quiz_id = ? AND ordinal > ? ORDER BY ordinal LIMIT 1", (quiz_id, question["ordinal"])).fetchone()
    return Feedback(
        correct=request.selected_option == question["correct_option"], selected_option=request.selected_option,
        correct_option=question["correct_option"], explanation=question["explanation"], source_reference=question["source_reference"],
        next_question=question_payload(next_row) if next_row else None,
    )


@app.get("/v1/quizzes/{quiz_id}/results", response_model=QuizResults)
def quiz_results(quiz_id: str, user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> QuizResults:
    with connection(settings.database_path) as db:
        rows = db.execute(
            """SELECT questions.* FROM questions JOIN quizzes ON quizzes.id = questions.quiz_id
               WHERE questions.quiz_id = ? AND quizzes.owner_id = ? ORDER BY questions.ordinal""",
            (quiz_id, user_id),
        ).fetchall()
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")
    answered = [row for row in rows if row["answered_option"] is not None]
    correct = [row for row in answered if row["answered_option"] == row["correct_option"]]
    mistakes = [question_payload(row) for row in answered if row["answered_option"] != row["correct_option"]]
    return QuizResults(quiz_id=quiz_id, answered=len(answered), total=len(rows), correct=len(correct), accuracy=(len(correct) / len(answered) if answered else 0.0), mistakes=mistakes)
