import hashlib
import hmac
import os
import secrets
import time
import uuid
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from .documents import MAX_BYTES, MAX_TEXT, DocumentError, extract, retrieve, structure
from .quizzes import GenerationError, generate_local, public_question
from .storage import Store
from .provider import configured_provider
from .models import DocumentMetadata, Passage, Progress, QuizSnapshot, Results
from .flashcards import from_question, public_card, review as rate_flashcard
from .processing import analyze_upload, update_review_state
from .semantic import SemanticUnavailable, build_index, fingerprint, search as semantic_search
from .adaptive import recommend


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=10, max_length=128)


class Selection(BaseModel):
    section_ids: list[str] = Field(default_factory=list, max_length=100)
    page_start: int | None = None
    page_end: int | None = None
    topic: str = Field(default="", max_length=200)


class QuizRequest(BaseModel):
    selection: Selection = Field(default_factory=Selection)
    count: int = Field(default=10, ge=1, le=50)
    difficulty: Literal["easy", "medium", "hard", "mixed"] = "easy"
    question_type: Literal["multiple_choice", "true_false", "yes_no"] = "multiple_choice"


class Answer(BaseModel):
    question_id: str
    choice: int = Field(ge=0, le=3)


class Advance(BaseModel):
    expected_index: int = Field(ge=0)


class CardCreation(BaseModel):
    mistakes_only: bool = False


class CardRating(BaseModel):
    quality: int = Field(ge=0, le=5, strict=True)
    expected_version: int = Field(ge=0)
    request_id: str = Field(min_length=8, max_length=100)


class OcrReview(BaseModel):
    text: str = Field(max_length=20000)


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=300)
    selection: Selection = Field(default_factory=Selection)
    limit: int = Field(default=5, ge=1, le=10)


def create_app(data_dir: Path | None = None):
    app = FastAPI(title="Study Companion", version="0.1.0")
    store = Store(data_dir or Path(os.getenv("STUDY_DATA_DIR", "./.study-data")))
    app.state.store = store
    auth = HTTPBearer(auto_error=False)
    attempts = {}
    provider = configured_provider()
    mode = "openai" if provider else "local_practice"

    @app.middleware("http")
    async def upload_limit(request: Request, call_next):
        from starlette.responses import JSONResponse
        # Bound the entire request before multipart parsing can spool unbounded data.
        if request.url.path.endswith("/documents") and request.method == "POST":
            size = 0
            original_receive = request._receive

            async def receive():
                nonlocal size
                message = await original_receive()
                size += len(message.get("body", b""))
                if size > MAX_BYTES + 1024 * 1024:
                    raise HTTPException(413, "Upload exceeds 50 MB.")
                return message

            request._receive = receive
            try:
                declared_length = int(request.headers.get("content-length", "0"))
            except ValueError:
                return JSONResponse({"detail": "Invalid Content-Length."}, status_code=400)
            if declared_length > MAX_BYTES + 1024 * 1024:
                return JSONResponse({"detail": "Upload exceeds 50 MB."}, status_code=413)
        return await call_next(request)

    def owner(credentials: HTTPAuthorizationCredentials | None = Depends(auth)):
        if credentials is None:
            raise HTTPException(401, "Sign in to continue.")
        digest = hashlib.sha256(credentials.credentials.encode()).hexdigest()
        with store.lock:
            row = store.db.execute("SELECT owner FROM sessions WHERE token=? AND expires>?", (digest, time.time())).fetchone()
            if not row:
                raise HTTPException(401, "Your session expired. Sign in again.")
            # Documents and associated progress expire together after 30 days.
            expired = store.db.execute("SELECT id FROM records WHERE owner=? AND kind='document' AND created<?", (row[0], time.time() - 30 * 86400)).fetchall()
            for record in expired:
                store.db.execute("DELETE FROM records WHERE owner=? AND (id=? OR document=?)", (row[0], record[0], record[0]))
            store.db.commit()
            return row[0]

    def record(identifier, user, kind):
        value = store.get(identifier, user, kind)
        if value is None:
            raise HTTPException(404, "Item not found or no longer available.")
        return value

    def find_semantic_passages(doc, user, selected, query, limit=5):
        if doc.get("processing_state", "ready") != "ready":
            raise HTTPException(409, "Confirm uncertain scanned text before searching it.")
        identifier = "semantic-" + doc["id"]
        source_fingerprint = fingerprint(doc["passages"])
        with store.lock:
            index = store.get(identifier, user, "embedding")
        try:
            if index is None or index.get("fingerprint") != source_fingerprint:
                index = build_index(doc["passages"])
                with store.lock:
                    current = record(doc["id"], user, "document")
                    if fingerprint(current["passages"]) != source_fingerprint:
                        raise HTTPException(409, "The source changed while preparing search. Please retry.")
                    store.save(identifier, user, "embedding", doc["id"], doc["created"], index)
            hits = semantic_search(selected, index, query, limit=limit)
        except SemanticUnavailable as error:
            raise HTTPException(503, str(error))
        with store.lock:
            current = record(doc["id"], user, "document")
            if fingerprint(current["passages"]) != source_fingerprint:
                raise HTTPException(409, "The source changed during search. Please retry.")
        return hits

    def session(user):
        token = secrets.token_urlsafe(32)
        store.db.execute("INSERT INTO sessions VALUES (?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), user, time.time() + 30 * 86400))
        store.db.commit()
        return {"token": token, "expires_in": 30 * 86400}

    @app.get("/health")
    def health():
        return {"status": "ok", "generation_mode": mode, "ai_configured": provider is not None}

    @app.post("/auth/{action}")
    def authenticate(action: Literal["register", "login"], body: Credentials, request: Request):
        address = request.client.host if request.client else "unknown"
        with store.lock:
            now = time.time()
            # Bounded in-process local-server rate limiter; production needs a shared gateway.
            for ip in list(attempts):
                attempts[ip] = [t for t in attempts[ip] if t > now - 60]
                if not attempts[ip]:
                    del attempts[ip]
            history = attempts.setdefault(address, [])
            if len(history) >= 10:
                raise HTTPException(429, "Too many attempts. Try again in a minute.")
            history.append(now)
            username = body.username.lower()
            row = store.db.execute("SELECT * FROM users WHERE name=?", (username,)).fetchone()
            if action == "register":
                if row:
                    raise HTTPException(409, "This username is already taken.")
                salt = os.urandom(16)
                password = hashlib.scrypt(body.password.encode(), salt=salt, n=16384, r=8, p=1)
                user = str(uuid.uuid4())
                store.db.execute("INSERT INTO users VALUES (?,?,?,?)", (user, username, salt, password))
                return session(user)
            salt = row["salt"] if row else b"0" * 16
            password = hashlib.scrypt(body.password.encode(), salt=salt, n=16384, r=8, p=1)
            if not row or not hmac.compare_digest(password, row["password"]):
                raise HTTPException(401, "Username or password is incorrect.")
            return session(row["id"])

    @app.delete("/auth/session", status_code=204)
    def logout(credentials: HTTPAuthorizationCredentials = Depends(auth), user=Depends(owner)):
        with store.lock:
            store.db.execute("DELETE FROM sessions WHERE token=? AND owner=?", (hashlib.sha256(credentials.credentials.encode()).hexdigest(), user))
            store.db.commit()

    @app.delete("/account", status_code=204)
    def delete_account(user=Depends(owner)):
        with store.lock:
            store.db.execute("DELETE FROM users WHERE id=?", (user,))
            store.db.commit()

    def metadata(doc):
        return {k: v for k, v in doc.items() if k != "passages" and not k.startswith("_")}

    @app.get("/documents", response_model=list[DocumentMetadata])
    def documents(user=Depends(owner)):
        with store.lock:
            return [metadata(doc) for doc in store.all(user, "document")]

    @app.post("/documents", status_code=201, response_model=DocumentMetadata)
    def upload(file: UploadFile, user=Depends(owner)):
        try:
            content = file.file.read(MAX_BYTES + 1)
            doc = analyze_upload(file.filename or "", content)
        except DocumentError as error:
            raise HTTPException(422, str(error))
        finally:
            file.file.close()
        doc.update(id=str(uuid.uuid4()), created=time.time(), filename=Path(file.filename or "document").name)
        with store.lock:
            store.save(doc["id"], user, "document", doc["id"], doc["created"], doc)
        return metadata(doc)

    @app.get("/documents/{identifier}", response_model=DocumentMetadata)
    def document(identifier: str, user=Depends(owner)):
        with store.lock:
            return metadata(record(identifier, user, "document"))

    @app.get("/documents/{identifier}/next-practice")
    def next_practice(identifier: str, user=Depends(owner)):
        with store.lock:
            doc = record(identifier, user, "document")
            if doc.get("processing_state", "ready") != "ready":
                raise HTTPException(409, "Confirm uncertain scanned pages before planning practice.")
            quizzes = store.for_document(user, "quiz", identifier)
        try:
            return recommend(doc, quizzes, ai_configured=provider is not None)
        except DocumentError as error:
            raise HTTPException(422, str(error))

    @app.get("/documents/{identifier}/passages/{passage_id}", response_model=Passage)
    def passage(identifier: str, passage_id: str, user=Depends(owner)):
        with store.lock:
            doc = record(identifier, user, "document")
            item = next((p for p in doc["passages"] if p["id"] == passage_id), None)
            if item is None:
                raise HTTPException(404, "Passage not found.")
            return {**item, "extraction": "ocr" if any(page["page"] == item["page"] for page in doc.get("_ocr_pages", [])) else "native"}

    @app.post("/documents/{identifier}/search")
    def search_document(identifier: str, body: SearchRequest, user=Depends(owner)):
        with store.lock:
            doc = record(identifier, user, "document")
        if doc.get("processing_state", "ready") != "ready":
            raise HTTPException(409, "Confirm uncertain scanned text before searching it.")
        if body.selection.topic:
            raise HTTPException(422, "Use the query field for a semantic topic, with section/page filters in selection.")
        try:
            selected = retrieve(doc, body.selection.model_dump())
        except DocumentError as error:
            raise HTTPException(422, str(error))
        return {"mode": "local_semantic", "hits": find_semantic_passages(doc, user, selected, body.query, body.limit)}

    @app.get("/documents/{identifier}/ocr-pages")
    def ocr_pages(identifier: str, user=Depends(owner)):
        with store.lock:
            doc = record(identifier, user, "document")
            return [{k: v for k, v in page.items() if k != "image_base64"} for page in doc.get("_ocr_pages", [])]

    @app.get("/documents/{identifier}/ocr-pages/{page_number}")
    def ocr_page(identifier: str, page_number: int, user=Depends(owner)):
        with store.lock:
            doc = record(identifier, user, "document")
            page = next((page for page in doc.get("_ocr_pages", []) if page["page"] == page_number), None)
            if page is None:
                raise HTTPException(404, "Scanned page not found.")
            return page

    @app.post("/documents/{identifier}/ocr-pages/{page_number}/review", response_model=DocumentMetadata)
    def review_ocr(identifier: str, page_number: int, body: OcrReview, user=Depends(owner)):
        with store.lock:
            doc = record(identifier, user, "document")
            page = next((page for page in doc.get("_ocr_pages", []) if page["page"] == page_number), None)
            if page is None:
                raise HTTPException(404, "Scanned page not found.")
            text = body.text.strip()
            if page["human_reviewed"]:
                if text != page["text"]:
                    raise HTTPException(409, "This transcription was already confirmed. Upload a corrected copy to change it.")
                return metadata(doc)
            if store.db.execute("SELECT 1 FROM records WHERE owner=? AND kind='quiz' AND document=? LIMIT 1", (user, identifier)).fetchone():
                raise HTTPException(409, "This document already has quizzes. Upload a corrected copy to change its source text.")
            pages = list(doc["_pages"])
            pages[page_number - 1] = text
            if sum(map(len, pages)) > MAX_TEXT:
                raise HTTPException(422, "Confirmed transcription exceeds the 2 million character document limit.")
            try:
                rebuilt = structure(doc["filename"], pages)
            except DocumentError as error:
                raise HTTPException(422, str(error))
            page.update(text=text, reviewed=True, human_reviewed=True)
            doc.update(rebuilt, _pages=pages)
            doc["source_revision"] = doc.get("source_revision", 0) + 1
            update_review_state(doc)
            store.save(identifier, user, "document", identifier, doc["created"], doc)
            return metadata(doc)

    @app.delete("/documents/{identifier}", status_code=204)
    def delete_document(identifier: str, user=Depends(owner)):
        with store.lock:
            record(identifier, user, "document")
            store.db.execute("DELETE FROM records WHERE owner=? AND (id=? OR document=?)", (user, identifier, identifier))
            store.db.commit()

    def snapshot(quiz):
        index = quiz["index"]
        done = index >= len(quiz["questions"])
        feedback = None
        if not done and len(quiz["answers"]) > index:
            feedback = quiz["answers"][index]
        return {"id": quiz["id"], "document_id": quiz["document_id"], "index": index, "count": len(quiz["questions"]),
                "mode": quiz.get("mode", "local_practice"), "complete": done, "question": None if done else public_question(quiz["questions"][index]), "feedback": feedback}

    @app.post("/documents/{identifier}/quizzes", status_code=201, response_model=QuizSnapshot)
    def create_quiz(identifier: str, body: QuizRequest, user=Depends(owner)):
        with store.lock:
            doc = record(identifier, user, "document")
            if doc.get("processing_state", "ready") != "ready":
                raise HTTPException(409, "Review the uncertain scanned pages before creating a quiz.")
        try:
            selection = body.selection.model_dump()
            topic = selection.pop("topic", "").strip()
            passages = retrieve(doc, selection)
            if topic:
                hits = find_semantic_passages(doc, user, passages, topic, 100)
                supported = {hit["source_id"] for hit in hits}
                passages = [passage for passage in passages if passage["id"] in supported]
                if not passages:
                    raise DocumentError("No supported passages match that topic. Broaden the topic or selected material.")
            generator = provider.generate if provider else generate_local
            questions = generator(passages, body.count, body.question_type, body.difficulty)
        except (DocumentError, GenerationError) as error:
            raise HTTPException(422, str(error))
        with store.lock:
            current = record(identifier, user, "document")  # Do not resurrect data deleted during generation.
            if current.get("source_revision", 0) != doc.get("source_revision", 0):
                raise HTTPException(409, "The source changed during generation. Start the quiz again using the confirmed text.")
            quiz = {"id": str(uuid.uuid4()), "document_id": identifier, "mode": mode, "questions": questions, "index": 0, "answers": [], "created": time.time()}
            store.save(quiz["id"], user, "quiz", identifier, quiz["created"], quiz)
            current["source_locked"] = True
            store.save(identifier, user, "document", identifier, current["created"], current)
            return snapshot(quiz)

    @app.get("/quizzes/{identifier}", response_model=QuizSnapshot)
    def get_quiz(identifier: str, user=Depends(owner)):
        with store.lock:
            return snapshot(record(identifier, user, "quiz"))

    @app.post("/quizzes/{identifier}/answers", response_model=QuizSnapshot)
    def answer(identifier: str, body: Answer, user=Depends(owner)):
        with store.lock:
            quiz = record(identifier, user, "quiz")
            index = quiz["index"]
            if index >= len(quiz["questions"]):
                raise HTTPException(409, "This quiz is complete.")
            question = quiz["questions"][index]
            if question["id"] != body.question_id or body.choice >= len(question["choices"]):
                raise HTTPException(409, "Refresh this question before answering.")
            if len(quiz["answers"]) > index:
                if quiz["answers"][index]["selected"] != body.choice:
                    raise HTTPException(409, "This answer was already submitted.")
                return snapshot(quiz)  # retry after a lost response is idempotent
            quiz["answers"].append({"question_id": question["id"], "selected": body.choice,
                                     "correct": body.choice == question["answer"], "answer": question["answer"],
                                     "explanation": question["explanation"], "quote": question["quote"]})
            store.save(identifier, user, "quiz", quiz["document_id"], quiz["created"], quiz)
            return snapshot(quiz)

    @app.post("/quizzes/{identifier}/next", response_model=QuizSnapshot)
    def next_question(identifier: str, body: Advance, user=Depends(owner)):
        with store.lock:
            quiz = record(identifier, user, "quiz")
            # expected_index makes retried navigation safe.
            if body.expected_index != quiz["index"]:
                return snapshot(quiz)
            if quiz["index"] >= len(quiz["answers"]):
                raise HTTPException(409, "Submit an answer first.")
            quiz["index"] += 1
            store.save(identifier, user, "quiz", quiz["document_id"], quiz["created"], quiz)
            return snapshot(quiz)

    def results(quiz):
        if quiz["index"] < len(quiz["questions"]):
            raise HTTPException(409, "Complete the quiz to view results.")
        correct = sum(a["correct"] for a in quiz["answers"])
        concepts = {}
        mistakes = []
        for question, response in zip(quiz["questions"], quiz["answers"]):
            counts = concepts.setdefault(question["concept"], [0, 0])
            counts[0] += int(response["correct"])
            counts[1] += 1
            if not response["correct"]:
                mistakes.append({"question": public_question(question), "feedback": response})
        return {"id": quiz["id"], "correct": correct, "incorrect": len(quiz["answers"]) - correct,
                "total": len(quiz["answers"]), "accuracy": round(100 * correct / len(quiz["answers"])),
                "concepts": [{"id": k, "correct": v[0], "total": v[1]} for k, v in concepts.items()], "mistakes": mistakes}

    @app.get("/quizzes/{identifier}/results", response_model=Results)
    def quiz_results(identifier: str, user=Depends(owner)):
        with store.lock:
            return results(record(identifier, user, "quiz"))

    @app.post("/quizzes/{identifier}/retry", status_code=201, response_model=QuizSnapshot)
    def retry(identifier: str, user=Depends(owner)):
        with store.lock:
            previous = record(identifier, user, "quiz")
            results(previous)
            questions = [q for q, a in zip(previous["questions"], previous["answers"]) if not a["correct"]]
            if not questions:
                raise HTTPException(422, "No incorrect questions to retry.")
            quiz = {"id": str(uuid.uuid4()), "document_id": previous["document_id"], "mode": previous.get("mode", "local_practice"), "questions": questions, "index": 0, "answers": [], "created": time.time()}
            store.save(quiz["id"], user, "quiz", quiz["document_id"], quiz["created"], quiz)
            return snapshot(quiz)

    @app.get("/progress", response_model=Progress)
    def progress(user=Depends(owner)):
        with store.lock:
            quizzes = store.all(user, "quiz")
            completed = [q for q in quizzes if q["index"] == len(q["questions"])]
            answered = sum(len(q["answers"]) for q in completed)
            correct = sum(a["correct"] for q in completed for a in q["answers"])
            document_progress = []
            for doc in store.all(user, "document"):
                sections = []
                for section in doc["sections"]:
                    included = {section["id"]} | {s["id"] for s in doc["sections"] if s.get("parent_id") == section["id"]}
                    responses = [answer for quiz in completed if quiz["document_id"] == doc["id"]
                                 for question, answer in zip(quiz["questions"], quiz["answers"])
                                 if question.get("section_id", question["concept"]) in included]
                    sections.append({**section, "questions_answered": len(responses),
                                     "accuracy": round(100 * sum(a["correct"] for a in responses) / len(responses)) if responses else None})
                document_progress.append({"id": doc["id"], "title": doc["title"], "sections": sections})
            return {"quizzes_completed": len(completed), "questions_answered": answered,
                    "accuracy": round(100 * correct / answered) if answered else None,
                    "documents": document_progress,
                    "history": [{"document_id": q["document_id"], "created": q["created"], **results(q)} for q in completed],
                    "in_progress": [snapshot(q) for q in quizzes if q["index"] < len(q["questions"])]}

    @app.post("/quizzes/{identifier}/flashcards", status_code=201)
    def create_flashcards(identifier: str, body: CardCreation, user=Depends(owner)):
        with store.lock:
            quiz = record(identifier, user, "quiz")
            results(quiz)
            cards = []
            for question, response in zip(quiz["questions"], quiz["answers"]):
                if body.mistakes_only and response["correct"]:
                    continue
                card = from_question(quiz["document_id"], question)
                existing = store.get(card["id"], user, "flashcard")
                if existing is None:
                    store.save(card["id"], user, "flashcard", quiz["document_id"], card["created"], card)
                cards.append(public_card(existing or card))
            return cards

    @app.get("/flashcards")
    def flashcards(document_id: str | None = None, due_only: bool = True, user=Depends(owner)):
        with store.lock:
            if document_id is not None:
                record(document_id, user, "document")
            cards = store.all(user, "flashcard")
            now = time.time()
            return [public_card(card) for card in sorted(cards, key=lambda card: (card["review"]["due_at"], card["id"]))
                    if (document_id is None or card["document_id"] == document_id)
                    and (not due_only or card["repeat_today"] or card["review"]["due_at"] <= now)]

    @app.post("/flashcards/{identifier}/reviews")
    def rate_card(identifier: str, body: CardRating, user=Depends(owner)):
        with store.lock:
            card = record(identifier, user, "flashcard")
            try:
                updated = rate_flashcard(card, body.quality, body.expected_version, body.request_id, time.time())
            except ValueError as error:
                raise HTTPException(409, str(error))
            store.save(identifier, user, "flashcard", card["document_id"], card["created"], updated)
            return public_card(updated)

    return app
