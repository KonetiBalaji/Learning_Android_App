# God Mode acceptance ledger

The full objective is the user's attached “Take the Saras learning app to God Mode” specification. This ledger preserves its scope; an unchecked item is not complete merely because adjacent tests pass.

## Reconcile and publish source

- [x] Preserve the working Windows implementation on a backup branch.
- [x] Consolidate feature work on `dev` and promote the verified revision to default branch `main`. Preserve superseded histories under `archive/*` tags and retire their branches.
- [x] Rerun the reported Windows backend, Android JVM, build, lint, and emulator checks.
- [x] Inspect the substantial remote implementation and document incompatible contracts.
- [x] Record a separate archive disposition for the 51-test claim in [reconciliation](reconciliation.md). The source and revision remain reported only.
- [x] Complete a green, reproducible audit of adopted remote components; full rerun 726 passed/1 host-limited skip, with a separate real memory-limit probe for the reused guard.
- [x] Publish the tested runtime revision to dev and keep main unchanged for this closeout. The following audit commit changes documentation only; see the [test report](final-test-report.md).

## Learning functionality

- [x] Upload → structure → select → quiz → feedback → results → mistake retry → progress, with source references and owner checks.
- [x] Flashcards and SM-2: backend and Android flows verified; evidence in `reconciliation.md`.
- [x] OCR for scanned PDFs with visible confidence, needs-review state, and original-page comparison.
- [x] Semantic retrieval, including a real local-model evaluation rather than renamed keyword search.
- [x] Encrypted offline cache, local quizzes, validated progress import and revision/deletion reconciliation. Verified airplane mode, sync replay, and recovery after an actual process stop in `offline-study.md`.
- [x] Adaptive next quiz integrated with recent, distinct learning evidence; live AI difficulty still pending.
- [x] Tutor chat from the selected document's retrieved passages, with citations and a tested no-support response. Local source excerpt mode and Android citation flow verified; live AI explanations remain pending below.
- [x] Connect all learning tools with return paths, refresh-only retry after successful upload, and immediate access to unfinished quizzes. See the [navigation audit](final-audit.md) and connected test results.
- [x] Cover owner access, retention, document deletion and account deletion for linked records and local cache, including expiry while an offline result and its citation are open. See the [lifecycle audit](final-audit.md).

## Live AI

- [ ] Securely configure an authorized server-only key and selectable model. User previously deferred the key.
- [ ] Rerun real generation and grounding/answer/explanation validation on the sample document.
- [ ] Record real Easy, Medium, Hard, and Mixed difficulty samples and accuracy counts.
- [x] Demonstrate local fallback when the provider is unavailable: simulated HTTP/network outages and a real emulator flow, with explicit Easy/local labeling. See `provider-fallback.md`; live AI quality remains unverified.
- [x] Verify the scoped closeout secret handling: no matching key material or tracked credential artifacts in the audited tree, no new runtime credentials, and staging request logs use route templates. Keep the same rule for future deployment inputs.

## Branding, operations, and release

- [x] Identify the Saras Modern/Heritage assets from the user-supplied email; preserve a clearly named placeholder until real files are available.
- [ ] Import supplied assets into light/dark header, launcher, and splash surfaces after re-supply/access.
- [x] Docker and HTTPS configuration, mounted storage key validation, per-client rate limiting, safe request logs, readiness and background retention cleanup.
- [x] Verify trusted TLS, readiness, actual OCR and semantic retrieval, owner isolation and web account deletion on a disposable Linux Compose stack. [Staging run](https://github.com/KonetiBalaji/Learning_Android_App/actions/runs/42026775931)
- [ ] Provision the persistent production host, public DNS and certificate. Rerun smoke checks against that host.
- [x] Configure Android API 36 and environment-based release signing.
- [ ] Build the distribution bundle with the authorized Play upload key and verify its certificate.
- [x] Prepare Play Store listing, screenshot checklist, privacy and Data safety drafts, release notes and versioning instructions. Final declarations require actual production details.
- [ ] Publish only after Balaji's explicit action-specific go-ahead. No publishing is currently authorized.

## Demo and final audit

- [x] Three-minute Sivaraj demo script.
- [x] Seeded sample document and source-validated frozen sample quiz.
- [x] [One-page status sheet](sivaraj-status.txt) separating VERIFIED IN REPO from REPORTED ONLY.
- [x] [Test report](final-test-report.md) with current counts and explicit NOT VERIFIED release gates.
- [x] [Exact external blocker list](external-blockers.md): AI, branding, production, Play signing and publishing approval.
- [x] [Requirement-by-requirement audit](final-audit.md) of dev.

Unchecked release gates remain pending. Their inputs and follow-up checks are in the [external blocker list](external-blockers.md).

Public release preparation tracks each missing input and its acceptance evidence in the [release handoff](external-blockers.md#public-release-handoff). The disposable staging stack and disposable signing certificate do not satisfy the public production or Play signing gates.
