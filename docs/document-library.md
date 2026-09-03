# Uploaded document library

Study space now offers **My uploaded documents**, backed by the authenticated
`GET /v1/documents` endpoint. The screen has explicit empty/unavailable states and
a refresh action. Opening material re-fetches its owner-scoped summary, then
persists the same upload-stage pointer used by process recovery. It does not
re-upload the file or delete previous quizzes. The screen explicitly says that
reopening material starts a new quiz after chapter selection.

This makes server-committed uploads discoverable even without a local pointer.
It does not make upload retries idempotent: a retry after an unknown outcome can
still produce duplicate documents. There is not yet a library of prior quizzes,
document search/pagination or individual document deletion in this screen.

Backend tests verify own-document listing, other-account empty listing,
unauthenticated rejection and removal from the list after deletion. Backend
75 tests and Android build/lint/32 JVM tests passed. The JVM tests do not directly
exercise library UI or network failures.

Device verification command:
`scripts/qa-document-recovery.ps1 -ResetTestAppData -VerifyLibrary`.
It uses synthetic notes and a disposable account on LearnSmart_API36, checks the
empty library before upload, then reopens the document after clearing its local
resume pointer and confirms restart recovery, one server document and an unchanged
previous quiz. The run passed on 2026-09-03, including the existing upload,
quiz-conflict and result-recovery checks. The library screenshot at
`artifacts/qa-document-library.png` was visually inspected. The first run failed
in picker navigation; selecting the Downloads drawer entry by its resource ID
fixed the ambiguous text selector and the complete rerun passed.

Offline library failure, a second physical device, large libraries and user UAT
remain unverified. The theme QA script expects the default document recovery run
without `-VerifyLibrary`, which leaves the app at completed results.
