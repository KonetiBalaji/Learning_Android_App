from __future__ import annotations

import sqlite3
import asyncio
import logging
import uuid
from pathlib import Path
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, get_settings
from .google_login import google_login
from .database import connection, initialize, json_value, parse_json
from .document_service import detect_chapters, validate_and_store
from .document_errors import document_error_headers
from .quiz_service import generate_grounded_questions, question_id
from .quiz_creation import creation_fingerprint
from .document_selection import repair_chapter_coverage, resolve_quiz_selection
from .document_question_provider import generate_document_questions, QuestionGenerationUnavailable
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
    ChapterPreview,
    SourceSearchRequest,
    SourceSearchResults,
    PdfPageIndex,
    PdfPageRequest,
    PdfPageSelection,
    StudyPresence,
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
    DocumentQuizState,
)
from .security import create_token, current_user_id, hash_password, verify_password
from .weekly_reporting import build_weekly_report
from .mastery_transactions import lock_mastery_snapshot, mastery_state_token, check_expected_state
from .file_cleanup import queue_file_deletion, cleanup_pending_files, discard_uncommitted_upload
from .learner_preferences import InterestPreferences


async def retry_file_cleanup(settings: Settings):
    while True:
        await asyncio.sleep(60)
        try:
            await asyncio.to_thread(cleanup_pending_files, settings)
        except (sqlite3.Error, OSError):
            logging.getLogger(__name__).warning('Upload cleanup could not run; pending jobs remain queued')

@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    initialize(settings.database_path)
    await asyncio.to_thread(cleanup_pending_files, settings)
    worker = asyncio.create_task(retry_file_cleanup(settings))
    try:
        yield
    finally:
        worker.cancel()
        with suppress(asyncio.CancelledError):
            await worker


app = FastAPI(title="Learning API", version="0.1.0", lifespan=lifespan)
app.add_api_route('/v1/auth/google', google_login, methods=['POST'], response_model=Token)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://10.0.2.2", "http://localhost", "http://127.0.0.1"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
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
    return QuizQuestion(id=row["id"], ordinal=row["ordinal"], prompt=row["prompt"], options=parse_json(row["options_json"]), source_reference=row["source_reference"], question_type=row['question_type'])


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
        preferences = db.execute('SELECT interests_json FROM learner_preferences WHERE owner_id = ?', (user_id,)).fetchone()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return UserProfile(id=user["id"], email=user["email"], created_at=user["created_at"],
                       interests=parse_json(preferences['interests_json']) if preferences else [])


@app.put('/v1/account/interests', response_model=UserProfile)
def update_interests(request: InterestPreferences, user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> UserProfile:
    with connection(settings.database_path) as db:
        db.execute('BEGIN IMMEDIATE')
        if not db.execute('SELECT 1 FROM users WHERE id = ?', (user_id,)).fetchone():
            raise HTTPException(status_code=404, detail='Account not found')
        db.execute('INSERT INTO learner_preferences (owner_id, interests_json) VALUES (?, ?) ON CONFLICT(owner_id) DO UPDATE SET interests_json = excluded.interests_json',
                   (user_id, json_value(request.interests)))
    return account_profile(user_id, settings)


@app.delete("/v1/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> None:
    with connection(settings.database_path) as db:
        db.execute('BEGIN IMMEDIATE')
        files = [row["stored_path"] for row in db.execute("SELECT stored_path FROM documents WHERE owner_id = ?", (user_id,)).fetchall()]
        for stored_path in files:
            queue_file_deletion(db, stored_path)
        deleted = db.execute("DELETE FROM users WHERE id = ?", (user_id,)).rowcount
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    cleanup_pending_files(settings)


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
    try:
        chapters = detect_chapters(extracted_text)
        document_id = str(uuid.uuid4())
        with connection(settings.database_path) as db:
            db.execute(
                """INSERT INTO documents (id, owner_id, original_name, media_type, stored_path, extracted_text, chapters_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (document_id, user_id, filename, file.content_type or "application/octet-stream", str(stored), extracted_text, json_value([chapter.model_dump() for chapter in chapters]), now()),
            )
    except sqlite3.Error as error:
        discard_uncommitted_upload(settings, stored)
        raise HTTPException(status_code=503, detail='Document storage is temporarily unavailable. Please retry.') from error
    except BaseException:
        discard_uncommitted_upload(settings, stored)
        raise
    return DocumentSummary(id=document_id, original_name=filename, chapters=chapters)


@app.get("/v1/documents", response_model=list[DocumentSummary])
def list_documents(user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> list[DocumentSummary]:
    with connection(settings.database_path) as db:
        rows = db.execute("SELECT id, original_name, chapters_json FROM documents WHERE owner_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
    return [DocumentSummary(id=row["id"], original_name=row["original_name"], chapters=[Chapter.model_validate(item) for item in parse_json(row["chapters_json"])]) for row in rows]


@app.get("/v1/documents/{document_id}", response_model=DocumentSummary)
def document_summary(document_id: str, user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> DocumentSummary:
    row = owned_document(document_id, user_id, settings)
    return DocumentSummary(id=row["id"], original_name=row["original_name"],
                           chapters=[Chapter.model_validate(item) for item in parse_json(row["chapters_json"])])


@app.get('/v1/documents/{document_id}/chapters/{chapter_id}/preview', response_model=ChapterPreview)
def document_chapter_preview(document_id: str, chapter_id: str, page: int = Query(0, ge=0),
                             user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)):
    from .document_preview import preview_chapter
    row = owned_document(document_id, user_id, settings)
    try:
        chapters = [Chapter.model_validate(item) for item in parse_json(row['chapters_json'])]
        if not any(chapter.id == chapter_id for chapter in chapters):
            raise HTTPException(status_code=404, detail='Chapter not found')
        return preview_chapter(document_id, row['extracted_text'], chapters, chapter_id, page)
    except (ValueError, TypeError) as error:
        raise HTTPException(status_code=422, detail='Invalid preview page or stored source range') from error


def owned_pdf_pages(document_id: str, user_id: str, settings: Settings):
    from .pdf_page_selection import read_pdf_pages
    row = owned_document(document_id, user_id, settings)
    try:
        pages = read_pdf_pages(Path(row['stored_path']), settings.uploads_dir,
                               row['extracted_text'], settings.max_upload_bytes)
    except OSError as error:
        raise HTTPException(status_code=503, detail='The stored PDF is temporarily unavailable') from error
    except (ValueError, RuntimeError) as error:
        raise HTTPException(status_code=422, detail='Cannot safely map original PDF pages to this stored source') from error
    return row, pages


@app.get('/v1/documents/{document_id}/pdf-pages', response_model=PdfPageIndex)
def document_pdf_pages(document_id: str, user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)):
    _, pages = owned_pdf_pages(document_id, user_id, settings)
    return PdfPageIndex(document_id=document_id, pages=pages)


@app.post('/v1/documents/{document_id}/pdf-pages/selection', response_model=PdfPageSelection)
def document_pdf_page_selection(document_id: str, request: PdfPageRequest,
                                user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)):
    from .pdf_page_selection import select_pdf_pages
    row, pages = owned_pdf_pages(document_id, user_id, settings)
    try:
        chapters = [Chapter.model_validate(item) for item in parse_json(row['chapters_json'])]
        return select_pdf_pages(document_id, row['extracted_text'], chapters, pages, request.first_page, request.last_page)
    except (ValueError, TypeError) as error:
        raise HTTPException(status_code=422, detail=str(error), headers=document_error_headers(error)) from error


@app.post('/v1/documents/{document_id}/search', response_model=SourceSearchResults)
def search_document_source(document_id: str, request: SourceSearchRequest,
                           user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)):
    from .document_search import search_source
    row = owned_document(document_id, user_id, settings)
    try:
        chapters = [Chapter.model_validate(item) for item in parse_json(row['chapters_json'])]
        return search_source(document_id, row['extracted_text'], chapters, request.chapter_ids, request.query, request.limit)
    except (ValueError, TypeError) as error:
        raise HTTPException(status_code=422, detail='Invalid search phrase or selected source ranges') from error


@app.post('/v1/documents/{document_id}/structure/repair', response_model=DocumentSummary)
def repair_document_structure(document_id: str, user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)):
    with connection(settings.database_path) as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT * FROM documents WHERE id = ? AND owner_id = ?', (document_id, user_id)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail='Document not found')
        try:
            chapters = repair_chapter_coverage(row['extracted_text'],
                [Chapter.model_validate(item) for item in parse_json(row['chapters_json'])])
        except (ValueError, TypeError) as error:
            raise HTTPException(status_code=422, detail='Stored structure has invalid ranges; automatic repair is unsafe') from error
        db.execute('UPDATE documents SET chapters_json = ? WHERE id = ? AND owner_id = ?',
                   (json_value([chapter.model_dump() for chapter in chapters]), document_id, user_id))
    return DocumentSummary(id=document_id, original_name=row['original_name'], chapters=chapters)


@app.delete("/v1/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str, user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> None:
    with connection(settings.database_path) as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT stored_path FROM documents WHERE id = ? AND owner_id = ?', (document_id, user_id)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail='Document not found')
        queue_file_deletion(db, row['stored_path'])
        db.execute("DELETE FROM documents WHERE id = ? AND owner_id = ?", (document_id, user_id))
    cleanup_pending_files(settings)


def creation_replay(db, user_id, request_id, fingerprint):
    if request_id is None:
        return None
    saved = db.execute('''SELECT quizzes.*, quiz_creation_requests.fingerprint FROM quiz_creation_requests
        JOIN quizzes ON quizzes.id = quiz_creation_requests.quiz_id
        WHERE quiz_creation_requests.owner_id = ? AND request_id = ? AND quizzes.owner_id = ?''',
        (user_id, request_id, user_id)).fetchone()
    if saved is None:
        return None
    if saved['fingerprint'] != fingerprint:
        raise HTTPException(status_code=409, detail='This request ID was already used with different quiz settings')
    first = db.execute('SELECT * FROM questions WHERE quiz_id = ? ORDER BY ordinal LIMIT 1', (saved['id'],)).fetchone()
    count = db.execute('SELECT COUNT(*) FROM questions WHERE quiz_id = ?', (saved['id'],)).fetchone()[0]
    return QuizSummary(id=saved['id'], title=saved['title'], question_count=count,
        first_question=question_payload(first) if first else None,
        difficulty=saved['difficulty'], question_type=saved['question_type'],
        source_ranges=parse_json(saved['source_ranges_json']) if saved['source_ranges_json'] else None)


@app.post("/v1/documents/{document_id}/quizzes", response_model=QuizSummary, status_code=status.HTTP_201_CREATED)
def create_quiz(document_id: str, request: QuizRequest, user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> QuizSummary:
    document = owned_document(document_id, user_id, settings)
    request_id = str(request.request_id) if request.request_id is not None else None
    fingerprint = creation_fingerprint(document_id, request)
    with connection(settings.database_path) as db:
        replay = creation_replay(db, user_id, request_id, fingerprint)
        if replay is not None:
            return replay
    chapters = [Chapter.model_validate(item) for item in parse_json(document["chapters_json"])]
    try:
        selected = resolve_quiz_selection(document['extracted_text'], chapters, request.chapter_ids, request.source_ranges)
        generation_ids = [chapter.id for chapter in selected]
        if settings.ai_mode == 'openai':
            generated = generate_document_questions(document["extracted_text"], selected, generation_ids, request.question_count, settings, request.difficulty, request.question_type)
        elif settings.ai_mode == 'deterministic':
            if request.question_type != 'multiple_choice':
                raise ValueError('This offline generator supports multiple choice only; binary questions require live generation')
            if request.difficulty not in {None, 'easy'}:
                raise ValueError('This offline generator supports recall questions only; choose Easy or use live generation')
            generated = generate_grounded_questions(document["extracted_text"], selected, generation_ids, request.question_count)
        else:
            raise QuestionGenerationUnavailable('Unsupported provider mode')
    except QuestionGenerationUnavailable as error:
        raise HTTPException(status_code=503, detail='Could not validate this quiz request. Please retry.') from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error), headers=document_error_headers(error)) from error
    quiz_id = str(uuid.uuid4())
    with connection(settings.database_path) as db:
        db.execute('BEGIN IMMEDIATE')
        # Another request may have finished generation while this one was running.
        replay = creation_replay(db, user_id, request_id, fingerprint)
        if replay is not None:
            return replay
        saved_ranges = sorted((part.model_dump() for part in request.source_ranges),
            key=lambda part: (part['start_character'], part['end_character'])) if request.source_ranges else None
        db.execute("INSERT INTO quizzes (id, document_id, owner_id, title, created_at, difficulty, question_type, source_ranges_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (quiz_id, document_id, user_id, f"Quiz: {document['original_name']}", now(), request.difficulty, request.question_type, json_value(saved_ranges) if saved_ranges else None))
        for ordinal, question in enumerate(generated, start=1):
            db.execute(
                """INSERT INTO questions (id, quiz_id, ordinal, prompt, options_json, correct_option, explanation, source_reference, question_type)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (question_id(), quiz_id, ordinal, question.prompt, json_value(question.options), question.correct_option, question.explanation, question.source_reference, request.question_type),
            )
        first = db.execute("SELECT * FROM questions WHERE quiz_id = ? ORDER BY ordinal LIMIT 1", (quiz_id,)).fetchone()
        if request_id is not None:
            db.execute('INSERT INTO quiz_creation_requests (owner_id, request_id, fingerprint, quiz_id) VALUES (?, ?, ?, ?)',
                       (user_id, request_id, fingerprint, quiz_id))
    return QuizSummary(id=quiz_id, title=f"Quiz: {document['original_name']}", question_count=len(generated), first_question=question_payload(first) if first else None, difficulty=request.difficulty, question_type=request.question_type, source_ranges=saved_ranges)


@app.post("/v1/quizzes/{quiz_id}/questions/{question_id}/answer", response_model=Feedback)
def answer_question(quiz_id: str, question_id: str, request: AnswerRequest, user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> Feedback:
    with connection(settings.database_path) as db:
        # Serialize the read/validate/write boundary; no provider work occurs here.
        db.execute("BEGIN IMMEDIATE")
        question = db.execute(
            """SELECT questions.* FROM questions JOIN quizzes ON quizzes.id = questions.quiz_id
               WHERE questions.id = ? AND questions.quiz_id = ? AND quizzes.owner_id = ?""",
            (question_id, quiz_id, user_id),
        ).fetchone()
        if question is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        if question["answered_option"] is not None and question["answered_option"] != request.selected_option:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This question has already been answered")
        options = parse_json(question["options_json"])
        if request.selected_option not in options:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="The selected answer is not one of this question's options")
        if question["answered_option"] is None:
            earlier_pending = db.execute(
                "SELECT 1 FROM questions WHERE quiz_id = ? AND ordinal < ? AND answered_option IS NULL LIMIT 1",
                (quiz_id, question["ordinal"]),
            ).fetchone()
            if earlier_pending:
                raise HTTPException(status_code=409, detail="Answer the earlier question first")
            db.execute("UPDATE questions SET answered_option = ?, answered_at = ? WHERE id = ?", (request.selected_option, now(), question_id))
        # Identical retries replay feedback without changing the saved timestamp.
        next_row = db.execute("SELECT * FROM questions WHERE quiz_id = ? AND ordinal > ? ORDER BY ordinal LIMIT 1", (quiz_id, question["ordinal"])).fetchone()
    return Feedback(
        correct=request.selected_option == question["correct_option"], selected_option=request.selected_option,
        correct_option=question["correct_option"], explanation=question["explanation"], source_reference=question["source_reference"],
        next_question=question_payload(next_row) if next_row else None,
    )


@app.get("/v1/quizzes/{quiz_id}", response_model=DocumentQuizState)
def document_quiz_state(quiz_id: str, user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> DocumentQuizState:
    with connection(settings.database_path) as db:
        document = db.execute("""SELECT documents.*, quizzes.difficulty AS quiz_difficulty, quizzes.question_type AS quiz_question_type, quizzes.source_ranges_json AS quiz_source_ranges FROM documents JOIN quizzes ON quizzes.document_id = documents.id
                                 WHERE quizzes.id = ? AND quizzes.owner_id = ? AND documents.owner_id = ?""",
                              (quiz_id, user_id, user_id)).fetchone()
        if document is None:
            raise HTTPException(status_code=404, detail="Quiz not found")
        rows = db.execute("SELECT * FROM questions WHERE quiz_id = ? ORDER BY ordinal", (quiz_id,)).fetchall()
    answered = [row for row in rows if row['answered_option'] is not None]
    pending = next((row for row in rows if row['answered_option'] is None), None)
    last = answered[-1] if answered else None
    next_question = question_payload(pending) if pending else None
    feedback = Feedback(correct=last['answered_option'] == last['correct_option'], selected_option=last['answered_option'],
                        correct_option=last['correct_option'], explanation=last['explanation'],
                        source_reference=last['source_reference'], next_question=next_question) if last else None
    return DocumentQuizState(id=quiz_id, difficulty=document['quiz_difficulty'], question_type=document['quiz_question_type'], document=DocumentSummary(id=document['id'], original_name=document['original_name'],
                             chapters=[Chapter.model_validate(item) for item in parse_json(document['chapters_json'])]),
                             total=len(rows), answered=len(answered), question=next_question, last_feedback=feedback,
                             source_ranges=parse_json(document['quiz_source_ranges']) if document['quiz_source_ranges'] else None)


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


@app.post('/v1/mastery/sessions/{session_id}/presence', response_model=StudyPresence)
def observe_study_presence(session_id: str, reset: bool = False, user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)):
    from .study_time import record_presence
    with connection(settings.database_path) as db:
        db.execute('BEGIN IMMEDIATE')
        try:
            seconds = record_presence(db, user_id, session_id, datetime.fromisoformat(now()), reset=reset)
        except LookupError as error:
            raise HTTPException(status_code=404, detail='Session not found') from error
    return StudyPresence(session_id=session_id, observed_study_seconds=seconds)


@app.post("/v1/mastery/diagnostics", response_model=DiagnosticSession, status_code=status.HTTP_201_CREATED)
def start_diagnostic(request: DiagnosticStartRequest, user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> DiagnosticSession:
    from .learning_path import missing_prerequisite
    with connection(settings.database_path) as db:
        required = missing_prerequisite(db, user_id, request.grade, request.subject_id, request.chapter_id)
    if required is not None:
        raise HTTPException(status_code=403, detail=f'Complete {required} in this grade before starting this chapter')
    try:
        bank = tutor_provider(settings).diagnostic_bank(request.grade, request.subject_id, request.chapter_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    session_id = str(uuid.uuid4())
    with connection(settings.database_path) as db:
        # Revalidate after generation: a newer prerequisite attempt may have
        # started while the provider was working. Never hold a lock during AI work.
        db.execute('BEGIN IMMEDIATE')
        required = missing_prerequisite(db, user_id, request.grade, request.subject_id, request.chapter_id)
        if required is not None:
            raise HTTPException(status_code=403, detail=f'Complete {required} in this grade before starting this chapter')
        db.execute(
            """INSERT INTO mastery_sessions
               (id, owner_id, grade, subject_id, chapter_id, started_at, questions_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (session_id, user_id, request.grade, request.subject_id.lower(), request.chapter_id.lower(), now(), serialize_diagnostic_bank(bank)),
        )
    return DiagnosticSession(id=session_id, status="diagnostic", question=public_question(bank[0], 0, len(bank)),
                             state_token=mastery_state_token(dict(id=session_id, status='diagnostic', current_question=0, correct_answers=0, coaching_rounds=0)))


@app.post("/v1/mastery/sessions/{session_id}/diagnostic-answer", response_model=DiagnosticOutcome)
def answer_diagnostic(session_id: str, request: DiagnosticAnswerRequest, user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> DiagnosticOutcome:
    session = owned_mastery_session(session_id, user_id, settings)
    check_expected_state(session, request.expected_state)
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
    lesson = None
    if not correct:
        interests = account_profile(user_id, settings).interests
        provider = tutor_provider(settings, interests=tuple(interests)) if interests else tutor_provider(settings)
        lesson = provider.explain(session["grade"], item, request.selected_option)
    with connection(settings.database_path) as db:
        lock_mastery_snapshot(db, session)
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
        state_token=mastery_state_token(session, current_question=next_index, correct_answers=new_correct, status=next_status),
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
    check_expected_state(session, request.expected_state)
    if session["status"] not in {"tutor", "practice"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Guided practice is not available in the current phase")
    bank = session_diagnostic_bank(session)
    item = bank[session["current_question"]]
    correct, normalized = response_matches(request.response, item.practice_answers)
    next_item = None
    next_lesson = None
    if not correct and request.fresh_practice and session['subject_id'] == 'math' and session['chapter_id'] == 'fractions':
        from .fraction_practice import next_fraction_practice
        next_item = next_fraction_practice(item, session['coaching_rounds'] + 1)
        if next_item is not None:
            lesson = TutorIntervention.model_validate_json(session['tutor_json']) if session['tutor_json'] else tutor_for(item)
            next_lesson = lesson.model_copy(update={'practice_prompt': next_item.practice_prompt, 'hint': next_item.hint})
    with connection(settings.database_path) as db:
        lock_mastery_snapshot(db, session)
        db.execute(
            "INSERT INTO mastery_attempts (id, session_id, phase, prompt, response, correct, concept, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), session_id, "practice", item.practice_prompt, request.response, int(correct), item.concept, now()),
        )
        db.execute("UPDATE mastery_sessions SET status = ?, coaching_rounds = coaching_rounds + ? WHERE id = ?", ("rewrite" if correct else "practice", 0 if correct else 1, session_id))
        if next_item is not None:
            updated_bank = list(bank)
            updated_bank[session['current_question']] = next_item
            db.execute('UPDATE mastery_sessions SET questions_json = ?, tutor_json = ? WHERE id = ?',
                       (serialize_diagnostic_bank(tuple(updated_bank)), next_lesson.model_dump_json(), session_id))
    return PracticeOutcome(
        state_token=mastery_state_token(session, status='rewrite' if correct else 'practice', coaching_rounds=session['coaching_rounds'] + int(not correct)),
        correct=correct,
        normalized_answer=normalized,
        hint=None if correct else (next_item.hint if next_item else item.hint),
        next_practice=next_lesson,
        next_action="rewrite" if correct else "more_practice",
    )


@app.post("/v1/mastery/sessions/{session_id}/rewrite", response_model=RewriteOutcome)
def submit_rewrite(session_id: str, request: RewriteRequest, user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> RewriteOutcome:
    session = owned_mastery_session(session_id, user_id, settings)
    check_expected_state(session, request.expected_state)
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
    next_item = None
    if not understood and request.fresh_practice and session['subject_id'] == 'math' and session['chapter_id'] == 'fractions':
        from .fraction_practice import next_fraction_practice
        next_item = next_fraction_practice(item, session['coaching_rounds'] + 1)
        if next_item is not None:
            lesson = lesson.model_copy(update={'practice_prompt': next_item.practice_prompt, 'hint': next_item.hint})
    with connection(settings.database_path) as db:
        lock_mastery_snapshot(db, session)
        db.execute(
            "INSERT INTO mastery_attempts (id, session_id, phase, prompt, response, correct, concept, created_at, assessment_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), session_id, "rewrite", f"Explain {item.concept} in your own words", request.response, int(understood), item.concept, now(), assessment.model_dump_json()),
        )
        db.execute(
            "UPDATE mastery_sessions SET status = ?, current_question = ?, coaching_rounds = coaching_rounds + ?, completed_at = ?, tutor_json = ? WHERE id = ?",
            (next_status, next_index, 0 if understood else 1, now() if mastered else None, None if understood else lesson.model_dump_json(), session_id),
        )
        if next_item is not None:
            updated_bank = list(bank)
            updated_bank[session['current_question']] = next_item
            db.execute('UPDATE mastery_sessions SET questions_json = ? WHERE id = ?',
                       (serialize_diagnostic_bank(tuple(updated_bank)), session_id))
    return RewriteOutcome(
        next_practice=lesson if next_item is not None else None,
        state_token=mastery_state_token(session, status=next_status, current_question=next_index, coaching_rounds=session['coaching_rounds'] + int(not understood)),
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
        state_token=mastery_state_token(session),
        id=session_id, grade=session["grade"], subject_id=session["subject_id"], chapter_id=session["chapter_id"],
        status=session["status"], question=public_question(item, index, len(bank)) if item else None,
        tutor=lesson, selected_option=answer["response"] if answer and lesson else None,
        mastery_score=index / len(bank), coaching_rounds=session["coaching_rounds"], started_at=session["started_at"],
        assessment_points=grading.get("score"), assessment_feedback=grading.get("feedback"),
    )


@app.get("/v1/progress/dashboard", response_model=ProgressDashboard)
def progress_dashboard(grade: int | None = Query(default=None, ge=1, le=12), user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> ProgressDashboard:
    from .study_time import observed_seconds
    with connection(settings.database_path) as db:
        study_seconds = observed_seconds(db, user_id, grade)
        sessions = db.execute(
            "SELECT * FROM mastery_sessions WHERE owner_id = ? AND (? IS NULL OR grade = ?) ORDER BY started_at DESC, rowid DESC", (user_id, grade, grade)
        ).fetchall()
        attempts = db.execute(
            """SELECT mastery_attempts.*, mastery_attempts.rowid AS attempt_order FROM mastery_attempts
               JOIN mastery_sessions ON mastery_sessions.id = mastery_attempts.session_id
               WHERE mastery_sessions.owner_id = ? AND (? IS NULL OR mastery_sessions.grade = ?)
               ORDER BY mastery_attempts.rowid""", (user_id, grade, grade)
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
    by_session = {row['id']: row for row in sessions}
    latest_assessment = {}
    for attempt in attempts:
        # Guided practice alone is not evidence of independent understanding.
        if attempt['phase'] not in {'diagnostic', 'rewrite'}:
            continue
        session = by_session[attempt['session_id']]
        key = (session['grade'], session['subject_id'], session['chapter_id'], attempt['concept'].strip().casefold())
        latest_assessment[key] = attempt
    unresolved = sorted((row for row in latest_assessment.values() if not row['correct']),
                        key=lambda row: row['attempt_order'], reverse=True)
    weak_areas = list(dict.fromkeys(row['concept'] for row in unresolved))[:5]
    subject_scores = {name: sum(values) / len(values) for name, values in subjects.items()}
    recommendations = ([f"Practice {area} for 15 minutes" for area in weak_areas[:3]] or
                       ["Continue your saved assessment or explore the next concept" if attempts else "Start a diagnostic to personalize your learning path"])
    from .learning_path import PREREQUISITES
    mastered = {(chapter.subject_id, chapter.chapter_id) for chapter in chapters if chapter.status == 'mastered'}
    unlocked = sorted(f'{subject}:{chapter}' for (subject, chapter), required in PREREQUISITES.items()
                      if grade is not None and (subject, required) in mastered)
    return ProgressDashboard(observed_study_seconds=study_seconds, grade=grade, unlocked_chapter_ids=unlocked, subjects=subject_scores,
                             chapters=chapters, weak_areas=weak_areas, recommendations=recommendations)


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
    report = build_weekly_report(sessions, attempts, as_of,
                                 {row['id']: len(session_diagnostic_bank(row)) for row in sessions})
    from .study_time import observed_seconds
    with connection(settings.database_path) as db:
        report.observed_study_seconds = observed_seconds(db, user_id, grade,
            datetime.fromisoformat(report.period_start), datetime.fromisoformat(report.period_end))
    return report
