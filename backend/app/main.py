from __future__ import annotations

import sqlite3
import asyncio
import base64
import hashlib
import logging
import re
import uuid
from uuid import UUID
from pathlib import Path
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile, status, Query, Response
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, get_settings
from .google_login import GoogleChallenge, google_challenge, google_login
from .auth_throttle import limit_authentication
from .database import connection, initialize, json_value, parse_json
from .document_service import detect_chapters, validate_and_store
from .document_errors import DocumentErrorCode, DocumentValidationError, document_error_headers
from .parser_capacity import ParserCapacityError
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
from .tutor_provider import DiagnosticUnavailable, TutorLessonUnavailable, tutor_provider
from .schemas import (
    AdaptiveQuestion,
    AnswerRequest,
    Chapter,
    Credentials,
    DocumentSummary,
    ChapterPreview,
    SourceSearchRequest,
    SourceSearchResults,
    RetryMistakesRequest,
    PdfPageIndex,
    PdfPageRequest,
    PdfPageSelection,
    StudyPresence,
    Feedback,
    QuestionSourceEvidence,
    OriginalPdfPageEvidence,
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
    DocumentLearningProgress,
    DocumentQuizAttempt,
    DocumentChapterProgress,
    CurriculumCatalog,
    WeakAreaEvidence,
    RetentionPolicy,
)
from .security import create_token, current_user_id, hash_password, verify_password
from .weekly_reporting import build_weekly_report, load_weekly_rows
from .mastery_transactions import lock_mastery_snapshot, mastery_state_token, check_expected_state
from .mastery_idempotency import request_fingerprint, replay as replay_mastery_mutation, save as save_mastery_mutation
from .file_cleanup import (queue_file_deletion, cleanup_pending_files, discard_uncommitted_upload,
                           reconcile_orphan_uploads)
from .learner_preferences import InterestPreferences
from .tutor_conversation import TutorQuestionRequest, TutorTurn, answer_question as answer_tutor_follow_up, conversation_history
from .guardian_access import (
    GuardianInvitation, GuardianInvitationRedemption, LinkedAccount, GuardianAccessEvent,
    create_invitation, redeem_invitation, linked_learners, linked_guardians,
    require_link, revoke_by_guardian, revoke_by_learner, cleanup_invitations, access_history,
    access_history_csv,
    record_guardian_account_deletion,
)
from .learning_path import CATALOG, CATALOG_VERSION, catalog_chapter, unlocks_dependent_chapter
from .ai_usage import consume_ai_operation
from .operational_logging import OperationalLoggingMiddleware
from .runtime_readiness import verify_runtime_readiness
from .request_limits import RequestBodyLimitMiddleware


async def retry_file_cleanup(settings: Settings):
    while True:
        await asyncio.sleep(60)
        try:
            await asyncio.to_thread(cleanup_pending_files, settings)
            await asyncio.to_thread(cleanup_invitations, settings)
        except (sqlite3.Error, OSError):
            logging.getLogger(__name__).warning('Runtime retention cleanup could not run; pending work remains queued')

@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    initialize(settings.database_path)
    await asyncio.to_thread(reconcile_orphan_uploads, settings)
    await asyncio.to_thread(cleanup_pending_files, settings)
    await asyncio.to_thread(cleanup_invitations, settings)
    worker = asyncio.create_task(retry_file_cleanup(settings))
    try:
        yield
    finally:
        worker.cancel()
        with suppress(asyncio.CancelledError):
            await worker


app = FastAPI(title="Learning API", version="0.1.0", lifespan=lifespan)
app.add_api_route('/v1/auth/google/challenge', google_challenge, methods=['POST'],
                  response_model=GoogleChallenge, dependencies=[Depends(limit_authentication)])
app.add_api_route('/v1/auth/google', google_login, methods=['POST'], response_model=Token, dependencies=[Depends(limit_authentication)])
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://10.0.2.2", "http://localhost", "http://127.0.0.1"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(RequestBodyLimitMiddleware)
app.add_middleware(OperationalLoggingMiddleware)


@app.get("/")
def service_root() -> dict[str, str]:
    return {
        "service": "Learning API",
        "status": "ok",
        "health": "/health",
        "documentation": "/docs",
    }


def now() -> str:
    return datetime.now(UTC).isoformat()


@app.get('/v1/privacy/retention', response_model=RetentionPolicy)
def retention_policy(user_id: str = Depends(current_user_id),
                     settings: Settings = Depends(get_settings)) -> RetentionPolicy:
    # Authentication confirms the disclosure belongs to the same service that
    # stores this learner's data; the response contains no account data.
    del user_id
    return RetentionPolicy(guardian_invitation_days=settings.guardian_invitation_retention_days,
        crash_orphan_hours=settings.orphan_upload_grace_hours,
        backup_days=settings.backup_retention_days)


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
    return {
        "status": "ok",
        "environment": settings.environment,
        "revision": settings.release_revision,
        "ai_provider": tutor_provider(settings).name,
        "model": settings.openai_model if settings.ai_mode == "openai" else "none",
    }


@app.get('/ready')
def ready(settings: Settings = Depends(get_settings)):
    try:
        checks = verify_runtime_readiness(settings)
    except (OSError, sqlite3.Error) as error:
        raise HTTPException(status_code=503, detail='Runtime storage is not ready') from error
    return {'status': 'ready', 'environment': settings.environment,
            'revision': settings.release_revision, 'checks': list(checks)}


@app.get('/v1/catalog', response_model=CurriculumCatalog)
def curriculum_catalog(grade: int = Query(ge=1, le=12), _: str = Depends(current_user_id)) -> CurriculumCatalog:
    return CurriculumCatalog(version=CATALOG_VERSION, grade=grade, board='unconfirmed',
                             subjects=[{'id': subject.id, 'title': subject.title,
                                        'chapters': [chapter.__dict__ for chapter in subject.chapters]}
                                       for subject in CATALOG])


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
        record_guardian_account_deletion(db, user_id)
        deleted = db.execute("DELETE FROM users WHERE id = ?", (user_id,)).rowcount
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    cleanup_pending_files(settings)


@app.post("/v1/auth/register", response_model=Token, status_code=status.HTTP_201_CREATED, dependencies=[Depends(limit_authentication)])
def register(credentials: Credentials, settings: Settings = Depends(get_settings)) -> Token:
    user_id = str(uuid.uuid4())
    try:
        with connection(settings.database_path) as db:
            db.execute("INSERT INTO users (id, email, password_hash, created_at) VALUES (?, ?, ?, ?)", (user_id, credentials.email.lower(), hash_password(credentials.password), now()))
    except sqlite3.IntegrityError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with that email already exists") from error
    return Token(access_token=create_token(user_id, settings))


@app.post("/v1/auth/login", response_model=Token, dependencies=[Depends(limit_authentication)])
def login(credentials: Credentials, settings: Settings = Depends(get_settings)) -> Token:
    with connection(settings.database_path) as db:
        user = db.execute("SELECT * FROM users WHERE email = ?", (credentials.email.lower(),)).fetchone()
    if user is None or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return Token(access_token=create_token(user["id"], settings))


@app.post('/v1/guardian/invitations', response_model=GuardianInvitation, status_code=status.HTTP_201_CREATED)
def new_guardian_invitation(user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> GuardianInvitation:
    return create_invitation(user_id, settings)


@app.post('/v1/guardian/links', response_model=LinkedAccount, status_code=status.HTTP_201_CREATED)
def link_guardian_account(request: GuardianInvitationRedemption, user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> LinkedAccount:
    return redeem_invitation(user_id, request.code, settings)


@app.get('/v1/guardian/learners', response_model=list[LinkedAccount])
def guardian_learners(user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> list[LinkedAccount]:
    return linked_learners(user_id, settings)


@app.get('/v1/guardian/access', response_model=list[LinkedAccount])
def learner_guardians(user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> list[LinkedAccount]:
    return linked_guardians(user_id, settings)


@app.get('/v1/guardian/access-history', response_model=list[GuardianAccessEvent])
def learner_guardian_history(user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> list[GuardianAccessEvent]:
    return access_history(user_id, settings)


@app.get('/v1/guardian/access-history/export')
def learner_guardian_history_export(user_id: str = Depends(current_user_id),
                                    settings: Settings = Depends(get_settings)) -> Response:
    return Response(content=access_history_csv(user_id, settings),
                    media_type='text/csv',
                    headers={'Content-Disposition': 'attachment; filename="report-access-history.csv"',
                             'Cache-Control': 'no-store'})


@app.delete('/v1/guardian/learners/{learner_id}', status_code=status.HTTP_204_NO_CONTENT)
def unlink_learner(learner_id: str, user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> None:
    revoke_by_guardian(user_id, learner_id, settings)


@app.delete('/v1/guardian/access/{guardian_id}', status_code=status.HTTP_204_NO_CONTENT)
def revoke_guardian(guardian_id: str, user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> None:
    revoke_by_learner(user_id, guardian_id, settings)


@app.post("/v1/documents", response_model=DocumentSummary, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    x_upload_request_id: UUID | None = Header(default=None, alias='X-Upload-Request-ID'),
    user_id: str = Depends(current_user_id),
    settings: Settings = Depends(get_settings),
) -> DocumentSummary:
    stored, filename, extracted_text = await validate_and_store(file, settings)
    try:
        chapters = detect_chapters(extracted_text)
        document_id = str(uuid.uuid4())
        request_id = str(x_upload_request_id) if x_upload_request_id is not None else None
        digest = hashlib.sha256()
        for value in (filename, file.content_type or 'application/octet-stream'):
            encoded = value.encode('utf-8')
            digest.update(len(encoded).to_bytes(8, 'big'))
            digest.update(encoded)
        with stored.open('rb') as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b''):
                digest.update(chunk)
        fingerprint = digest.hexdigest()
        with connection(settings.database_path) as db:
            # SQLite's write lock makes quota-read plus insert one owner-safe critical
            # section; the temporary file is discarded on rejection or contention.
            db.execute('BEGIN IMMEDIATE')
            if request_id is not None:
                replay = db.execute('''SELECT document_upload_requests.fingerprint, documents.id,
                    documents.original_name, documents.chapters_json
                    FROM document_upload_requests JOIN documents
                      ON documents.id = document_upload_requests.document_id
                    WHERE document_upload_requests.owner_id = ? AND request_id = ?
                      AND documents.owner_id = ?''', (user_id, request_id, user_id)).fetchone()
                if replay is not None:
                    if replay['fingerprint'] != fingerprint:
                        raise HTTPException(status_code=409, detail='Upload request identity was already used for different content.')
                    try:
                        stored.unlink(missing_ok=True)
                    except OSError:
                        queue_file_deletion(db, str(stored))
                    return DocumentSummary(id=replay['id'], original_name=replay['original_name'],
                        chapters=[Chapter.model_validate(item) for item in parse_json(replay['chapters_json'])])
            usage = db.execute(
                'SELECT COUNT(*) AS count, COALESCE(SUM(stored_bytes), 0) AS bytes FROM documents WHERE owner_id = ?',
                (user_id,),
            ).fetchone()
            if usage['count'] >= settings.max_documents_per_owner:
                raise DocumentValidationError(DocumentErrorCode.DOCUMENT_COUNT_LIMIT,
                                              'Delete a saved document before uploading another.')
            incoming_bytes = stored.stat().st_size
            if usage['bytes'] + incoming_bytes > settings.max_document_bytes_per_owner:
                raise DocumentValidationError(DocumentErrorCode.DOCUMENT_BYTES_LIMIT,
                                              'Delete saved documents before uploading more material.')
            db.execute(
                """INSERT INTO documents (id, owner_id, original_name, media_type, stored_path, extracted_text, chapters_json, created_at, stored_bytes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (document_id, user_id, filename, file.content_type or "application/octet-stream", str(stored), extracted_text, json_value([chapter.model_dump() for chapter in chapters]), now(), incoming_bytes),
            )
            if request_id is not None:
                db.execute('INSERT INTO document_upload_requests (owner_id, request_id, fingerprint, document_id) VALUES (?, ?, ?, ?)',
                           (user_id, request_id, fingerprint, document_id))
    except DocumentValidationError as error:
        discard_uncommitted_upload(settings, stored)
        raise HTTPException(status_code=422, detail=str(error), headers=document_error_headers(error)) from error
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


@app.get('/v1/documents/{document_id}/progress', response_model=DocumentLearningProgress)
def document_learning_progress(document_id: str, user_id: str = Depends(current_user_id),
                               settings: Settings = Depends(get_settings)) -> DocumentLearningProgress:
    with connection(settings.database_path) as db:
        document = db.execute('SELECT chapters_json FROM documents WHERE id = ? AND owner_id = ?',
                              (document_id, user_id)).fetchone()
        if document is None:
            raise HTTPException(status_code=404, detail='Document not found')
        rows = db.execute('''SELECT quizzes.id, quizzes.created_at, quizzes.completed_at,
                COUNT(questions.id) AS total,
                SUM(CASE WHEN questions.answered_option IS NOT NULL THEN 1 ELSE 0 END) AS answered,
                SUM(CASE WHEN questions.answered_option = questions.correct_option THEN 1 ELSE 0 END) AS correct,
                MAX(questions.answered_at) AS last_answered_at
            FROM quizzes LEFT JOIN questions ON questions.quiz_id = quizzes.id
            WHERE quizzes.document_id = ? AND quizzes.owner_id = ?
            GROUP BY quizzes.id ORDER BY quizzes.created_at, quizzes.id''',
            (document_id, user_id)).fetchall()
        retry_rows = db.execute('SELECT retry_quiz_id, source_quiz_id FROM quiz_retry_requests WHERE owner_id = ?',
                                (user_id,)).fetchall()
        source_rows = db.execute('''SELECT questions.source_reference,
                SUM(CASE WHEN questions.answered_option = questions.correct_option THEN 1 ELSE 0 END) AS correct,
                SUM(CASE WHEN questions.answered_option IS NOT NULL AND questions.answered_option <> questions.correct_option THEN 1 ELSE 0 END) AS incorrect
            FROM questions JOIN quizzes ON quizzes.id = questions.quiz_id
            WHERE quizzes.document_id = ? AND quizzes.owner_id = ? AND questions.answered_option IS NOT NULL
            GROUP BY questions.source_reference''', (document_id, user_id)).fetchall()
        chapter_rows = db.execute('''SELECT questions.chapter_id,
                COUNT(*) AS answered,
                SUM(CASE WHEN questions.answered_option = questions.correct_option THEN 1 ELSE 0 END) AS correct
            FROM questions JOIN quizzes ON quizzes.id = questions.quiz_id
            WHERE quizzes.document_id = ? AND quizzes.owner_id = ?
              AND questions.answered_option IS NOT NULL AND questions.chapter_id IS NOT NULL
            GROUP BY questions.chapter_id''', (document_id, user_id)).fetchall()
        concept_rows = db.execute('''SELECT questions.concept,
                COUNT(*) AS answered,
                SUM(CASE WHEN questions.answered_option = questions.correct_option THEN 1 ELSE 0 END) AS correct
            FROM questions JOIN quizzes ON quizzes.id = questions.quiz_id
            WHERE quizzes.document_id = ? AND quizzes.owner_id = ?
              AND questions.answered_option IS NOT NULL AND questions.concept IS NOT NULL
            GROUP BY questions.concept''', (document_id, user_id)).fetchall()
    retry_of = {row['retry_quiz_id']: row['source_quiz_id'] for row in retry_rows}
    attempts = []
    for row in rows:
        total, answered, correct = row['total'] or 0, row['answered'] or 0, row['correct'] or 0
        complete = total > 0 and answered == total
        attempts.append(DocumentQuizAttempt(quiz_id=row['id'], created_at=row['created_at'],
            completed_at=(row['completed_at'] or row['last_answered_at']) if complete else None,
            answered=answered, total=total, correct=correct,
            accuracy=(correct / answered if answered else 0.0), complete=complete,
            retry_of=retry_of.get(row['id'])))
    completed = [attempt for attempt in attempts if attempt.complete]
    answered_total = sum(attempt.answered for attempt in attempts)
    correct_total = sum(attempt.correct for attempt in attempts)
    improvement = None if len(completed) < 2 else round(
        (completed[-1].accuracy - completed[-2].accuracy) * 100, 1)
    trend = ('insufficient_data' if improvement is None else 'improving' if improvement > 0.05
             else 'declining' if improvement < -0.05 else 'steady')
    strongest = sorted(source_rows, key=lambda row: (-row['correct'], row['incorrect'], row['source_reference']))
    weakest = sorted(source_rows, key=lambda row: (-row['incorrect'], row['correct'], row['source_reference']))
    chapter_evidence = {row['chapter_id']: row for row in chapter_rows}
    chapter_models = []
    for chapter in [Chapter.model_validate(value) for value in parse_json(document['chapters_json'])]:
        evidence = chapter_evidence.get(chapter.id)
        answered = evidence['answered'] if evidence else 0
        correct = evidence['correct'] if evidence else 0
        chapter_models.append(DocumentChapterProgress(chapter_id=chapter.id, title=chapter.title,
            questions_answered=answered, correct_answers=correct,
            accuracy=(correct / answered if answered else None)))
    strongest_concepts = sorted(concept_rows,
        key=lambda row: (-(row['correct'] / row['answered']), -row['answered'], row['concept'].casefold()))
    weakest_concepts = sorted(concept_rows,
        key=lambda row: ((row['correct'] / row['answered']), -row['answered'], row['concept'].casefold()))
    return DocumentLearningProgress(document_id=document_id, quizzes_created=len(attempts),
        quizzes_completed=len(completed), questions_answered=answered_total,
        correct_answers=correct_total,
        accuracy=(correct_total / answered_total if answered_total else 0.0), trend=trend,
        improvement_percentage_points=improvement,
        strong_source_areas=[row['source_reference'] for row in strongest if row['correct'] > 0][:3],
        weak_source_areas=[row['source_reference'] for row in weakest if row['incorrect'] > 0][:3],
        strongest_concepts=[row['concept'] for row in strongest_concepts if row['correct'] > 0][:3],
        weak_concepts=[row['concept'] for row in weakest_concepts if row['correct'] < row['answered']][:3],
        chapters=chapter_models,
        attempts=attempts)


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
    from .pdf_page_selection import read_pdf_pages_isolated
    row = owned_document(document_id, user_id, settings)
    try:
        pages = read_pdf_pages_isolated(Path(row['stored_path']), settings.uploads_dir,
                                        row['extracted_text'], settings.max_upload_bytes,
                                        settings.document_parse_timeout_seconds,
                                        settings.max_concurrent_document_parsers,
                                        settings.database_path)
    except ParserCapacityError as error:
        busy = DocumentValidationError(DocumentErrorCode.DOCUMENT_PROCESSING_BUSY,
                                       'Document processing is busy. Retry shortly.')
        raise HTTPException(status_code=503, detail=str(busy),
                            headers={**document_error_headers(busy), 'Retry-After': '2'}) from error
    except TimeoutError as error:
        limit = DocumentValidationError(DocumentErrorCode.DOCUMENT_PROCESSING_LIMIT,
                                        'The PDF exceeded safe page-processing limits.')
        raise HTTPException(status_code=422, detail=str(limit),
                            headers=document_error_headers(limit)) from error
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
        result = search_source(document_id, row['extracted_text'], chapters, request.chapter_ids, request.query, request.limit)
        if result.matches or settings.ai_mode != 'openai':
            return result
        from .semantic_source_search import (
            SemanticSearchScopeTooLarge, SemanticSearchUnavailable, semantic_search_source,
        )
        consume_ai_operation(settings, user_id)
        try:
            return semantic_search_source(document_id, row['extracted_text'], chapters,
                request.chapter_ids, request.query.strip(), request.limit,
                settings.openai_api_key or '', settings.openai_embedding_model)
        except SemanticSearchUnavailable as error:
            raise HTTPException(status_code=503, detail='Semantic source search is temporarily unavailable; retry or use exact source words') from error
        except SemanticSearchScopeTooLarge as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
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
            consume_ai_operation(settings, user_id)
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
        selected_by_id = {chapter.id: chapter for chapter in selected}
        source_chapters = [Chapter.model_validate(item) for item in parse_json(document['chapters_json'])]
        for ordinal, question in enumerate(generated, start=1):
            generated_chapter = selected_by_id.get(question.chapter_id)
            matches = [chapter for chapter in source_chapters if generated_chapter is not None
                       and chapter.start_character <= generated_chapter.start_character
                       and generated_chapter.end_character <= chapter.end_character]
            source_chapter_id = matches[0].id if len(matches) == 1 else None
            db.execute(
                """INSERT INTO questions (id, quiz_id, ordinal, prompt, options_json, correct_option, explanation, source_reference, question_type, chapter_id, concept)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (question_id(), quiz_id, ordinal, question.prompt, json_value(question.options), question.correct_option,
                 question.explanation, question.source_reference, request.question_type, source_chapter_id, question.concept),
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
            if db.execute('SELECT 1 FROM questions WHERE quiz_id = ? AND answered_option IS NULL LIMIT 1',
                          (quiz_id,)).fetchone() is None:
                db.execute('UPDATE quizzes SET completed_at = COALESCE(completed_at, ?) WHERE id = ?',
                           (now(), quiz_id))
        # Identical retries replay feedback without changing the saved timestamp.
        next_row = db.execute("SELECT * FROM questions WHERE quiz_id = ? AND ordinal > ? ORDER BY ordinal LIMIT 1", (quiz_id, question["ordinal"])).fetchone()
    return Feedback(
        question_id=question_id,
        correct=request.selected_option == question["correct_option"], selected_option=request.selected_option,
        correct_option=question["correct_option"], explanation=question["explanation"], source_reference=question["source_reference"],
        next_question=question_payload(next_row) if next_row else None,
    )


@app.get("/v1/quizzes/{quiz_id}/questions/{question_id}/source", response_model=QuestionSourceEvidence)
def question_source(quiz_id: str, question_id: str, user_id: str = Depends(current_user_id),
                    settings: Settings = Depends(get_settings)) -> QuestionSourceEvidence:
    """Return exact source evidence only after the learner has answered the question."""
    with connection(settings.database_path) as db:
        row = db.execute(
            """SELECT questions.source_reference, questions.answered_option, documents.extracted_text,
                      documents.id AS document_id, documents.stored_path
               FROM questions JOIN quizzes ON quizzes.id = questions.quiz_id
               JOIN documents ON documents.id = quizzes.document_id
               WHERE questions.id = ? AND questions.quiz_id = ?
                 AND quizzes.owner_id = ? AND documents.owner_id = ?""",
            (question_id, quiz_id, user_id, user_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Question not found")
    if row['answered_option'] is None:
        raise HTTPException(status_code=409, detail="Answer this question before viewing its source")
    match = re.fullmatch(r".+ \(source characters (\d+)-(\d+)\)", row['source_reference'])
    if match is None:
        raise HTTPException(status_code=409, detail="Exact source evidence is unavailable for this question")
    start, end = map(int, match.groups())
    text = row['extracted_text']
    if not 0 <= start < end <= len(text):
        raise HTTPException(status_code=409, detail="Exact source evidence is unavailable for this question")
    original_pages = []
    stored = Path(row['stored_path'])
    if stored.suffix.lower() == '.pdf':
        try:
            _, pages = owned_pdf_pages(row['document_id'], user_id, settings)
            page_numbers = [page.page for page in pages
                            if start < page.end_character and end > page.start_character]
            if not page_numbers or len(page_numbers) > 5:
                raise ValueError('Question source spans an unsafe number of PDF pages')
            from .pdf_page_selection import render_pdf_pages_isolated
            rendered = render_pdf_pages_isolated(stored, settings.uploads_dir, page_numbers,
                settings.max_upload_bytes, settings.document_parse_timeout_seconds,
                settings.max_concurrent_document_parsers, settings.database_path)
            original_pages = [OriginalPdfPageEvidence(page=number,
                image_base64=base64.b64encode(image).decode('ascii')) for number, image in rendered]
        except ParserCapacityError as error:
            raise HTTPException(status_code=503, detail='Document processing is busy. Retry shortly.',
                                headers={'Retry-After': '2'}) from error
        except (OSError, TimeoutError) as error:
            raise HTTPException(status_code=503, detail='The original PDF page is temporarily unavailable') from error
        except (ValueError, RuntimeError) as error:
            raise HTTPException(status_code=409, detail='The original PDF page cannot be safely displayed') from error
    return QuestionSourceEvidence(quiz_id=quiz_id, question_id=question_id,
        source_reference=row['source_reference'], start_character=start, end_character=end,
        text=text[start:end], original_pdf_pages=original_pages)


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
    feedback = Feedback(question_id=last['id'], correct=last['answered_option'] == last['correct_option'], selected_option=last['answered_option'],
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
    mistakes = [{**question_payload(row).model_dump(),
        'selected_option': row['answered_option'], 'correct_option': row['correct_option'],
        'explanation': row['explanation']}
        for row in answered if row["answered_option"] != row["correct_option"]]
    return QuizResults(quiz_id=quiz_id, answered=len(answered), total=len(rows), correct=len(correct), accuracy=(len(correct) / len(answered) if answered else 0.0), mistakes=mistakes)


@app.post('/v1/quizzes/{quiz_id}/retry-mistakes', response_model=QuizSummary,
          status_code=status.HTTP_201_CREATED)
def retry_quiz_mistakes(quiz_id: str, request: RetryMistakesRequest,
                        user_id: str = Depends(current_user_id),
                        settings: Settings = Depends(get_settings)) -> QuizSummary:
    request_id = str(request.request_id)
    with connection(settings.database_path) as db:
        db.execute('BEGIN IMMEDIATE')
        source = db.execute('SELECT * FROM quizzes WHERE id = ? AND owner_id = ?',
                            (quiz_id, user_id)).fetchone()
        if source is None:
            raise HTTPException(status_code=404, detail='Quiz not found')
        replay = db.execute('''SELECT quizzes.* FROM quiz_retry_requests
            JOIN quizzes ON quizzes.id = quiz_retry_requests.retry_quiz_id
            WHERE quiz_retry_requests.owner_id = ? AND quiz_retry_requests.source_quiz_id = ?
              AND quiz_retry_requests.request_id = ? AND quizzes.owner_id = ?''',
            (user_id, quiz_id, request_id, user_id)).fetchone()
        if replay is not None:
            first = db.execute('SELECT * FROM questions WHERE quiz_id = ? ORDER BY ordinal LIMIT 1',
                               (replay['id'],)).fetchone()
            count = db.execute('SELECT COUNT(*) FROM questions WHERE quiz_id = ?',
                               (replay['id'],)).fetchone()[0]
            return QuizSummary(id=replay['id'], title=replay['title'], question_count=count,
                first_question=question_payload(first), difficulty=replay['difficulty'],
                question_type=replay['question_type'],
                source_ranges=parse_json(replay['source_ranges_json']) if replay['source_ranges_json'] else None)
        if db.execute('SELECT 1 FROM questions WHERE quiz_id = ? AND answered_option IS NULL LIMIT 1',
                      (quiz_id,)).fetchone():
            raise HTTPException(status_code=409, detail='Finish this quiz before retrying its mistakes')
        mistakes = db.execute('''SELECT * FROM questions WHERE quiz_id = ?
            AND answered_option IS NOT NULL AND answered_option <> correct_option ORDER BY ordinal''',
            (quiz_id,)).fetchall()
        if not mistakes:
            raise HTTPException(status_code=409, detail='This quiz has no answered mistakes to retry')
        retry_id = str(uuid.uuid4())
        title = f"Retry mistakes: {source['title']}"
        db.execute('''INSERT INTO quizzes
            (id, document_id, owner_id, title, created_at, difficulty, question_type, source_ranges_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (retry_id, source['document_id'], user_id, title, now(), source['difficulty'],
             source['question_type'], source['source_ranges_json']))
        for ordinal, question in enumerate(mistakes, start=1):
            db.execute('''INSERT INTO questions
                (id, quiz_id, ordinal, prompt, options_json, correct_option, explanation,
                 source_reference, question_type, chapter_id, concept) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (question_id(), retry_id, ordinal, question['prompt'], question['options_json'],
                 question['correct_option'], question['explanation'], question['source_reference'],
                 question['question_type'], question['chapter_id'], question['concept']))
        db.execute('''INSERT INTO quiz_retry_requests
            (owner_id, source_quiz_id, request_id, retry_quiz_id) VALUES (?, ?, ?, ?)''',
            (user_id, quiz_id, request_id, retry_id))
        first = db.execute('SELECT * FROM questions WHERE quiz_id = ? ORDER BY ordinal LIMIT 1',
                           (retry_id,)).fetchone()
    return QuizSummary(id=retry_id, title=title, question_count=len(mistakes),
        first_question=question_payload(first), difficulty=source['difficulty'],
        question_type=source['question_type'],
        source_ranges=parse_json(source['source_ranges_json']) if source['source_ranges_json'] else None)


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
    if catalog_chapter(request.subject_id, request.chapter_id) is None:
        raise HTTPException(status_code=422, detail='This subject or chapter is not in the current catalog')
    from .learning_path import missing_prerequisite
    with connection(settings.database_path) as db:
        required = missing_prerequisite(db, user_id, request.grade, request.subject_id, request.chapter_id)
    if required is not None:
        raise HTTPException(status_code=403, detail=f'Complete {required} in this grade before starting this chapter')
    try:
        consume_ai_operation(settings, user_id)
        bank = tutor_provider(settings).diagnostic_bank(request.grade, request.subject_id, request.chapter_id)
    except DiagnosticUnavailable as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail='A reviewed diagnostic is temporarily unavailable. Please retry.') from error
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
               (id, owner_id, grade, subject_id, chapter_id, catalog_version, started_at, questions_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, user_id, request.grade, request.subject_id.lower(), request.chapter_id.lower(),
             CATALOG_VERSION, now(), serialize_diagnostic_bank(bank)),
        )
    return DiagnosticSession(id=session_id, status="diagnostic", question=public_question(bank[0], 0, len(bank)),
                             state_token=mastery_state_token(dict(id=session_id, status='diagnostic', current_question=0, correct_answers=0, coaching_rounds=0)))


@app.post("/v1/mastery/sessions/{session_id}/diagnostic-answer", response_model=DiagnosticOutcome)
def answer_diagnostic(session_id: str, request: DiagnosticAnswerRequest, user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> DiagnosticOutcome:
    session = owned_mastery_session(session_id, user_id, settings)
    fingerprint = request_fingerprint(request)
    if prior := replay_mastery_mutation(settings, session_id, 'diagnostic-answer', request.expected_state,
                                        fingerprint, DiagnosticOutcome):
        return prior
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
        consume_ai_operation(settings, user_id)
        interests = account_profile(user_id, settings).interests
        provider = tutor_provider(settings, interests=tuple(interests)) if interests else tutor_provider(settings)
        try:
            lesson = provider.explain(session["grade"], item, request.selected_option)
        except TutorLessonUnavailable as error:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                                detail='A reviewed tutor lesson is temporarily unavailable. Your answer was not saved; please retry.') from error
    score = next_index / len(bank)
    next_question = public_question(bank[next_index], next_index, len(bank)) if correct and next_index < len(bank) else None
    outcome = DiagnosticOutcome(
        state_token=mastery_state_token(session, current_question=next_index, correct_answers=new_correct, status=next_status),
        correct=correct,
        selected_option=request.selected_option,
        correct_option=item.correct_option,
        mastery_score=score,
        next_action="mastery" if next_status == "mastered" else ("next_question" if correct else "tutor"),
        next_question=next_question,
        tutor=lesson,
    )
    try:
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
            save_mastery_mutation(db, session_id, 'diagnostic-answer', request.expected_state, fingerprint, outcome)
    except HTTPException as error:
        if error.status_code == 409 and (prior := replay_mastery_mutation(
                settings, session_id, 'diagnostic-answer', request.expected_state, fingerprint, DiagnosticOutcome)):
            return prior
        raise
    return outcome


@app.get('/v1/mastery/sessions/{session_id}/tutor-questions', response_model=list[TutorTurn])
def get_tutor_questions(session_id: str, user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)):
    return conversation_history(owned_mastery_session(session_id, user_id, settings), settings)


@app.post('/v1/mastery/sessions/{session_id}/tutor-questions', response_model=TutorTurn)
def ask_tutor_question(session_id: str, request: TutorQuestionRequest, user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)):
    session = owned_mastery_session(session_id, user_id, settings)
    if session['status'] not in {'tutor', 'practice'}:
        raise HTTPException(409, 'Tutor questions are available during tutoring and practice.')
    item = session_diagnostic_bank(session)[session['current_question']]
    return answer_tutor_follow_up(session, item, request, settings, tutor_provider(settings),
                                  before_provider=lambda: consume_ai_operation(settings, user_id))


@app.post("/v1/mastery/sessions/{session_id}/practice", response_model=PracticeOutcome)
def submit_practice(session_id: str, request: PracticeRequest, user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> PracticeOutcome:
    session = owned_mastery_session(session_id, user_id, settings)
    fingerprint = request_fingerprint(request)
    if prior := replay_mastery_mutation(settings, session_id, 'practice', request.expected_state,
                                        fingerprint, PracticeOutcome):
        return prior
    check_expected_state(session, request.expected_state)
    if session["status"] not in {"tutor", "practice"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Guided practice is not available in the current phase")
    bank = session_diagnostic_bank(session)
    item = bank[session["current_question"]]
    correct, normalized = response_matches(request.response, item.practice_answers, item.answer_mode)
    next_item = None
    next_lesson = None
    if not correct and request.fresh_practice:
        consume_ai_operation(settings, user_id)
        with connection(settings.database_path) as db:
            previous_prompts = tuple(row['prompt'] for row in db.execute(
                "SELECT prompt FROM mastery_attempts WHERE session_id = ? AND phase = 'practice' ORDER BY created_at",
                (session_id,))) + (item.practice_prompt,)
        interests = tuple(account_profile(user_id, settings).interests)
        next_item = tutor_provider(settings, interests).fresh_practice(
            session['grade'], session['subject_id'], session['chapter_id'], item,
            session['coaching_rounds'] + 1, previous_prompts)
        if next_item is not None:
            lesson = TutorIntervention.model_validate_json(session['tutor_json']) if session['tutor_json'] else tutor_for(item)
            next_lesson = lesson.model_copy(update={'practice_prompt': next_item.practice_prompt, 'hint': next_item.hint})
    outcome = PracticeOutcome(
        state_token=mastery_state_token(session, status='rewrite' if correct else 'practice', coaching_rounds=session['coaching_rounds'] + int(not correct)),
        correct=correct,
        normalized_answer=normalized,
        hint=None if correct else (next_item.hint if next_item else item.hint),
        next_practice=next_lesson,
        next_action="rewrite" if correct else "more_practice",
    )
    try:
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
            save_mastery_mutation(db, session_id, 'practice', request.expected_state, fingerprint, outcome)
    except HTTPException as error:
        if error.status_code == 409 and (prior := replay_mastery_mutation(
                settings, session_id, 'practice', request.expected_state, fingerprint, PracticeOutcome)):
            return prior
        raise
    return outcome


@app.post("/v1/mastery/sessions/{session_id}/rewrite", response_model=RewriteOutcome)
def submit_rewrite(session_id: str, request: RewriteRequest, user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> RewriteOutcome:
    session = owned_mastery_session(session_id, user_id, settings)
    fingerprint = request_fingerprint(request)
    if prior := replay_mastery_mutation(settings, session_id, 'rewrite', request.expected_state,
                                        fingerprint, RewriteOutcome):
        return prior
    check_expected_state(session, request.expected_state)
    if session["status"] != "rewrite":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A concept rewrite is not pending")
    bank = session_diagnostic_bank(session)
    item = bank[session["current_question"]]
    interests = tuple(account_profile(user_id, settings).interests)
    consume_ai_operation(settings, user_id)
    provider = tutor_provider(settings, interests)
    assessment = provider.assess_rewrite(session["grade"], item, request.response)
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
    if not understood and request.fresh_practice:
        consume_ai_operation(settings, user_id)
        with connection(settings.database_path) as db:
            previous_prompts = tuple(row['prompt'] for row in db.execute(
                "SELECT prompt FROM mastery_attempts WHERE session_id = ? AND phase = 'practice' ORDER BY created_at",
                (session_id,))) + (item.practice_prompt,)
        next_item = provider.fresh_practice(
            session['grade'], session['subject_id'], session['chapter_id'], item,
            session['coaching_rounds'] + 1, previous_prompts)
        if next_item is not None:
            lesson = lesson.model_copy(update={'practice_prompt': next_item.practice_prompt, 'hint': next_item.hint})
    outcome = RewriteOutcome(
        next_practice=lesson if next_item is not None else None,
        state_token=mastery_state_token(session, status=next_status, current_question=next_index, coaching_rounds=session['coaching_rounds'] + int(not understood)),
        understood=understood,
        mastery_achieved=mastered,
        mastery_score=mastery_score,
        confidence=confidence_for(mastery_score),
        coaching=coaching,
        next_chapter_unlocked=mastered and unlocks_dependent_chapter(session['subject_id'], session['chapter_id']),
        next_action="mastery" if mastered else ("next_question" if understood else "tutor"),
        next_question=public_question(bank[next_index], next_index, len(bank)) if understood and not mastered else None,
        assessment_points=assessment.score,
        assessment_max_points=4 if assessment.score is not None else None,
        assessment_feedback=assessment.feedback,
    )
    try:
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
            save_mastery_mutation(db, session_id, 'rewrite', request.expected_state, fingerprint, outcome)
    except HTTPException as error:
        if error.status_code == 409 and (prior := replay_mastery_mutation(
                settings, session_id, 'rewrite', request.expected_state, fingerprint, RewriteOutcome)):
            return prior
        raise
    return outcome


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
        id=session_id, catalog_version=session['catalog_version'], grade=session["grade"],
        subject_id=session["subject_id"], chapter_id=session["chapter_id"],
        status=session["status"], question=public_question(item, index, len(bank)) if item else None,
        tutor=lesson, selected_option=answer["response"] if answer and lesson else None,
        mastery_score=index / len(bank), coaching_rounds=session["coaching_rounds"], started_at=session["started_at"],
        assessment_points=grading.get("score"), assessment_feedback=grading.get("feedback"),
    )


@app.get("/v1/progress/dashboard", response_model=ProgressDashboard)
def progress_dashboard(grade: int | None = Query(default=None, ge=1, le=12), user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> ProgressDashboard:
    from .study_time import observed_seconds
    from .learning_badges import learning_badges
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
    unresolved_by_concept = {}
    for attempt in attempts:
        # Guided practice alone is not evidence of independent understanding.
        if attempt['phase'] not in {'diagnostic', 'rewrite'}:
            continue
        session = by_session[attempt['session_id']]
        key = (session['grade'], session['subject_id'], session['chapter_id'], attempt['concept'].strip().casefold())
        if attempt['correct']:
            unresolved_by_concept.pop(key, None)
        else:
            previous = unresolved_by_concept.get(key)
            unresolved_by_concept[key] = (attempt, (previous[1] if previous else 0) + 1, session)
    unresolved = sorted(unresolved_by_concept.values(), key=lambda value: value[0]['attempt_order'], reverse=True)
    evidence = [WeakAreaEvidence(concept=attempt['concept'], grade=session['grade'],
                    subject_id=session['subject_id'], chapter_id=session['chapter_id'],
                    unresolved_independent_mistakes=count)
                for attempt, count, session in unresolved[:5]]
    weak_areas = list(dict.fromkeys(item.concept for item in evidence))
    subject_scores = {name: sum(values) / len(values) for name, values in subjects.items()}
    from .learning_path import PREREQUISITES
    mastered = {(chapter.subject_id, chapter.chapter_id) for chapter in chapters if chapter.status == 'mastered'}
    unlocked = sorted(f'{subject}:{chapter}' for (subject, chapter), required in PREREQUISITES.items()
                      if grade is not None and (subject, required) in mastered)
    titles = {(subject.id, chapter.id): (subject.title, chapter.title)
              for subject in CATALOG for chapter in subject.chapters}
    if evidence:
        recommendations = []
        for item in evidence[:3]:
            subject_title, chapter_title = titles.get((item.subject_id, item.chapter_id),
                                                       (item.subject_id, item.chapter_id))
            count = item.unresolved_independent_mistakes
            recommendations.append(
                f"Review {item.concept} in {subject_title} · {chapter_title}: {count} unresolved independent mistake{'s' if count != 1 else ''}")
    else:
        ongoing = next((session for session in sessions if session['status'] != 'mastered'), None)
        if ongoing is not None:
            subject_title, chapter_title = titles.get((ongoing['subject_id'], ongoing['chapter_id']),
                                                       (ongoing['subject_id'], ongoing['chapter_id']))
            recommendations = [f"Continue {subject_title} · {chapter_title} from your saved {ongoing['status']} step"]
        elif grade is not None:
            available = next(((subject.title, chapter.title) for subject in CATALOG for chapter in subject.chapters
                              if (subject.id, chapter.id) not in mastered
                              and (chapter.prerequisite_id is None or (subject.id, chapter.prerequisite_id) in mastered)), None)
            recommendations = ([f"Start {available[0]} · {available[1]} as your next diagnostic"] if available
                               else ["All current catalog chapters are mastered. Revisit a chapter to strengthen retention."])
        else:
            recommendations = ["Choose a grade to get a prerequisite-aware next step."]
    return ProgressDashboard(observed_study_seconds=study_seconds, grade=grade, unlocked_chapter_ids=unlocked, subjects=subject_scores,
                             chapters=chapters, weak_areas=weak_areas, weak_area_evidence=evidence,
                             badges=learning_badges(sessions, attempts),
                             recommendations=recommendations)


@app.get("/v1/progress/weekly-report", response_model=WeeklyReport)
def weekly_report(grade: int | None = Query(default=None, ge=1, le=12), user_id: str = Depends(current_user_id), settings: Settings = Depends(get_settings)) -> WeeklyReport:
    as_of = datetime.fromisoformat(now())
    with connection(settings.database_path) as db:
        sessions, attempts = load_weekly_rows(db, user_id, grade, as_of)
    report = build_weekly_report(sessions, attempts, as_of,
                                 {row['id']: len(session_diagnostic_bank(row)) for row in sessions})
    from .study_time import observed_seconds
    with connection(settings.database_path) as db:
        report.observed_study_seconds = observed_seconds(db, user_id, grade,
            datetime.fromisoformat(report.period_start), datetime.fromisoformat(report.period_end))
    return report


@app.get('/v1/guardian/learners/{learner_id}/progress/dashboard', response_model=ProgressDashboard)
def guardian_progress_dashboard(learner_id: str, grade: int | None = Query(default=None, ge=1, le=12),
                                user_id: str = Depends(current_user_id),
                                settings: Settings = Depends(get_settings)) -> ProgressDashboard:
    require_link(user_id, learner_id, settings)
    return progress_dashboard(grade, learner_id, settings)


@app.get('/v1/guardian/learners/{learner_id}/progress/weekly-report', response_model=WeeklyReport)
def guardian_weekly_report(learner_id: str, grade: int | None = Query(default=None, ge=1, le=12),
                           user_id: str = Depends(current_user_id),
                           settings: Settings = Depends(get_settings)) -> WeeklyReport:
    require_link(user_id, learner_id, settings)
    return weekly_report(grade, learner_id, settings)
