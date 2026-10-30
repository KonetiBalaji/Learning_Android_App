# Document tutor integration

The document selection screen opens a tutor for the chosen chapters and PDF pages. A topic belongs in the question, not a hidden keyword filter. Each turn records its selection and cites exact source passage IDs, section IDs, page numbers where available, and quote offsets.

With no configured AI provider, the screen explicitly uses **source excerpt mode**. It quotes a related passage without claiming to synthesize an explanation. Below the semantic retrieval threshold, it responds: “I don't have support for that in the selected material.” Retrieval similarity is not proof that a passage entails an answer.

When a server AI provider is enabled, the existing strict draft and independent grounding review must both pass before generated prose is returned. Invalid citations, unsupported claims rejected by review, or provider failures discard the generated prose and show a labeled original-source excerpt. Live provider accuracy remains NOT VERIFIED until an authorized key is supplied and live samples are evaluated.

## API and storage

- `POST /documents/{id}/tutor`: question (2–1000 characters), selection, and stable request ID. Successful replies include the answer, mode, citations, notice, question, selection, and turn ID.
- `GET /documents/{id}/tutor`: up to 100 saved turns, oldest first, restricted to the current source fingerprint.
- All access requires the document owner. Turns are Fernet encrypted and linked to their document, so document deletion, account deletion, and document retention remove them alongside other records.
- A repeated request returns the same saved result. Reusing its ID for different input is a conflict. Android's retry action retains the original ID after a connection failure.
- Source fingerprints are checked around retrieval and again after generation. Corrections invalidate old dialogue and reject stale replay or an in-flight answer. Old turns are retained encrypted until document deletion/retention, but are excluded from current history and AI context.
- Only the latest six turns with the same source fingerprint and exact selection are eligible as contextual dialogue. Earlier dialogue is explicitly not evidence.
- There is a bounded 100-turn lifetime limit per document. Reaching it returns an explicit error; other study tools remain available. Separate conversation management is not implemented.

## Verification scope

Backend integration tests cover owner isolation, selection boundaries, explicit no-support replies, encrypted persistence, retry idempotency/conflicts, source correction during inference, stale saved replies, uncertain OCR gating, history invalidation, and deletion. Seven existing helper tests separately cover strict citations, independent review, provider failure, and no-hit behavior.

The Android integration test exercises the actual local semantic model, asks a biology question, verifies source excerpt mode, opens its source citation, and returns to the quiz flow. Fresh verification for this integration: **73 backend tests passed** (`.venv/Scripts/python.exe -m pytest backend/tests -q`), **2 Android JVM tests passed**, **2 emulator flows passed** (zero failures/errors/skips), and debug assembly plus lint passed (`scripts/build-android.ps1 -ConnectedTests`). The emulator flows cover the complete learning loop with tutor/search/adaptive/flashcards and scanned-PDF review. No live AI result is implied by these local tests.
