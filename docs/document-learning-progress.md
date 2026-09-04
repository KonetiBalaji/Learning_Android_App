# Uploaded-document learning progress

## Contract

`GET /v1/documents/{document_id}/progress` is authenticated and owner scoped. A
missing or other-owner document returns the same 404. The response derives from
saved quizzes and answers rather than client counters and reports:

- created and fully completed quiz counts;
- cumulative answered/correct counts and accuracy;
- every attempt's created/completed timestamps and completion state;
- mistake-retry provenance without exposing another account;
- the percentage-point change between the two latest completed attempts; and
- up to three strongest and weakest grounded source references.

Unfinished attempts contribute their answered questions to cumulative totals but
never to the improvement trend. Completing the final question stamps the quiz in
the same database transaction. Historical fully answered quizzes without that
stamp remain readable using their final answer timestamp.

The Android chapter-selection screen fetches this authoritative record whenever a
saved document is opened or the learner returns to configuration from results. It
validates counts, accuracy and the finite trend vocabulary before displaying them.

## Automated evidence

`python -m pytest tests -q` from `backend` passed 559 tests with one existing
host-permission symlink skip. `test_document_progress.py` covers the zero state,
two-attempt improvement, source evidence, completion timestamps, unfinished-attempt
exclusion, authentication and owner isolation. Android JVM tests, lint and debug APK
assembly passed. Hosted quality-gate run 33888648953 passed repository hygiene,
backend, Android and locked production-container jobs for commit `1f76d59`.

## API 36 evidence

`scripts/qa-document-recovery.ps1 -ResetTestAppData -VerifyDocumentProgress`
passed on the dedicated `LearnSmart_API36` emulator against an isolated deterministic
backend after rebuilding the current APK. The disposable learner uploaded through
Android's system picker, survived process restarts, completed a ten-question quiz,
created and completed a mistake-only retry, then completed another ten-question
quiz. The runner checked three completed server attempts, 27 answered questions,
non-empty completion timestamps and retry provenance before matching the Android
text to the server response.

`artifacts/qa-document-progress.png` was visually inspected at 1080 by 2400. It
shows 3 completed quizzes, 27 answers, 22% cumulative accuracy, a 30 percentage-point
improvement, and distinct review/strong source areas. Captures remain untracked.

This proves per-document aggregate history and recent-attempt improvement for the
tested path. A source reference is shown as a source area; it is not represented as
an AI-inferred concept. Chapter percentages and true named weak/strong concepts need
durable question attribution, and physical-device/user acceptance remain open.
