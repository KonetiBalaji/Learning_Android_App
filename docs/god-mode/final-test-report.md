# Saras dev verification report

## Current promoted checkpoint

Revision `fa5110aaf7c9ddb01dfee9bd7acbc9b724d5084c` passed 166 backend tests, 4 Android unit tests, and 15 Android 15 emulator tests before promotion to `main`. The separate process-stop rehearsal passed one preparation test and one resume test. The API contract check, debug and instrumentation APK builds, lint, and Docker HTTPS staging passed. [Hosted verification](https://github.com/KonetiBalaji/Learning_Android_App/actions/runs/42225180316) · [Docker HTTPS staging](https://github.com/KonetiBalaji/Learning_Android_App/actions/runs/42225180312)

- The starter catalog contains 23 lessons across Grades 1–12, including 12 in Grade 6. New attempts have at least two diagnostic questions. All lessons offer three worked steps, at least five authored practice prompts, and a guiding question for an incomplete rewrite.
- Backend coverage verifies the ordered steps and bank structure across the catalog, original question counts on existing attempts, and retry cycling in the slope lesson. Android coverage verifies starter diagnostic navigation across all grades, the full Grade 6 Science path, and themed examples in fractions and percentages.
- Staging verified private readiness resume, scoring, identical answer retries, linked parent aggregates, and revocation over trusted HTTPS. Android tests verify resume from grade selection and report removal when the viewer returns after revocation. The backend regression verifies that account deletion invalidates the old session and removes the unfinished assessment while preserving another student's attempt.
- Staging replaced the API container after question one and resumed the assessment at question two while preserving documents, quizzes, and existing sessions. It then restored a consistent SQLite snapshot into a fresh Docker volume using the original mounted key. Integrity and foreign-key checks passed. Existing sessions, the owner's document and quiz, and the completed readiness result were usable in the restore. The second account was denied access to the owner's document.
- The restored database rejected a wrong key and permitted a fresh sign-in with the original key mounted. Backend tests using simulated provider responses verified the Mixed difficulty label rule. The Android outage regression confirmed that a Hard request displayed the returned Easy label alongside the fallback notice. Live question difficulty and accuracy remain unverified.

## Release checks with separate evidence

On `8b31a1e`, the Android release bundle rebuilt with a disposable two-day certificate. `bundletool validate` passed, `jarsigner -verify` reported a verified signature, and the manifest identified package `com.studycompanion` with target API 36 and no debug flag. The verifier warned about the self-signed certificate, missing timestamp, and differences between JAR file and stream verification. The disposable keystore was removed after the check. Authorized Play signing remains unverified.

The disposable backup rehearsal was verified at `48b67d8`. [Hosted verification](https://github.com/KonetiBalaji/Learning_Android_App/actions/runs/42175587701) · [Docker HTTPS staging](https://github.com/KonetiBalaji/Learning_Android_App/actions/runs/42175587753)

- The disposable backup rehearsal checked SQLite integrity and foreign keys, original-key recovery, email sign-in, document access by its owner, denial to another account, and startup rejection with a different key. Production recovery still requires the intended host and backup procedure.
- The Android APK declares the microphone optional and offers typed input when dictation is unavailable. Separate Android 15 emulator tests verified the typing fallback after denying microphone access and clearing pending dictation controls on background. The recognizer did not reach the listening state in the cancellation rehearsal. The physical Android 13 phone accepted the QA app but canceled the instrumentation APK installation with `INSTALL_FAILED_USER_RESTRICTED`. Audible narration, active recording cancellation, and microphone transcription on a physical phone remain unverified.
- Google web account deletion passed a headless-browser rehearsal with a simulated Google callback. Live Google verification on the authorized public origin remains open.

## Earlier runtime and release bundle checkpoint

Commit `5ba44181d85dd3eea35fa52b7583daac2109393d` passed the following checks on `dev` before `main` was fast-forwarded to the same revision.

| Check | Observed result |
|---|---|
| Backend pytest | 154 passed, one Starlette/httpx deprecation warning |
| Android unit tests | 4 passed, zero failures or errors |
| Android 15 emulator | 15 passed |
| Android build and lint | Debug and instrumentation APKs built. Lint reported zero errors and 15 warnings. |
| Docker HTTPS staging | Passed, including document study, curriculum coaching and owner-only chapter unlock, password-based account deletion, and Google deletion page wiring with a synthetic client ID. |
| Android release bundle | `bundleRelease` succeeded, `bundletool validate` passed, and `jarsigner` reported a verified signature from a short-lived, self-signed test certificate. The manifest identifies `com.studycompanion`, target API 36, with no debug flag. The verifier reported self-signed trust, missing timestamp, and differences between JAR file and stream verification. |

[Hosted verification on dev](https://github.com/KonetiBalaji/Learning_Android_App/actions/runs/42170621266) · [Docker HTTPS staging on dev](https://github.com/KonetiBalaji/Learning_Android_App/actions/runs/42170621255)

The Grade 6 checks validate answer-key indexes, independently recalculate all 89 math practice answers, and compare normalized prompt text across lesson and readiness banks. These checks cover the authored catalog and scoring. Validation against actual exam outcomes remains open.

The [release blocker list](external-blockers.md) tracks live AI, approved branding, public hosting, Google OAuth and account deletion on the public origin, authorized Play signing, and publication. The [curriculum matrix](../product/curriculum-verification.md) tracks remaining product and device verification, including physical voice testing.

## Hosted verification of the curriculum and tutor changes

Runtime revision `8f6620f` passed [backend and Android verification](https://github.com/KonetiBalaji/Learning_Android_App/actions/runs/42166542893) and [Docker HTTPS staging](https://github.com/KonetiBalaji/Learning_Android_App/actions/runs/42166542958).

| Check | Observed result |
|---|---|
| Backend pytest | 138 passed, one Starlette/httpx deprecation warning |
| Android unit tests | 4 passed, no failures or errors |
| Android 15 emulator | 15 passed, including Grade 6 subject progression and document tutor |
| APK assembly and lint | Debug and instrumentation APKs built. Lint reported zero errors and 15 warnings. |
| Docker HTTPS staging | Trusted test TLS, readiness, OCR, semantic retrieval, owner isolation and web account deletion passed. |

The emulator used disposable accounts and synthetic study material. The [curriculum verification matrix](../product/curriculum-verification.md) describes the narrower evidence for diagnostic coaching, mastery, readiness, invitation-based reports, and the tutor avatar. The [private Google sign-in device check](../api/google-sign-in.md#live-device-verification) used one approved test account. Public OAuth, Play-signed Google sign-in, Google-capable web account deletion, and physical narration or dictation remain unverified.

The earlier `484fe6c` [hosted run](https://github.com/KonetiBalaji/Learning_Android_App/actions/runs/42166176737) timed out during Android test registration. The successful `8f6620f` run did not reproduce the failure. Revision `9d2bebe` adds registration error reporting and disposable backend request logs to aid diagnosis. The updated [hosted suite on `9d2bebe`](https://github.com/KonetiBalaji/Learning_Android_App/actions/runs/42167310988) passed 139 backend tests and 15 emulator tests. [Docker HTTPS staging](https://github.com/KonetiBalaji/Learning_Android_App/actions/runs/42167310948) also passed on that revision. The earlier timeout was not reproduced, and its cause remains unconfirmed.

## Original God Mode closeout


Runtime revision: `ad03dda15c3fdc3bd426491c4416a7b75b30651f` (base `0181f83`). The audit pack follows in a documentation-only commit. The app targets API 36; the connected device runs Android 15 (API 35).

| Check | Actual result | Evidence |
|---|---|---|
| Backend pytest | 102 passed; one Starlette/httpx deprecation warning | `.venv\Scripts\python.exe -m pytest backend/tests -q`; includes owner and lifecycle cases |
| Android JVM | 4 passed; 0 failed or skipped | Gradle XML: OfflinePracticeTest and QuizRulesTest |
| Android emulator | 9 passed; 0 failed or skipped | Connected suite on SarasTest, Android 15; six learning flow tests and three cache tests. Regression checks cover upload retry after a failed library refresh, automatic dismissal of an expired offline result and source dialog, and immediate quiz resume from Library. Existing checks cover OCR citation return, account deletion, airplane mode, sync and remote deletion. |
| Android debug build | Passed | Debug APK and instrumentation APK assembled |
| Android debug lint | Passed; 0 errors, 14 warnings | lint-results-debug.txt |
| Docker HTTPS staging | Passed on disposable Linux Compose | [GitHub Actions run 42026775931](https://github.com/KonetiBalaji/Learning_Android_App/actions/runs/42026775931): redirect, trusted TLS, readiness, upload, real OCR and confirmation, semantic retrieval, owner isolation, quiz and web account deletion |
| Separately reported Python unittest core | REPORTED ONLY: 51 | No attributable revision or test files; excluded from the totals. See [reconciliation](reconciliation.md). |

Android command: `scripts/build-android.ps1 -ConnectedTests`. The build finished successfully. The emulator uses disposable backend fixtures; the Docker smoke independently verifies a Linux deployment.

**NOT VERIFIED:** live AI and grounding, real difficulty accuracy, original logo integration, public production TLS and smoke, authorized Play signing, final store declarations and publishing. Prior disposable signing and offline process restart evidence is historical, as recorded in the release and offline guides. See [external blockers](external-blockers.md).

## Public release verification

| Gate | Status | Evidence still needed |
|---|---|---|
| Approved branding | NOT VERIFIED | Approved assets and inspection of launcher, splash and headers in light and dark modes |
| Live AI | NOT VERIFIED | No live evaluation run. Easy, Medium, Hard and Mixed each have zero evaluated items. Accuracy is unavailable. |
| Public production | NOT VERIFIED | Production URL, trusted public certificate and completed smoke results from the supplied host |
| Authorized Play bundle | NOT VERIFIED | Bundle signed with the authorized upload key, matching certificate fingerprint and final privacy and Data safety declarations |

## Physical phone and account isolation

On November 5, 2026, nine instrumentation tests passed on a physical Android 13 (API 33) phone using the debug build and disposable local backend over ADB reverse forwarding. The two-account scenario verified registration, sign-in for each account, wrong-password rejection, sign-out, server-side token revocation, deletion of saved copies on sign-out, rejection of cross-owner document access, and restoration of the original account's library on sign-in. Disposable accounts were removed.

The phone also passed the document-to-results flow with retrieval, tutor, citations, adaptive practice, flashcards and progress, plus OCR correction, provider fallback, upload retry, offline expiry and cache tests. The airplane-mode scenario is reserved for the emulator because the phone's wireless debugging transport depends on Wi-Fi.

To repeat the phone run, install the debug and instrumentation APKs on a disposable test installation, forward ports 18763 and 18764 with ADB reverse, and run AndroidJUnitRunner with `-e studyHost 127.0.0.1`. The normal fixture uses local practice, and the second fixture simulates a provider outage. Public production and live AI were outside this device run.

This audit reran 102 backend tests and four Android unit tests successfully. Debug assembly and lint passed with zero errors and 14 warnings. The separate airplane-mode rerun stalled on the emulator and was stopped. The earlier passing emulator run for the same application code remains recorded above.
