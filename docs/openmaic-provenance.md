# OpenMAIC selective adaptation ledger

No repository clone or upstream Git cherry-pick was performed. The original
commits `7153b3e` and `3d50b0e` were independent implementations, not imports.
The entries below identify actual source-informed adaptations made afterward.

## OA-01: Short-answer scoring and feedback

- Upstream repository: https://github.com/THU-MAIC/OpenMAIC
- Pinned revision: `132d01cd04af22b4b52cc36666a82b55f2ef224f`
- Source: https://github.com/THU-MAIC/OpenMAIC/blob/132d01cd04af22b4b52cc36666a82b55f2ef224f/app/api/quiz-grade/route.ts
- License: MIT, Copyright (c) 2026 THU-MAIC. Full notice retained in
  `third_party/OpenMAIC-LICENSE.txt`.
- Acquisition: read the single raw source file and license from the pinned
  revision; no clone, runtime dependency, or claim of a complete upstream port.
- Local implementation: `backend/app/rewrite_grading.py`, called from
  `OpenAITutorProvider.assess_rewrite` and the authenticated rewrite route.
- Adapted elements: assessor prompt, question/full-marks/grading-guidance/student
  answer inputs, integer score and brief comment result.
- Deliberate changes: Python/Pydantic and Responses Structured Outputs instead
  of Next.js and generic LLM calls; fixed server-owned 0–4 conceptual rubric;
  strict range/type/schema validation; separated untrusted learner data;
  full-credit requirement for conceptual remediation; retryable evaluator outage.
- Not adopted: regex JSON extraction, numeric/string coercion, score clamping,
  automatic half credit on malformed output, question snippets in error logs,
  client-selected model/points, or upstream Chinese-language branch.
- Local safety extension: scores below 4 use server-authored scaffolding instead
  of relaying model comments, preventing an incomplete response from receiving
  a full model-generated solution in the grading feedback.
- Verification: schema/prompt tests, evaluator-outage state preservation tests,
  mocked provider contract tests, and explicitly labelled live evaluation cases.
  These do not establish full curriculum correctness or calibrated scoring.

### Evidence (2026-09-03)

- Backend suite: 41 passing tests including strict grade validation, prompt data
  separation, no credit/mutation on evaluator outage, persisted score/comment,
  and server-owned feedback despite a deliberately leaking model comment.
- Live synthetic evaluation (`uv run python scripts/evaluate_rewrite.py --live`):
  first run passed 7/8 score expectations and exposed answer leakage. The rubric
  and feedback boundary were revised without weakening expected ranges. Second
  run passed 8/8. Model: `gpt-5-mini`; full-mark scores for two valid explanations,
  3 for concept without application, 1 for wrong-denominator/contradictory answers,
  0 for keyword list, irrelevant response and instruction injection.
- Dataset: `backend/evals/rewrite-fractions.json`. These are development regression
  cases about like fractions, not held-out evaluations or Grade 8 board coverage.
- Android: points and feedback are shown after grading and recovered from the
  persisted assessment on resume. Device checks use a visibly scripted QA
  evaluator; they do not count as live-model evaluation.
- `scripts/qa-mastery-resume.ps1 -ResetTestAppData -ExpectRubricFeedback` passed
  with exit 0. The new score/comment card was visually inspected in
  `artifacts/qa-rubric-feedback.png` after a forced process restart; question 2
  remained pending. The test completed the remaining questions before mastery.

## OA-02: Owner-scoped learning-material quotas

- Upstream repository: https://github.com/THU-MAIC/OpenMAIC
- Pinned revision: `f6cf8fd4b74ac83ea969e88b6dc2c974931b4d65`
- Sources:
  - `lib/server/agent-runtime/config.ts` (`maxMaterialsPerOwner`,
    `maxMaterialBytesPerOwner`)
  - `lib/persistence/owner-materials.ts` (`registerOwnerMaterial` quota
    read/check/insert under an owner-scoped transaction lock)
  - `app/api/materials/route.ts` (quota rejection at authenticated upload)
- License: MIT, Copyright (c) 2026 THU-MAIC. The existing full notice remains
  in `third_party/OpenMAIC-LICENSE.txt`.
- Acquisition: inspected only those files from the existing local checkout at the
  pinned commit. No cherry-pick, copy of TypeScript, runtime dependency or upstream
  database schema was introduced.
- Local implementation: `Settings` owner count/byte ceilings, `documents.stored_bytes`
  migration/backfill, and the authenticated `/v1/documents` transaction.
- Adapted elements: independently configurable maximum active document count and
  aggregate stored bytes per owner; serialized quota-read/check/insert so concurrent
  uploads cannot both consume one remaining slot; deletion releases capacity.
- Deliberate changes: SQLite `BEGIN IMMEDIATE` replaces PostgreSQL advisory locks;
  the already-validated temporary file is removed when admission loses the race;
  the existing local database/file lifecycle remains authoritative. Stable 422
  error codes select Android-owned recovery text instead of exposing quota internals
  or using upstream's generic 429 response.
- Migration: existing rows gain `stored_bytes`; startup backfills it from the saved
  file where present. A missing legacy file remains zero and is separately governed
  by existing deletion/reconciliation work rather than inventing a byte value.
- Verification: endpoint tests cover count and byte rejection, distinct owners,
  deletion/retry and temporary-file cleanup; a parallel two-request regression
  proves one-slot admission cannot overshoot; migration restores a real legacy file
  size. Android tests verify only exact known codes can show local quota guidance.

## Remaining candidates (not integrated)

OpenMAIC's teacher/classroom orchestration, whiteboard/action engine, interactive
HTML teaching scenes, course generation, and material-grounding pipeline still
need separate compatibility/security decisions. Multi-agent classroom simulation and
course publishing are not required for the learner's single-teacher Android flow;
provider voice cloning is rejected because device TTS avoids retaining biometric
voice material. Rich interactive scenes remain a candidate for TUT-05 rather than
being silently counted as integrated. OA-01 and OA-02 do not claim a complete port.
