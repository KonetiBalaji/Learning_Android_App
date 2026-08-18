# Development Instructions

## Current scope

This repository is being built in stages. Keep the MVP focused on the core learning loop described in `Initial_plan.md`:

**Upload → Analyze → Select → Quiz → Instant Feedback → Results → Improve**

Do not add implementation, dependencies, or infrastructure as part of documentation-only changes.

## Repository conventions

- Keep Android code under `android/` and backend code under `backend/`.
- Put cross-service request/response contracts under `shared/contracts/`.
- Put durable architectural and product decisions under `docs/`.
- Keep feature code cohesive; avoid placing business rules directly in Compose screens or HTTP handlers.
- Use clear names that describe behavior rather than implementation details.

## Android guidelines

- Use Kotlin, Jetpack Compose, Material 3, and coroutines/Flow.
- Separate UI state, domain use cases, repositories, and data sources.
- Keep navigation and screen state lifecycle-aware.
- Make loading, empty, validation, failure, and retry states explicit.
- Add accessibility semantics and support content that can scale with font size.
- Keep document and quiz state resilient to rotation and process recreation.

## Backend and AI guidelines

- Keep provider/API credentials on the server and out of source control.
- Authenticate every document and progress request; enforce owner-level authorization.
- Validate file type, size, corruption, password protection, and extraction failures at the upload boundary.
- Retrieve only content relevant to the selected chapter, section, page range, or topic.
- Require structured quiz output and validate it before returning it to the client.
- Reject questions with missing answers, invalid choices, duplicate choices, ambiguous correctness, weak grounding, or contradictory explanations.
- Preserve source references for questions and explanations whenever available.
- Treat unsupported claims as generation failures or requests for clarification, not as facts.

## Privacy and security

- Never commit secrets, tokens, private keys, user documents, or local credential files.
- Encrypt network traffic and protect stored documents.
- Restrict document access to its owner.
- Provide document deletion and account/data deletion paths as the product develops.
- Define retention behavior before enabling production uploads.

## Testing expectations

Every implementation slice should include the smallest useful automated tests. Prioritize:

- document validation and extraction failure cases;
- chapter/section detection confidence handling;
- selection-to-retrieval boundaries;
- structured AI response validation;
- one-question-at-a-time quiz state transitions;
- immediate correct/incorrect feedback;
- result calculations and mistake review;
- authorization and document ownership.

Also verify loading, empty, offline, retry, and partial-failure states in the Android UI.

## Git workflow

- Use a focused feature branch such as `agent/<short-description>`.
- Make small commits with imperative, meaningful messages.
- Keep unrelated changes out of a commit.
- Review `git diff` and `git status` before committing.
- Do not commit generated build output or secrets.
- Push only the intended branch and confirm its upstream remote.

## Definition of done for a feature

A feature is complete when its behavior, failure states, security boundary, tests, documentation, and integration path are clear. Passing tests alone is not sufficient if the user flow or source grounding is unverified.

