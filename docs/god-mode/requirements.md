# God Mode acceptance ledger

The full objective is the user's attached “Take the Saras learning app to God Mode” specification. This ledger preserves its scope; an unchecked item is not complete merely because adjacent tests pass.

## Reconcile and publish source

- [x] Preserve the working Windows implementation on a backup branch.
- [x] Create and push the exact requested `god-mode` branch.
- [x] Rerun the reported Windows backend, Android JVM, build, lint, and emulator checks.
- [x] Inspect the substantial remote implementation and document incompatible contracts.
- [ ] Locate and reconcile the separately reported 51-test unittest core; its source location/revision is missing.
- [x] Complete a green, reproducible audit of adopted remote components; full rerun 726 passed/1 host-limited skip, with a separate real memory-limit probe for the reused guard.
- [ ] Keep final committed history clean and confirm remote HEAD matches the final tested revision.

## Learning functionality

- [x] Upload → structure → select → quiz → feedback → results → mistake retry → progress, with source references and owner checks.
- [x] Flashcards and SM-2: backend and Android flows verified; evidence in `reconciliation.md`.
- [x] OCR for scanned PDFs with visible confidence, needs-review state, and original-page comparison.
- [x] Semantic retrieval, including a real local-model evaluation rather than renamed keyword search.
- [ ] Offline encrypted document cache plus quizzes generated locally on Android.
- [x] Adaptive next quiz integrated with recent, distinct learning evidence; live AI difficulty still pending.
- [ ] Tutor chat from the selected document's retrieved passages, with citations and a tested no-support response.
- [ ] Complete navigation between all learning tools with no dead ends.
- [ ] Owner-only access, retention, document deletion, and account deletion cover every new record type and local cache.

## Live AI

- [ ] Securely configure an authorized server-only key and selectable model. User previously deferred the key.
- [ ] Rerun real generation and grounding/answer/explanation validation on the sample document.
- [ ] Record real Easy, Medium, Hard, and Mixed difficulty samples and accuracy counts.
- [ ] Demonstrate local fallback when the provider is unavailable.
- [ ] Never record credentials, document content, or private keys in Git/APK/logs/chat.

## Branding, operations, and release

- [x] Identify the Saras Modern/Heritage assets from the user-supplied email; preserve a clearly named placeholder until real files are available.
- [ ] Import supplied assets into light/dark header, launcher, and splash surfaces after re-supply/access.
- [ ] Docker and HTTPS configuration, encrypted-at-rest production storage, rate limits, safe structured logging, health/readiness, and background retention cleanup.
- [ ] Run staging smoke checks against the actual staged deployment.
- [ ] Release signing configuration with no keystore/password in Git; create a genuinely signed release only with authorized signing material.
- [ ] Play Store title, short/full descriptions, screenshots checklist, privacy-policy draft, data-safety draft, versioning, and release notes.
- [ ] Publish only after Balaji's explicit action-specific go-ahead. No publishing is currently authorized.

## Demo and final audit

- [ ] Three-minute Sivaraj demo script.
- [ ] Seeded sample document and source-validated frozen sample quiz.
- [ ] One-page status sheet separating VERIFIED IN REPO from REPORTED ON WINDOWS ONLY / reported elsewhere.
- [ ] Test report with actual current counts; live AI or release gaps clearly say NOT VERIFIED.
- [ ] Exact external blocker list: API setup, real logo assets, hosting/TLS, signing material, and Play Console access if publishing.
- [ ] Requirement-by-requirement completion audit of the final current state, not merely this checklist.

The active goal remains incomplete until the full requested state is implemented and verified, or specific external dependencies prevent further progress after all independent work has been done.
