# Saras — Learning Android App

An AI-powered interactive study and quiz application that transforms a student's own study material into a grounded, chapter-based learning experience.

The product loop is:

**Learn → Answer → Understand the mistake → Improve → Continue**

## Project status

The core Android learning loop and local backend are implemented. Students can upload PDF/DOCX/TXT material, review detected chapters, select sections/pages/topics, practice one question at a time, read immediate feedback and sources, review mistakes, retry incorrect questions, and track chapter progress. Accounts, documents, and quizzes persist across restarts.

The default **local practice mode** needs no API key. It generates exact-passage recall questions and clearly identifies its limitations. The optional OpenAI adapter and AI difficulty controls are implemented and tested with simulated provider responses; live generation awaits the user's API key and model configuration. No live AI request has been made.

The user-supplied **Saras Logos** email establishes the Saras brand name. The supplied Modern and Heritage artwork has not yet been imported because attachment retrieval was interrupted; the launcher currently uses a temporary book symbol.

The `god-mode` branch now adds scanned-PDF OCR with original-page confirmation, local semantic search, focused adaptive practice, source-backed flashcards, and SM-2 spaced review. See the [acceptance ledger](docs/god-mode/requirements.md) and [reconciliation audit](docs/god-mode/reconciliation.md) for verified scope and the remaining offline/chat/release work.

## MVP goal

The first release should support:

1. Uploading PDF, DOCX, or TXT study material up to 50 MB.
2. Extracting text and detecting chapters or sections.
3. Selecting a document, chapter, section, page range, or custom topic.
4. Generating ten source-grounded questions.
5. Presenting one question at a time with immediate teaching feedback.
6. Showing quiz results and allowing incorrect questions to be reviewed.

## Repository structure

```text
android/app/src/main/     Compose UI, ViewModel, repository, and domain rules
android/app/src/test/     JVM tests
android/app/src/androidTest/  Emulator learning-flow test
android/gradle/           Pinned Gradle wrapper
backend/study/            API, extraction, retrieval, quiz rules, provider, storage
backend/tests/            Backend and simulated-provider tests
shared/contracts/         Generated OpenAPI request and response schemas
shared/sample-study-material.txt  Sample for a ten-question practice session
docs/                     Architecture, API, and product documentation
scripts/                  Start, build, test, and contract-export utilities
```

The original empty scaffold directories remain available for future module extraction; active backend code currently lives in `backend/study/` and active Android code in the application module.

## Architecture direction

The Android client will use Kotlin, Jetpack Compose, Material 3, coroutines/Flow, and a layered MVVM or Clean Architecture approach. Local persistence will use Room where offline or cached state is useful.

The backend will own authentication, document storage, parsing, retrieval, AI calls, quiz validation, and progress persistence. Provider credentials must never be shipped in the APK.

Large documents will follow a retrieval-based pipeline:

```text
Upload → Extract → Detect structure → Chunk → Index → Retrieve → Generate structured quiz → Validate → Present
```

Questions and explanations must be grounded in the selected material and retain source references whenever possible.

## Product principles

- Teach through feedback; do not only mark answers right or wrong.
- Prefer reliable, source-supported questions over unsupported questions.
- Keep the student experience focused and avoid exposing unnecessary AI controls.
- Protect uploaded documents and give users deletion controls.
- Design interfaces and contracts so future flashcards, tutor chat, adaptive learning, OCR, and additional clients can be added without rewriting the MVP.

## Run locally on Windows

Requirements: Python 3.11+, JDK 17, and Android SDK 35 (or Android Studio). A local toolchain used for verification is available under ignored `work/toolchain/` on this machine; `scripts/build-android.ps1` detects it automatically.

Start the backend from the repository root:

```powershell
.\scripts\start-backend.ps1
```

The server listens at `http://127.0.0.1:8000`; interactive API docs are at `/docs`. Android Emulator reaches this server using `http://10.0.2.2:8000`, the app's default server URL. Create an account in the app, then upload `shared/sample-study-material.txt` to try a ten-question session. Usernames require 3+ letters/digits/`_.-`; passwords require 10+ characters. The APK is a client and still needs the backend running.

Before using scanned PDFs or semantic topics, prepare and verify the public local models in another terminal. This downloads models, not documents, and requires no API key:

```powershell
.venv/Scripts/python scripts/prepare-models.py
.venv/Scripts/python scripts/prepare-models.py --verify
```

Open `android/` in Android Studio, or build and verify:

```powershell
.\scripts\build-android.ps1
.\scripts\test-backend.ps1
```

Debug APK: `android/app/build/outputs/apk/debug/app-debug.apk`. For a physical device, use an HTTPS backend, or `adb reverse tcp:8000 tcp:8000` and set the debug app's server URL to `http://127.0.0.1:8000`. Release builds require HTTPS. No provider credential belongs in the APK.

Backend dependencies are specified in `backend/requirements.txt`; the verified environment is pinned in `backend/requirements-lock.txt`. The first start script creates `.venv/`. To reproduce exact versions, install the lock file with `.venv/Scripts/python -m pip install -r backend/requirements-lock.txt`.

## AI setup later

Local mode does not read or require an API key. When ready, configure the ignored `.env.local` with `STUDY_GENERATION_MODE=openai`, an authorized `OPENAI_API_KEY`, and `OPENAI_MODEL` for a model supporting Responses structured outputs. The start script loads `.env.local` if present. The server then enables semantic generation and all difficulty levels. Live provider access, output quality, and model availability still need validation at that stage. `.env.example` documents configuration names without credentials.

## Automated verification

Backend tests cover uploads and extraction failures, nested chapter boundaries, quote validation, answer transitions and retries, persistence, ownership, encryption, retention, account deletion, and simulated provider success/failure/review. Android JVM tests cover answer gating and count validation. The emulator instrumentation test covers a full ten-question session, source viewing, activity recreation, results, mistake review, and retrying incorrect questions. It uses a disposable backend on port **18763**, which must be running separately with `STUDY_DATA_DIR` pointing to test storage:

```powershell
$env:STUDY_DATA_DIR = "$PWD/work/ui-test-data"
.venv/Scripts/python -m uvicorn study.api:create_app --factory --app-dir backend --host 127.0.0.1 --port 18763
# In another PowerShell session with an emulator running:
.\scripts\build-android.ps1 -ConnectedTests
```

This is a locally runnable application, not a deployed public service. Production deployment still requires the operational safeguards listed in [implementation notes](docs/architecture/implementation.md). See [OCR/search/adaptive notes](docs/god-mode/ocr-search-adaptive.md) and [document tutor notes](docs/god-mode/document-tutor.md) for actual local-model checks and limitations; live OpenAI quality remains unverified until setup.

Read [INSTRUCTIONS.md](INSTRUCTIONS.md), [API usage](docs/api/usage.md), and the full [product requirements](Initial_plan.md) for context.

