# Offline study implementation

## Implemented foundations

`GET /documents/{id}/offline-bundle` exports an authenticated owner's confirmed document metadata and passages, source fingerprint, schema version, download time, and absolute expiry. It excludes private OCR preview fields and rejects uncertain OCR. The expiry is the original document creation time plus 30 days; downloading again does not renew retention. Session responses include the stable owner ID, and `GET /account` resolves it for an existing session.

Android's `OfflineCache` stores bundles in Room, using Java entities/DAO and its annotation processor with Room 2.7.1 ([official release notes](https://developer.android.com/jetpack/androidx/releases/room#2.7.1)). Source text, document titles, metadata, and passages are AES-GCM ciphertext under a non-exportable Android Keystore key. SQLite indexes only opaque record/account-server hashes and expiry. Record ID, account/server scope, and expiry are authenticated additional data, so changing those fields cannot transfer a record or extend its lease. Different servers and different owner IDs have distinct scopes and encryption keys.

Cache reads purge expired records. Downloads more than five minutes in the future are rejected, and reads after a device-clock rollback beyond that tolerance require reconnection. Cache operations run off the main thread. Each bundle is limited to 12 MB, with five saved documents per account/server scope. Removal and complete cache/key clearing primitives are provided. App backup remains disabled. This does not claim instant remote revocation while a device is disconnected; online reconciliation is still required.

`OfflinePractice` generates Easy exact-passage recall on the device for multiple-choice, True/False and Yes/No. It preserves passage/section/page references, uses distinct source-derived choices, checks the requested count, and refuses insufficient material instead of inventing filler. Tests exercise multiple random seeds and all three types, including exact reconstruction of the masked source and duplicate-source handling.

## Integration and remaining verification

- Implemented: explicit download, saved-material browsing, removal confirmation, and offline entry from the library. Refreshing an unchanged download preserves its local sessions; a changed source cannot silently overwrite them.
- Implemented: stable owner identity persistence; cache clearing on logout, session rejection, account change and account deletion; cache and in-memory copy removal when online document deletion succeeds. Successful online refresh also reconciles remote deletion and source changes.
- Implemented: parent-chapter expansion and PDF page selection before on-device generation. Semantic topic inference is not available on the phone; the screen explicitly directs users to online tools for it.
- Implemented: encrypted local quiz/answer/advance persistence, saved-session browsing, immediate feedback, source viewing, results, mistake retry, and rotation recovery. Each session records its selection. Saved state survives repository/database reopen; an actual app process-kill/relaunch check is still pending.
- Implemented: explicit sync of completed sessions, validated server progress import, per-session acknowledgement persistence, idempotent retry and remote revision/deletion reconciliation. Verification details follow below.
- The two-phase `scripts/verify-offline-restart.ps1` run passed. The harness verified the original process was absent, reopened encrypted state while offline, resumed the saved answer, and synchronized the completed result after reconnecting.

Offline sessions remain device-only until the user selects **Sync completed offline sessions** while connected. Incomplete sessions are skipped. Successful imports receive a server quiz ID, are labeled as synced, and can open the account result for further online study tools. Each downloaded copy stores up to 20 local sessions within the encrypted size limit; removal explicitly warns that unsynced answers are deleted.

The synchronization revision passed all seven device tests. The airplane-mode flow exercised repeated sync without duplicate progress and removal of the cached copy after another client deleted the document.

## Synchronization boundary

`POST /documents/{id}/offline-attempts` accepts a stable local session ID, source fingerprint, section/page selection, question type/prompt/choices/source ID and selected answer. It does **not** accept a device answer key, explanation, accuracy score or completion timestamp. The server retrieves the selected source, reconstructs the exact recall question, validates source-derived distractors or the single-word binary alteration, derives correctness and builds teaching feedback. Duplicate passages, invalid choices, unsupported wording, changed sources and ownership violations are rejected. Accepted results enter the existing quiz/progress/mistake/flashcard/adaptive pipeline as Easy local practice.

The import ID and payload digest make retries idempotent; changing an already imported session's answers is a conflict. The completed quiz and document source lock commit in one SQLite transaction, so a partial write cannot leave a quiz citing an editable source. The same transaction helper now protects online quiz creation. Sync requests are bounded to 16 MB, 50 questions, 50,000 characters per prompt and 200 characters per choice. Offline completion time is not independently verifiable; account history records server synchronization time and says so explicitly.

`GET /documents/{id}/offline-status` exposes only an owned source fingerprint, processing state and expiry. Successful online refresh removes cached documents absent from the owned library. A changed or uncertain source marks its cached copy stale: history remains reviewable, but generation, answering, advancement, retries and import are blocked until the old copy is explicitly removed and current material saved. No deleted/changed data is resurrected by an import. These checks occur on reconnect/refresh or explicit sync; disconnected devices cannot receive immediate revocation.

## Fresh foundation verification

- Backend: **81 passed**, including the new bundle ownership, confirmed-OCR, expiry, and deletion checks (`.venv/Scripts/python.exe -m pytest backend/tests -q`).
- Android JVM: **4 passed**, comprising two existing quiz-rule tests and two new offline-generation tests.
- Device: **5 passed**, zero failures/errors/skips: three existing learning flows plus two direct cache tests. These prove cache reopen/persistence, ciphertext storage, owner/server isolation, authenticated expiry, expiry purge, clear, uncertain-source rejection, and clock-rollback rejection. They are not five full offline study flows.
- Debug assembly and lint passed with `scripts/build-android.ps1 -ConnectedTests`. The initial overlapping-source build failed because its compile snapshot preceded the newly added domain class; the fresh completed-source build above passed.

## Integrated Android verification

The subsequent integration reran the backend suite (**81 passed**), Android JVM suite (**4 passed**), debug assembly and lint, and **7 device tests** (zero failures/errors/skips). The seven comprise the three existing online learning flows, the new airplane-mode learning flow, two cache-security tests, and one local-session scope/persistence test. The completed-source final run is `work/offline-integration-final-device.log` (ignored local evidence); the repeatable command is `scripts/build-android.ps1 -ConnectedTests` with the documented local fixtures.

The airplane-mode flow downloads confirmed material, disables connectivity, creates a one-question quiz, submits an incorrect answer, opens the saved citation, rotates the activity, views results, and retries mistakes. It restores connectivity in a finally block, deletes the online document, verifies its cache and in-memory copy are gone, and deletes the disposable account. The focused service test verifies parent-chapter expansion and PDF page boundaries, refusal to advance without an answer, idempotent same-answer retry, conflicting-answer rejection, persisted session reopening, and source-preserving mistake retry. These tests do not imply completed server synchronization or a verified process-kill/relaunch flow.
