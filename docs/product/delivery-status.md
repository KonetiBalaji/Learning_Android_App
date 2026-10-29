# Delivery status — October 28, 2026

## Implemented and verified

- Kotlin / Compose / Material 3 Android app with server account sign-in.
- PDF, DOCX, and TXT upload and readable validation failures.
- Chapter, subsection, and DOCX heading detection with uncertain-structure fallback.
- Whole-document, chapter, multi-section, PDF page, and lexical topic selection.
- Question count configuration and three question formats.
- Explicit local exact-passage recall practice requiring no API key.
- One question at a time; immediate correct/incorrect feedback and source passage viewing.
- Server-persisted quizzes, idempotent answer/advance retries, activity recreation recovery, and resumable sessions.
- Score and accuracy, concept review, retrying mistakes, history, and chapter progress.
- Password hashing, bearer sessions, owner checks, encrypted document/quiz storage, deletion paths, and documented retention.
- Optional OpenAI adapter with strict structured output, bounded retrieval, source validation, independent review, and redacted errors. Tested with a simulated transport only.
- Generated OpenAPI contract, sample study material, pinned backend environment, Gradle wrapper, and build/start/test scripts.

## Verification

- **31 backend tests passed.** Includes real text PDF and DOCX extraction, nested selection boundaries, storage recovery protection, ownership, deletion, retention, source validation, and simulated provider behavior.
- **2 Android JVM tests passed.** Answer gating and question count validation.
- **1 full emulator instrumentation test passed on Android 15 / API 35.** Exercises sign-up, offline failure and retry, document upload, ten questions, source viewing, activity recreation, a 90% result, mistake review, and retrying the one incorrect question.
- **Debug APK build and Android lint passed.** Lint retains dependency-update and optional KTX-style warnings; no lint errors.
- **Python dependency consistency passed.** No broken requirements.

## Deferred or blocked

- API key and model configuration: deliberately deferred by the user. No live OpenAI calls, quota charges, credential creation, or secret writes occurred. AI access and educational quality still require live validation after setup.
- Original Saras artwork: the supplied email was read, and the Saras name incorporated. Modern and Heritage PNG/SVG assets are identified, but download failed and browser automation subsequently stopped because it could not verify the URL. The current book icon is temporary.
- Public production deployment and release signing are not performed. The README and architecture notes distinguish the locally runnable MVP from the operational requirements for a public service.
- OCR, embeddings/semantic topic retrieval, adaptive tutoring, flashcards, offline quiz caching, and other features listed as future enhancements remain outside the MVP.
