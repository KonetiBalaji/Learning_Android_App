# Saras dev closeout audit

This audit applies to the Saras application with Android ID `com.studycompanion` and the existing document API. The tested code revision is `ad03dda15c3fdc3bd426491c4416a7b75b30651f`. The base was `0181f83`. For later curriculum, Google sign-in and Android coaching work, see the [curriculum verification matrix](../product/curriculum-verification.md) and the newer hosted checkpoint in the test report. See the [test report](final-test-report.md) for execution results and the [acceptance ledger](requirements.md) for individual statuses.

| In-scope requirement | Evidence and boundary |
|---|---|
| 1. Reconcile the 51-test core | [Reconciliation](reconciliation.md) records the decision to archive the claim separately. Exact source and revision remain reported only. The different app ID and API of the archived MVP were kept separate. |
| 2. Connect the learning tools | Library opens upload, saved documents and quiz resume. Document configuration opens practice, OCR, search, tutor and offline download. Quiz completion opens results, which lead to mistakes, retry, adaptive practice and card creation. Review exposes due and all cards. Progress reopens past results. Offline has a saved-material list, session selection, local results and validated account results after sync. Android Back returns to the relevant study screen, and the original scan viewer keeps its own document and return context. After a successful upload, a failed library refresh can be retried without another upload request. Newly started quizzes appear in Continue studying immediately. The Android report identifies exercised paths. |
| 3. Protect all record types and caches | `test_record_lifecycle.py` creates the document, embedding, tutor, quiz (including validated offline import), and flashcard rows through API calls, rejects cross-owner access and verifies document delete, retention and account delete. Existing card-review tests cover the mutation boundary. OCR text and images live in the encrypted document row. Answers, progress and sync receipts derive from or live in quiz records. Android cache tests cover owner/server scope, expiry, ciphertext and stale-source checks. Device flow tests cover reconciliation after remote deletion and removal of a saved copy after account deletion. Offline expiry is enforced when opening, listing or using a saved session. An open offline result and its source dialog close at expiry. Server deletion is learned on reconnect, refresh or an authenticated 401. |
| 4. Update the ledger with evidence | [Acceptance ledger](requirements.md) tracks the audit and separates external verification from implementation. |
| 5. Report current tests | [Final test report](final-test-report.md) records actual counts, revisions and exclusions. |
| 6. Provide a one-page status sheet | [Sivaraj status](sivaraj-status.txt) separates verified repository evidence from the reported-only core. |
| 7. Identify exact external inputs | [External blockers](external-blockers.md) lists provider setup, approved assets, deployment inputs, Play release inputs and publication approval. |
| 8. Audit the current dev revision | This table maps all eight requirements to implementation and verification evidence. The report records the exact runtime revision separately from documentation updates. |

The closeout includes Android navigation and refresh cleanup, backend lifecycle coverage, and regressions for upload retry, offline expiry and quiz resume. The existing ingestion, OCR, model retrieval, scoring, scheduling, offline sync protocol and Docker stack are retained. CI exercises real OCR and semantic retrieval using public models and synthetic samples. Base signing with a disposable certificate is historical evidence. Live AI, original branding, a production endpoint and Play distribution await the external inputs above.

| Product and release requirement | Closeout verdict |
|---|---|
| Upload and document structure | Verified for PDF, DOCX and TXT; chapter/page selection is retained. Backend and Android learning flow evidence is in the test report. |
| OCR and correction | Verified with a real scanned sample in staging and a correction flow on Android. Confidence and review behavior are recorded in [OCR evidence](ocr-search-adaptive.md). |
| Semantic search | Verified with a local embedding model and held-out samples; staging rechecks retrieval. |
| Quiz, feedback and progress | Verified with source citations, result reopening, mistake retry and adaptive practice. Live difficulty accuracy remains unverified. |
| Flashcards and spaced repetition | Verified for creation from results, due/all views, review, owner checks and duplicate protection. |
| Document tutor | Verified in local excerpt mode with cited passages and an explicit no-support response; live explanations remain unverified. |
| Offline study | Verified for cache encryption, scope, local quizzes, expiry, sync and remote deletion. Prior process-stop evidence is recorded in [offline study](offline-study.md). |
| Deployment controls | Verified on disposable staging for Docker, trusted test TLS, readiness and deletion. Mounted keys, rate limits, log format and retention have repository evidence. Production remains unverified. |
| Android and demo | API 36 target and debug APK verified; prior disposable signing and the [Sivaraj demo](sivaraj-demo.md) are documented. |
| Branding and Play | Placeholder and [draft materials](play-store-draft.md) are in the repository. Original assets, authorized signing, final declarations and publishing remain unverified. |
