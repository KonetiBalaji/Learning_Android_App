from __future__ import annotations

import sqlite3
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, get_settings
from .database import connection, initialize, json_value, parse_json
from .document_service import detect_chapters, validate_and_store
from .quiz_service import generate_grounded_questions, question_id
from .mastery_service import (
    diagnostic_bank,
    confidence_for,
    response_matches,
    public_question,
    parse_diagnostic_bank,
    serialize_diagnostic_bank,
    tutor_for,
)
from .tutor_provider import tutor_provider
from .schemas import (
    AdaptiveQuestion,
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
    ChapterProgress,
    DiagnosticAnswerRequest,
    DiagnosticOutcome,
    DiagnosticSession,
    DiagnosticStartRequest,
    PracticeOutcome,
    PracticeRequest,
    ProgressDashboard,
    RewriteOutcome,
    RewriteRequest,
    UserProfile,
    WeeklyReport,
    MasterySessionState,
    TutorIntervention,
)
from .security import create_token, current_user_id, hash_password, verify_password
from .weekly_reporting import build_weekly_report

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


def owned_mastery_session(session_id: str, user_id: str, settings: Settings) -> sqlite3.Row:
    with connection(settings.database_path) as db:
        row = db.execute("SELECT * FROM mastery_sessions WHERE id = ? AND owner_id = ?", (session_id, user_id)).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mastery session not found")
    return row


def session_diagnostic_bank(session: sqlite3.Row):
    stored = session["questions_json"] if "questions_json" in session.keys() else ""
    return parse_diagnostic_bank(stored) if stored else diagnostic_bank(session["subject_id"], session["chapter_id"])


@app.get("/health")
def health(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    return {"status": "ok", "ai_provider": tutor_provider(settings).name, "model": settings.openai_model if settings.ai_mode == "openai" else "none"}


@app.get("/v1/account", response_model=UserProfile)
def account_profile(user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> UserProfile:
    with connection(settings.database_path) as db:
        user = db.execute("SELECT id, email, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return UserProfile(id=user["id"], email=user["email"], created_at=user["created_at"])


@app.delete("/v1/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> None:
    with connection(settings.database_path) as db:
        files = [Path(row["stored_path"]) for row in db.execute("SELECT stored_path FROM documents WHERE owner_id = ?", (user_id,)).fetchall()]
        deleted = db.execute("DELETE FROM users WHERE id = ?", (user_id,)).rowcount
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    for stored_file in files:
        stored_file.unlink(missing_ok=True)


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


@app.post("/v1/mastery/diagnostics", response_model=DiagnosticSession, status_code=status.HTTP_201_CREATED)
def start_diagnostic(request: DiagnosticStartRequest, user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> DiagnosticSession:
    try:
        bank = tutor_provider(settings).diagnostic_bank(request.grade, request.subject_id, request.chapter_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    session_id = str(uuid.uuid4())
    with connection(settings.database_path) as db:
        db.execute(
            """INSERT INTO mastery_sessions
               (id, owner_id, grade, subject_id, chapter_id, started_at, questions_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (session_id, user_id, request.grade, request.subject_id.lower(), request.chapter_id.lower(), now(), serialize_diagnostic_bank(bank)),
        )
    return DiagnosticSession(id=session_id, status="diagnostic", question=public_question(bank[0], 0, len(bank)))


@app.post("/v1/mastery/sessions/{session_id}/diagnostic-answer", response_model=DiagnosticOutcome)
def answer_diagnostic(session_id: str, request: DiagnosticAnswerRequest, user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> DiagnosticOutcome:
    session = owned_mastery_session(session_id, user_id, settings)
    if session["status"] != "diagnostic":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The diagnostic phase is already complete")
    bank = session_diagnostic_bank(session)
    index = session["current_question"]
    if index >= len(bank):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No diagnostic question is pending")
    item = bank[index]
    if request.selected_option not in item.options:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="The selected answer is not one of this question's options")
    correct = request.selected_option == item.correct_option
    new_correct = session["correct_answers"] + int(correct)
    next_index = index + 1 if correct else index
    next_status = "mastered" if correct and next_index == len(bank) else ("diagnostic" if correct else "tutor")
    # Generate before advancing state: provider failures must leave the question retryable.
    lesson = None if correct else tutor_provider(settings).explain(session["grade"], item, request.selected_option)
    with connection(settings.database_path) as db:
        db.execute(
            "INSERT INTO mastery_attempts (id, session_id, phase, prompt, response, correct, concept, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), session_id, "diagnostic", item.prompt, request.selected_option, int(correct), item.concept, now()),
        )
        db.execute(
            "UPDATE mastery_sessions SET current_question = ?, correct_answers = ?, status = ?, completed_at = ?, tutor_json = ? WHERE id = ?",
            (next_index, new_correct, next_status, now() if next_status == "mastered" else None, lesson.model_dump_json() if lesson else None, session_id),
        )
    score = next_index / len(bank)
    next_question = public_question(bank[next_index], next_index, len(bank)) if correct and next_index < len(bank) else None
    return DiagnosticOutcome(
        correct=correct,
        selected_option=request.selected_option,
        correct_option=item.correct_option,
        mastery_score=score,
        next_action="mastery" if next_status == "mastered" else ("next_question" if correct else "tutor"),
        next_question=next_question,
        tutor=lesson,
    )


@app.post("/v1/mastery/sessions/{session_id}/practice", response_model=PracticeOutcome)
def submit_practice(session_id: str, request: PracticeRequest, user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> PracticeOutcome:
    session = owned_mastery_session(session_id, user_id, settings)
    if session["status"] not in {"tutor", "practice"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Guided practice is not available in the current phase")
    bank = session_diagnostic_bank(session)
    item = bank[session["current_question"]]
    correct, normalized = response_matches(request.response, item.practice_answers)
    with connection(settings.database_path) as db:
        db.execute(
            "INSERT INTO mastery_attempts (id, session_id, phase, prompt, response, correct, concept, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), session_id, "practice", item.practice_prompt, request.response, int(correct), item.concept, now()),
        )
        db.execute("UPDATE mastery_sessions SET status = ?, coaching_rounds = coaching_rounds + ? WHERE id = ?", ("rewrite" if correct else "practice", 0 if correct else 1, session_id))
    return PracticeOutcome(
        correct=correct,
        normalized_answer=normalized,
        hint=None if correct else item.hint,
        next_action="rewrite" if correct else "more_practice",
    )


@app.post("/v1/mastery/sessions/{session_id}/rewrite", response_model=RewriteOutcome)
def submit_rewrite(session_id: str, request: RewriteRequest, user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> RewriteOutcome:
    session = owned_mastery_session(session_id, user_id, settings)
    if session["status"] != "rewrite":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A concept rewrite is not pending")
    bank = session_diagnostic_bank(session)
    item = bank[session["current_question"]]
    assessment = tutor_provider(settings).assess_rewrite(session["grade"], item, request.response)
    if not assessment.available:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Assessment is temporarily unavailable. Your explanation has not been graded; please retry.")
    understood, coaching = assessment.understood, assessment.coaching
    next_index = session["current_question"] + int(understood)
    mastery_score = next_index / len(bank)
    mastered = understood and next_index == len(bank)
    next_status = "mastered" if mastered else ("diagnostic" if understood else "tutor")
    lesson = TutorIntervention.model_validate_json(session["tutor_json"]) if session["tutor_json"] else tutor_for(item)
    if coaching:
        lesson = lesson.model_copy(update={"explanation": coaching})
    with connection(settings.database_path) as db:
        db.execute(
            "INSERT INTO mastery_attempts (id, session_id, phase, prompt, response, correct, concept, created_at, assessment_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), session_id, "rewrite", f"Explain {item.concept} in your own words", request.response, int(understood), item.concept, now(), assessment.model_dump_json()),
        )
        db.execute(
            "UPDATE mastery_sessions SET status = ?, current_question = ?, coaching_rounds = coaching_rounds + ?, completed_at = ?, tutor_json = ? WHERE id = ?",
            (next_status, next_index, 0 if understood else 1, now() if mastered else None, None if understood else lesson.model_dump_json(), session_id),
        )
    return RewriteOutcome(
        understood=understood,
        mastery_achieved=mastered,
        mastery_score=mastery_score,
        confidence=confidence_for(mastery_score),
        coaching=coaching,
        next_chapter_unlocked=mastered,
        next_action="mastery" if mastered else ("next_question" if understood else "tutor"),
        next_question=public_question(bank[next_index], next_index, len(bank)) if understood and not mastered else None,
        assessment_points=assessment.score,
        assessment_max_points=4 if assessment.score is not None else None,
        assessment_feedback=assessment.feedback,
    )


@app.get("/v1/mastery/sessions/{session_id}", response_model=MasterySessionState)
def mastery_session_state(session_id: str, user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> MasterySessionState:
    session = owned_mastery_session(session_id, user_id, settings)
    bank = session_diagnostic_bank(session)
    index = session["current_question"]
    item = bank[index] if index < len(bank) else None
    with connection(settings.database_path) as db:
        answer = db.execute(
            "SELECT response FROM mastery_attempts WHERE session_id = ? AND phase = 'diagnostic' ORDER BY created_at DESC LIMIT 1",
            (session_id,),
        ).fetchone()
        last_assessment = db.execute(
            "SELECT assessment_json FROM mastery_attempts WHERE session_id = ? AND phase = 'rewrite' ORDER BY created_at DESC LIMIT 1",
            (session_id,),
        ).fetchone()
    grading = parse_json(last_assessment["assessment_json"]) if last_assessment and last_assessment["assessment_json"] else {}
    lesson = None
    if item and session["status"] in {"tutor", "practice", "rewrite"}:
        lesson = TutorIntervention.model_validate_json(session["tutor_json"]) if session["tutor_json"] else tutor_for(item)
    return MasterySessionState(
        id=session_id, grade=session["grade"], subject_id=session["subject_id"], chapter_id=session["chapter_id"],
        status=session["status"], question=public_question(item, index, len(bank)) if item else None,
        tutor=lesson, selected_option=answer["response"] if answer and lesson else None,
        mastery_score=index / len(bank), coaching_rounds=session["coaching_rounds"], started_at=session["started_at"],
        assessment_points=grading.get("score"), assessment_feedback=grading.get("feedback"),
    )


@app.get("/v1/progress/dashboard", response_model=ProgressDashboard)
def progress_dashboard(grade: int | None = Query(default=None, ge=1, le=12), user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> ProgressDashboard:
    with connection(settings.database_path) as db:
        sessions = db.execute(
            "SELECT * FROM mastery_sessions WHERE owner_id = ? AND (? IS NULL OR grade = ?) ORDER BY started_at DESC", (user_id, grade, grade)
        ).fetchall()
        attempts = db.execute(
            """SELECT mastery_attempts.* FROM mastery_attempts
               JOIN mastery_sessions ON mastery_sessions.id = mastery_attempts.session_id
               WHERE mastery_sessions.owner_id = ? AND (? IS NULL OR mastery_sessions.grade = ?)""", (user_id, grade, grade)
        ).fetchall()
    chapters: list[ChapterProgress] = []
    subjects: dict[str, list[float]] = {}
    seen: set[tuple[int, str, str]] = set()
    for session in sessions:
        key = (session["grade"], session["subject_id"], session["chapter_id"])
        if key in seen:
            continue
        seen.add(key)
        bank_size = len(session_diagnostic_bank(session))
        score = session["current_question"] / bank_size
        subjects.setdefault(session["subject_id"], []).append(score)
        chapters.append(ChapterProgress(grade=key[0], subject_id=key[1], chapter_id=key[2], mastery=score, attempts=sum(1 for row in attempts if row["session_id"] == session["id"]), status=session["status"]))
    incorrect = [row["concept"] for row in attempts if not row["correct"]]
    weak_areas = list(dict.fromkeys(incorrect))[:5]
    subject_scores = {name: sum(values) / len(values) for name, values in subjects.items()}
    recommendations = ([f"Practice {area} for 15 minutes" for area in weak_areas[:3]] or ["Start a diagnostic to personalize your learning path"])
    return ProgressDashboard(subjects=subject_scores, chapters=chapters, weak_areas=weak_areas, recommendations=recommendations)


@app.get("/v1/progress/weekly-report", response_model=WeeklyReport)
def weekly_report(grade: int | None = Query(default=None, ge=1, le=12), user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> WeeklyReport:
    as_of = datetime.fromisoformat(now())
    with connection(settings.database_path) as db:
        attempts = db.execute(
            """SELECT mastery_attempts.* FROM mastery_attempts
               JOIN mastery_sessions ON mastery_sessions.id = mastery_attempts.session_id
               WHERE mastery_sessions.owner_id = ?
                 AND (? IS NULL OR mastery_sessions.grade = ?)""",
            (user_id, grade, grade),
        ).fetchall()
        sessions = db.execute(
            "SELECT * FROM mastery_sessions WHERE owner_id = ? AND (? IS NULL OR grade = ?)",
            (user_id, grade, grade),
        ).fetchall()
    return build_weekly_report(sessions, attempts, as_of,
                               {row['id']: len(session_diagnostic_bank(row)) for row in sessions})
