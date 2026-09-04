# Tappable question source evidence

## Contract

After a document question has been answered, the learner can open its displayed
source reference from immediate feedback or any completed mistake record. Android
requests `GET /v1/quizzes/{quiz_id}/questions/{question_id}/source` and displays the
exact extracted characters in a scrollable dialog. The dialog identifies the
absolute source range and states that the passage is extracted rather than
AI-generated.

The backend joins question, quiz and document ownership. A missing or other-owner
question returns 404. An unanswered question returns 409 so source evidence cannot
reveal the answer before submission. Only the server-created
`(source characters START-END)` reference format is accepted, and invalid, stale or
out-of-bounds historical references fail closed with 409. The response repeats quiz
and question identity, range and reference; Android validates all of them, including
exact text length and the range embedded in the reference, before rendering.

Deterministic generation now records the exact original sentence offsets rather
than the whole chapter. Provider generation continues to record its independently
reviewed supporting quote range. No provider call, state mutation or answer grading
occurs when evidence is opened.

## Verification

- Backend tests cover the unanswered gate, owner isolation, exact extracted slice,
  response identity/range, explanation correspondence, and malformed historical
  references.
- Android JVM tests reject mismatched identity, range, text length and reference.
- Android JVM tests, lint and debug assembly pass.
- `scripts/qa-document-recovery.ps1 -ResetTestAppData -VerifyResultActions` passed
  on the dedicated API 36 emulator. After a conflicting answer was recovered and
  the app was force-stopped, the restored feedback opened the original answered
  question's exact source, not the next unanswered question. The dialog text and
  character range were reconciled with the authenticated endpoint. The screenshot
  is `artifacts/qa-question-source.png`. The same journey completed results,
  TalkBack result-action exposure, mistake-only retry, configure-another and
  difficulty-increase checks.

This is emulator QA for extracted text. Original PDF-page rendering, physical-device
accessibility and user acceptance remain separate release gates.
