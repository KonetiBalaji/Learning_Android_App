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

from .documents import MAX_BYTES, DocumentError, extract, retrieve, structure
from .quizzes import GenerationError, generate_local, public_question
from .storage import Store
from .provider import configured_provider
from .models import DocumentMetadata, Passage, Progress, QuizSnapshot, Results


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
        return {k: v for k, v in doc.items() if k != "passages"}

    @app.get("/documents", response_model=list[DocumentMetadata])
    def documents(user=Depends(owner)):
        with store.lock:
            return [metadata(doc) for doc in store.all(user, "document")]

    @app.post("/documents", status_code=201, response_model=DocumentMetadata)
    def upload(file: UploadFile, user=Depends(owner)):
        try:
            content = file.file.read(MAX_BYTES + 1)
            doc = structure(file.filename or "", extract(file.filename or "", content))
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

    @app.get("/documents/{identifier}/passages/{passage_id}", response_model=Passage)
    def passage(identifier: str, passage_id: str, user=Depends(owner)):
        with store.lock:
            doc = record(identifier, user, "document")
            item = next((p for p in doc["passages"] if p["id"] == passage_id), None)
            if item is None:
                raise HTTPException(404, "Passage not found.")
            return item

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
        try:
            passages = retrieve(doc, body.selection.model_dump())
            generator = provider.generate if provider else generate_local
            questions = generator(passages, body.count, body.question_type, body.difficulty)
        except (DocumentError, GenerationError) as error:
            raise HTTPException(422, str(error))
        with store.lock:
            record(identifier, user, "document")  # Do not resurrect data deleted during generation.
            quiz = {"id": str(uuid.uuid4()), "document_id": identifier, "mode": mode, "questions": questions, "index": 0, "answers": [], "created": time.time()}
            store.save(quiz["id"], user, "quiz", identifier, quiz["created"], quiz)
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

    return app
