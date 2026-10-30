# Offline study implementation

## Implemented foundations

`GET /documents/{id}/offline-bundle` exports an authenticated owner's confirmed document metadata and passages, source fingerprint, schema version, download time, and absolute expiry. It excludes private OCR preview fields and rejects uncertain OCR. The expiry is the original document creation time plus 30 days; downloading again does not renew retention. Session responses include the stable owner ID, and `GET /account` resolves it for an existing session.

Android's `OfflineCache` stores bundles in Room, using Java entities/DAO and its annotation processor with Room 2.7.1 ([official release notes](https://developer.android.com/jetpack/androidx/releases/room#2.7.1)). Source text, document titles, metadata, and passages are AES-GCM ciphertext under a non-exportable Android Keystore key. SQLite indexes only opaque record/account-server hashes and expiry. Record ID, account/server scope, and expiry are authenticated additional data, so changing those fields cannot transfer a record or extend its lease. Different servers and different owner IDs have distinct scopes and encryption keys.

Cache reads purge expired records. Downloads more than five minutes in the future are rejected, and reads after a device-clock rollback beyond that tolerance require reconnection. Cache operations run off the main thread. Each bundle is limited to 12 MB, with five saved documents per account/server scope. Removal and complete cache/key clearing primitives are provided. App backup remains disabled. This does not claim instant remote revocation while a device is disconnected; online reconciliation is still required.

`OfflinePractice` generates Easy exact-passage recall on the device for multiple-choice, True/False and Yes/No. It preserves passage/section/page references, uses distinct source-derived choices, checks the requested count, and refuses insufficient material instead of inventing filler. Tests exercise multiple random seeds and all three types, including exact reconstruction of the masked source and duplicate-source handling.

## Still pending before the offline feature is complete

- Wire explicit download, saved-material browsing, removal, and offline entry into Android navigation.
- Integrate owner identity persistence and clear the cache on logout, session rejection, account change and account deletion; remove a saved document when its online deletion succeeds.
- Apply chapter/page selection to the saved passage set before local generation. Semantic topic inference is not available on the phone unless separately implemented; do not silently rename keyword filtering as semantic search.
- Save and resume local quiz state across rotation and process recreation, show feedback/source/results/mistakes, and clearly distinguish unsynced device progress.
- Reconcile cache revisions/deletions on reconnection and validate offline attempts on the server before importing them into authoritative progress.
- Run a real airplane-mode learning flow, process restart, reconnection and deletion flow. Foundation tests alone do not prove a usable offline product.

The acceptance ledger therefore keeps the overall offline requirement unchecked until this integration and its device verification are complete.

## Fresh foundation verification

- Backend: **81 passed**, including the new bundle ownership, confirmed-OCR, expiry, and deletion checks (`.venv/Scripts/python.exe -m pytest backend/tests -q`).
- Android JVM: **4 passed**, comprising two existing quiz-rule tests and two new offline-generation tests.
- Device: **5 passed**, zero failures/errors/skips: three existing learning flows plus two direct cache tests. These prove cache reopen/persistence, ciphertext storage, owner/server isolation, authenticated expiry, expiry purge, clear, uncertain-source rejection, and clock-rollback rejection. They are not five full offline study flows.
- Debug assembly and lint passed with `scripts/build-android.ps1 -ConnectedTests`. The initial overlapping-source build failed because its compile snapshot preceded the newly added domain class; the fresh completed-source build above passed.
