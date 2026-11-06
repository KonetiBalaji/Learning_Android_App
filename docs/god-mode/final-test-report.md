# Saras dev verification report

## Promoted runtime checkpoint

Revision `d3d6fb036666d1dda57d3060febc766734c051e9` passed Backend and Android verification and Docker HTTPS staging on dev before promotion, and both checks passed independently on main. The main run recorded 166 backend tests, four Android unit tests, 15 emulator tests, and the two single-test restart phases. [Main verification](https://github.com/KonetiBalaji/Learning_Android_App/actions/runs/42260630918) · [Main staging](https://github.com/KonetiBalaji/Learning_Android_App/actions/runs/42260631133)

Revision `c00776ba41a301589114a5355cb627864cbdd7df` passed 166 backend tests, 4 Android unit tests, and 15 Android 15 emulator tests on dev before promotion to main. The separate process-stop rehearsal passed one preparation test and one resume test. The API contract check, debug and instrumentation APK builds, lint, and Docker HTTPS staging passed. [Hosted verification](https://github.com/KonetiBalaji/Learning_Android_App/actions/runs/42229528612) · [Docker HTTPS staging](https://github.com/KonetiBalaji/Learning_Android_App/actions/runs/42229528565)

- Docker staging verified the Google deletion page and rejected cross-origin submissions, missing confirmation, and missing credentials. The live Google browser callback and deletion on the authorized public HTTPS origin remain unverified.
- The Android 13 phone signed out and signed back in to the private deployment using one approved Google test account. The Library reopened. This check used the installed debug APK and an ADB-forwarded local backend.

- The starter catalog contains 23 lessons across Grades 1–12, including 12 in Grade 6. New attempts have at least two diagnostic questions. All lessons offer three worked steps, at least five authored practice prompts, and a guiding question for an incomplete rewrite.
- Backend coverage verifies the ordered steps and bank structure across the catalog, original question counts on existing attempts, and retry cycling in the slope lesson. Android coverage verifies starter diagnostic navigation across all grades, the full Grade 6 Science path, and themed examples in fractions and percentages.
- Staging verified private readiness resume, scoring, identical answer retries, linked parent aggregates, and revocation over trusted HTTPS. Android tests verify resume from grade selection and report removal when the viewer returns after revocation. The backend regression verifies that account deletion invalidates the old session and removes the unfinished assessment while preserving another student's attempt.
- Staging replaced the API container after question one and resumed the assessment at question two while preserving documents, quizzes, and existing sessions. It then restored a consistent SQLite snapshot into a fresh Docker volume using the original mounted key. Integrity and foreign-key checks passed. Existing sessions, the owner's document and quiz, and the completed readiness result were usable in the restore. The second account was denied access to the owner's document.
- The restored database rejected a wrong key and permitted a fresh sign-in with the original key mounted. Backend tests using simulated provider responses verified the Mixed difficulty label rule. The Android outage regression confirmed that a Hard request displayed the returned Easy label alongside the fallback notice. Live question difficulty and accuracy remain unverified.

## Release checks with separate evidence

On `8b31a1e`, the Android release bundle rebuilt with a disposable two-day certificate. `bundletool validate` passed, `jarsigner -verify` reported a verified signature, and the manifest identified package `com.studycompanion` with target API 36 and no debug flag. The verifier warned about the self-signed certificate, missing timestamp, and differences between JAR file and stream verification. The disposable keystore was removed after the check. Authorized Play signing remains unverified.

The disposable backup rehearsal was verified at `48b67d8`. [Hosted verification](https://github.com/KonetiBalaji/Learning_Android_App/actions/runs/42175587701) · [Docker HTTPS staging](https://github.com/KonetiBalaji/Learning_Android_App/actions/runs/42175587753)

- The disposable backup rehearsal checked SQLite integrity and foreign keys, original-key recovery, email sign-in, document access by its owner, denial to another account, and startup rejection with a different key. Production recovery still requires the intended host and backup procedure.
- The Android APK declares the microphone optional and offers typed input when dictation is unavailable. Separate Android 15 emulator tests verified the typing fallback after denying microphone access and clearing pending dictation controls on background. The recognizer did not reach the listening state in the cancellation rehearsal. After clearing the phone's USB installation restriction, the QA instrumentation APK installed and the Android 13 fractions test passed with `verifyDictationBackground=true` against a fresh local backend. It exercised the read-aloud control, cleared pending dictation on background, and completed mastery by typing. The phone logged that its recognizer could not connect to the speech service. That run did not verify cancellation during active recording or successful microphone transcription.
- In a later Android 13 rerun, the Google text-to-speech engine started a speech audio track. Android routed it to the built-in speaker and logged that it stopped about 12 seconds later. In a separate manual check, the tester confirmed that the Adding fractions explanation was clearly audible through the phone speaker. The same rerun failed the pending-dictation assertion after the recognizer reported that it could not connect. The earlier pending-dictation pass was not reproduced.
- Android 13 recognizer logs showed that its offline engine rejected generic `en`. After the app requested `en-US`, the same engine reported that the supported pack was missing. The updated QA app displayed the missing-model message and completed the fractions lesson by typing. That run did not reach active dictation.
- The Android 13 phone already had the offline `en-IN` pack. With the app using the device's regional English locale, the fractions test passed with `verifyDictationBackground=true` and `requireActiveDictation=true`. It reached Listening before backgrounding, then cleared the dictation controls. Device logs showed the `en-IN` model loading, microphone capture starting, and the recognizer stopping detection. That run did not check transcription.
- A separate Android 13 instrumentation run with `verifySpokenDictation=true` played a short synthetic English phrase through the phone speaker, used the physical microphone and offline recognizer, and matched the expected words in the editable response field before submission. The full fractions test passed. An earlier attempt with a longer sentence returned a transcript that did not match the full sentence. This verifies the device-to-app transcription path with one controlled sample.
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

The [release blocker list](external-blockers.md) tracks live AI, approved branding, public hosting, Google OAuth and account deletion on the public origin, authorized Play signing, and publication. The [curriculum matrix](../product/curriculum-verification.md) tracks product coverage and records the scope of physical voice verification.

## Hosted verification of the curriculum and tutor changes

Runtime revision `8f6620f` passed [backend and Android verification](https://github.com/KonetiBalaji/Learning_Android_App/actions/runs/42166542893) and [Docker HTTPS staging](https://github.com/KonetiBalaji/Learning_Android_App/actions/runs/42166542958).

| Check | Observed result |
|---|---|
| Backend pytest | 138 passed, one Starlette/httpx deprecation warning |
| Android unit tests | 4 passed, no failures or errors |
| Android 15 emulator | 15 passed, including Grade 6 subject progression and document tutor |
| APK assembly and lint | Debug and instrumentation APKs built. Lint reported zero errors and 15 warnings. |
| Docker HTTPS staging | Trusted test TLS, readiness, OCR, semantic retrieval, owner isolation and web account deletion passed. |

The emulator used disposable accounts and synthetic study material. The [curriculum verification matrix](../product/curriculum-verification.md) describes the narrower evidence for diagnostic coaching, mastery, readiness, invitation-based reports, and the tutor avatar. The [private Google sign-in device check](../api/google-sign-in.md#live-device-verification) used one approved test account. Public OAuth, Play-signed Google sign-in, Google-capable web account deletion remain unverified.

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
