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
- per-detected-chapter answer accuracy, including explicit not-started chapters;
- up to three strongest and weakest grounded concept terms; and
- legacy source-area evidence when historical questions predate attribution.

Unfinished attempts contribute their answered questions to cumulative totals but
never to the improvement trend. Completing the final question stamps the quiz in
the same database transaction. Historical fully answered quizzes without that
stamp remain readable using their final answer timestamp.

New deterministic questions use the first substantive term copied from their exact
source sentence. Live-provider questions must return a short concept term or phrase
copied verbatim from the reconstructed supporting quote; invented labels fail the
entire generation batch before persistence. Chapter IDs must resolve through the
server-validated selection, including excerpt selections. Both attribution columns
are nullable so migration preserves historical rows without guessing.

The Android chapter-selection screen fetches this authoritative record whenever a
saved document is opened or the learner returns to configuration from results. It
validates counts, accuracy and the finite trend vocabulary before displaying them.

## Automated evidence

`python -m pytest tests -q` from `backend` passed 562 tests with one existing
host-permission symlink skip. `test_document_progress.py` covers the zero state,
two-attempt improvement, chapter/concept evidence, completion timestamps,
unfinished-attempt exclusion, authentication, owner isolation, retry attribution
copying, invented-concept rejection and legacy migration. Android JVM tests, lint and debug APK
assembly passed. Hosted quality-gate run 33888648953 passed repository hygiene,
backend, Android and locked production-container jobs for commit `1f76d59`.

## API 36 evidence

`scripts/qa-document-recovery.ps1 -ResetTestAppData -VerifyDocumentProgress`
passed on the dedicated `LearnSmart_API36` emulator against an isolated deterministic
backend after rebuilding the current APK. The disposable learner uploaded through
Android's system picker, survived process restarts, completed a ten-question quiz,
created and completed a mistake-only retry, then completed another ten-question
quiz. The runner checked three completed server attempts, dynamically reconciled
document and chapter answer counts, non-empty completion timestamps, retry provenance,
every detected chapter and grounded strong/weak concepts before matching Android to
the server response. Taller results also forced the TalkBack helper to scroll and
verify every action through fresh accessibility trees.

`artifacts/qa-document-progress.png` was visually inspected at 1080 by 2400. It
shows 3 completed quizzes, 28 answers, 17% cumulative accuracy, a 30 percentage-point
improvement, Cells at 30% from 10 answers, Plants at 11% from 18 answers, review term
Chlorophyll and strongest concept Chloroplasts. Captures remain untracked.

This proves per-document aggregate history, chapter accuracy, grounded concept
ranking and recent-attempt improvement for the tested deterministic path. It does
not establish live-provider concept quality, curriculum completion, physical-device
behavior or user acceptance.
