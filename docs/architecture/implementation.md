# Saras implementation

Saras implements the core study loop on Android with a local Python backend. The initial repository contained documentation and empty directories. This implementation uses a single Android application module, with separate repository, domain rules, ViewModel state, and Compose rendering. Backend modules separate extraction, retrieval, quiz rules, optional AI generation, encrypted persistence, response contracts, and HTTP ownership checks.

## Data flow

1. Create an account or sign in. Passwords use salted scrypt; opaque bearer tokens are stored as hashes on the server and expire after 30 days. The Android token is encrypted with an Android Keystore key and excluded from backups.
2. Stream a PDF, DOCX, or UTF-8 TXT upload. Reject files above 50 MB, corrupted or encrypted files, empty text, excessive DOCX expansion, and image-only PDFs. Bound extraction to 2 million characters and 2,000 PDF pages. Original upload files are discarded after parsing.
3. Detect chapters, numbered sections, uppercase headings, Markdown headings, and DOCX heading styles. Preserve parent chapter relationships and page references. Join wrapped text lines within a page. Detection is heuristic; uncertain structure is explicitly shown. DOCX and TXT do not claim physical pagination.
4. Apply section, page, and topic filters together. Selecting a chapter includes its child sections. Topic search is lexical across text and headings; it does not perform semantic/embedding search. Only selected passages can reach generation.
5. Generate and validate questions. Local mode creates exact-passage recall questions, explicitly labeled Easy. It rejects insufficient material instead of filling the requested count with fabricated questions. The three formats are multiple choice, exact-passage True/False, and exact-passage Yes/No.
6. Return only the current question. Correct answers, source quotes, and teaching explanations stay server-side until an answer is submitted. Submit and advance use idempotent retry semantics. A submitted answer cannot be changed.
7. Persist every answer, current position, and feedback. Android retains state across rotation, and a relaunched app resumes its active quiz from the server. Interrupted quizzes are also listed in the library.
8. Calculate results, review mistakes, retry only incorrect questions, and aggregate chapter accuracy and chronological session history. A retry is a separate session and contributes to progress when completed.

## Optional AI adapter

Default configuration is `STUDY_GENERATION_MODE=local_practice`. No AI key is required and no requests reach a provider in this mode.

The optional `openai` mode requires both a server-side key and explicitly configured model. It uses the [Responses API structured output format](https://developers.openai.com/api/docs/guides/structured-outputs), strict schemas, `store=false`, a 24,000-character selected-source context budget, exact-quote/source validation, choice validation, and a separate model review. Refused, incomplete, malformed, ambiguous, or unsupported output fails clearly; it is not silently replaced with local questions. Source content is treated as untrusted data in both prompts. A model review reduces errors but cannot guarantee educational accuracy. Live provider generation and account/model access still need verification after the user supplies a key. No live provider calls were made during implementation.

The Android client reads server mode and enables Easy/Medium/Hard/Mixed options when AI mode is configured. In AI mode it tells students that selected passages are sent to the provider. Secrets remain on the backend. A provider failure does not expose upstream response bodies or credentials.

## Privacy and operational boundary

All document text, metadata, question data, and answers are Fernet-encrypted in SQLite. The local `storage.key` must be kept private with the database; losing it makes stored records unreadable. This is local development storage, not a managed production key vault. Usernames and password hashes remain normal authentication records. Uploaded originals are not retained.

Documents expire 30 days after upload. Expired documents and associated quizzes are purged on the owner's next authenticated request; an inactive account is not proactively purged by a background job. Document deletion removes its related quizzes. Account deletion cascades through documents, sessions, and progress. Logical SQLite deletion does not guarantee forensic erasure from disk or backups.

Run the supplied server bound to `127.0.0.1`. Android release networking requires HTTPS. Debug HTTP is permitted only for localhost, 127.0.0.1, and the Android emulator host 10.0.2.2. Before exposing uploads publicly, add managed TLS, durable secret/key management, shared rate limits, storage quotas, parser isolation/timeouts, background retention cleanup, backups and deletion policy, and production authentication recovery. The current rate limiter and SQLite lock support one local server process.

## Branding source

The user supplied the Gmail thread titled **Saras Logos**, dated September 7, 2026. It identifies the brand as **Saras** and includes Heritage and Modern PNG logos plus `Saras_Logo_Heritage.svg` and `Saras_Logo_Modern.svg`. The app now uses the Saras name. Browser attachment retrieval failed and automation later stopped because it could not verify the current URL. Neither supplied logo has been imported. The book launcher symbol is temporary; it is not represented as either supplied logo. Import the Modern asset when available, and preserve the Heritage variant as an alternative.
