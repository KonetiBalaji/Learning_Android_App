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
document search/pagination. Individual deletion is described below.

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

## Confirmed document deletion

Each library item now offers a named Delete action and a confirmation describing
permanent removal of the document and its quizzes/answers. Cancel makes no API
request. Successful deletion removes the library item and clears active document
state/pointers when they identify the deleted item. Other active material and
adaptive learning state remain unchanged. A 404 is treated as already deleted;
other failures retain the item for refresh/retry. A stale quiz-only pointer whose
source is not currently loaded still resolves through the existing 404 resume
cleanup rather than guessing which unrelated quiz pointer to clear.

Backend 76 tests passed, including file removal, dependent quiz/question removal
and preservation of a second document/quiz. Android build/lint/35 JVM tests passed;
new state tests cover active deletion, unrelated deletion and repeat cleanup.
The dedicated `qa-document-deletion.ps1` uses only the disposable account and
single synthetic file left by document recovery QA. On 2026-09-03 it passed Cancel,
confirmed deletion, empty server library and process-restart checks on API 36.
`artifacts/qa-deleted-document.png` was visually inspected. The initial test
incorrectly wrapped the empty REST array and reported a count of one; direct
inspection confirmed zero documents. The count check was corrected and the full
test passed with a fresh fixture. Only disposable QA documents/quizzes were
removed; their original synthetic source remains in `scripts/fixtures`.

Subsequent backend work added durable cleanup/retry handling for filesystem-unlink
failure after database commit; see `upload-cleanup.md`. Backup retention is not defined. UI
deletion is not evidence that production backups or third-party retention have
been erased. No production data was involved in this QA.
