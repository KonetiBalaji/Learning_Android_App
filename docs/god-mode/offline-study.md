# Offline study implementation

## Implemented foundations

`GET /documents/{id}/offline-bundle` exports an authenticated owner's confirmed document metadata and passages, source fingerprint, schema version, download time, and absolute expiry. It excludes private OCR preview fields and rejects uncertain OCR. The expiry is the original document creation time plus 30 days; downloading again does not renew retention. Session responses include the stable owner ID, and `GET /account` resolves it for an existing session.

Android's `OfflineCache` stores bundles in Room, using Java entities/DAO and its annotation processor with Room 2.7.1 ([official release notes](https://developer.android.com/jetpack/androidx/releases/room#2.7.1)). Source text, document titles, metadata, and passages are AES-GCM ciphertext under a non-exportable Android Keystore key. SQLite indexes only opaque record/account-server hashes and expiry. Record ID, account/server scope, and expiry are authenticated additional data, so changing those fields cannot transfer a record or extend its lease. Different servers and different owner IDs have distinct scopes and encryption keys.

Cache reads purge expired records. Downloads more than five minutes in the future are rejected, and reads after a device-clock rollback beyond that tolerance require reconnection. Cache operations run off the main thread. Each bundle is limited to 12 MB, with five saved documents per account/server scope. Removal and complete cache/key clearing primitives are provided. App backup remains disabled. This does not claim instant remote revocation while a device is disconnected; online reconciliation is still required.

`OfflinePractice` generates Easy exact-passage recall on the device for multiple-choice, True/False and Yes/No. It preserves passage/section/page references, uses distinct source-derived choices, checks the requested count, and refuses insufficient material instead of inventing filler. Tests exercise multiple random seeds and all three types, including exact reconstruction of the masked source and duplicate-source handling.

## Still pending before the offline feature is complete

- Implemented: explicit download, saved-material browsing, removal confirmation, and offline entry from the library. Refreshing an unchanged download preserves its local sessions; a changed source cannot silently overwrite them.
- Implemented: stable owner identity persistence; cache clearing on logout, session rejection, account change and account deletion; cache and in-memory copy removal when online document deletion succeeds. Remote deletion reconciliation across devices is still pending below.
- Implemented: parent-chapter expansion and PDF page selection before on-device generation. Semantic topic inference is not available on the phone; the screen explicitly directs users to online tools for it.
- Implemented: encrypted local quiz/answer/advance persistence, saved-session browsing, immediate feedback, source viewing, results, mistake retry, and rotation recovery. Each session records its selection. Saved state survives repository/database reopen; an actual app process-kill/relaunch check is still pending.
- Reconcile cache revisions/deletions on reconnection and validate offline attempts on the server before importing them into authoritative progress.
- Verify an actual process restart and additional account/session-rejection cleanup cases. The integrated airplane-mode learning flow and online deletion have been exercised, but do not prove server progress import.

Offline sessions currently remain device-only and are labeled as not synced. Their scores are not added to server progress. Each downloaded copy stores up to 20 local sessions within the encrypted size limit; removal explicitly warns that unsynced answers are deleted. Server reconciliation is required before treating this as a fully completed offline feature.

The acceptance ledger therefore keeps the overall offline requirement unchecked until this integration and its device verification are complete.

## Fresh foundation verification

- Backend: **81 passed**, including the new bundle ownership, confirmed-OCR, expiry, and deletion checks (`.venv/Scripts/python.exe -m pytest backend/tests -q`).
- Android JVM: **4 passed**, comprising two existing quiz-rule tests and two new offline-generation tests.
- Device: **5 passed**, zero failures/errors/skips: three existing learning flows plus two direct cache tests. These prove cache reopen/persistence, ciphertext storage, owner/server isolation, authenticated expiry, expiry purge, clear, uncertain-source rejection, and clock-rollback rejection. They are not five full offline study flows.
- Debug assembly and lint passed with `scripts/build-android.ps1 -ConnectedTests`. The initial overlapping-source build failed because its compile snapshot preceded the newly added domain class; the fresh completed-source build above passed.

## Integrated Android verification

The subsequent integration reran the backend suite (**81 passed**), Android JVM suite (**4 passed**), debug assembly and lint, and **7 device tests** (zero failures/errors/skips). The seven comprise the three existing online learning flows, the new airplane-mode learning flow, two cache-security tests, and one local-session scope/persistence test. The completed-source final run is `work/offline-integration-final-device.log` (ignored local evidence); the repeatable command is `scripts/build-android.ps1 -ConnectedTests` with the documented local fixtures.

The airplane-mode flow downloads confirmed material, disables connectivity, creates a one-question quiz, submits an incorrect answer, opens the saved citation, rotates the activity, views results, and retries mistakes. It restores connectivity in a finally block, deletes the online document, verifies its cache and in-memory copy are gone, and deletes the disposable account. The focused service test verifies parent-chapter expansion and PDF page boundaries, refusal to advance without an answer, idempotent same-answer retry, conflicting-answer rejection, persisted session reopening, and source-preserving mistake retry. These tests do not imply completed server synchronization or a verified process-kill/relaunch flow.
