# Learning Android App

An AI-powered interactive study and quiz application that transforms a student's own study material into a grounded, chapter-based learning experience.

The product loop is:

**Learn → Answer → Understand the mistake → Improve → Continue**

## Project status

The MVP implementation is in progress on `agent/mvp-implementation`:

- `android/` contains the Jetpack Compose client for account creation, document selection, chapter selection, the one-question quiz experience, teaching feedback, and results/mistake review.
- `backend/` contains the FastAPI service that owns authentication, document validation/extraction, chapter detection, grounded quiz sessions, answer evaluation, and owner-scoped deletion.
- The Grade 8 learning path now persists diagnostic answers, tutoring interventions, guided practice, student rewrites, mastery evidence, and parent/teacher progress. All current Mathematics, Science, and English chapters have app-owned deterministic diagnostic fallbacks; configured OpenAI generation remains independently reviewed and fails closed before persistence.

The backend test suite passes. Android APK compilation requires a locally accepted Android SDK license; see `android/README.md`.

## Backend entry points

Opening the backend origin returns a small service landing response. Use
`/health` for runtime health and `/docs` for the interactive API reference; the
Android client uses the authenticated `/v1/*` routes.

## MVP goal

The first release should support:

1. Uploading PDF, DOCX, or TXT study material up to 50 MB.
2. Extracting text and detecting chapters or sections.
3. Selecting a document, chapter, section, page range, or custom topic.
4. Generating ten source-grounded questions.
5. Presenting one question at a time with immediate teaching feedback.
6. Showing quiz results and allowing incorrect questions to be reviewed.

## Planned repository structure

```text
android/                  Kotlin Android client
├── app/                  Application entry point and navigation
├── core/                 Shared Android infrastructure
├── data/                 Repositories and data sources
├── domain/               Use cases and domain models
├── feature/              Feature-specific UI and state
└── ui/                   Design system and shared Compose UI

backend/                  Secure server-side application
├── api/                  HTTP API and authentication boundary
├── document-processing/  Upload, extraction, validation, and structure detection
├── ai/                   Prompting, generation, and response validation
├── retrieval/            Chunking, indexing, embeddings, and grounded retrieval
├── progress/             Quiz history and learning analytics
└── tests/                Backend test suites

shared/contracts/         API schemas and cross-service contracts
docs/                     Architecture, API, and product documentation
scripts/                  Developer and maintenance utilities
```

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

## Getting started

Read [INSTRUCTIONS.md](INSTRUCTIONS.md) before adding implementation. The backend can be run now; the Android app can be built once the Android SDK is installed locally.

The full product requirements are in [Initial_plan.md](Initial_plan.md).
