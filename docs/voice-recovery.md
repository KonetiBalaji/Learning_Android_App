# Voice failure handling

## API 36 playback lifecycle QA

Command: `scripts/qa-mastery-resume.ps1 -ResetTestAppData -VerifyReadAloud`.
Tested the debug APK from `c1c600b` on the dedicated LearnSmart_API36 emulator,
using its installed Google TTS service and a synthetic Grade 8 Fractions account
against the isolated scripted-qa backend. No OpenAI request was made. Only this
dedicated emulator app's local test data was reset; server account data was not
deleted. The script installs the built APK and validates the AVD/backend first.

Passed: engine readiness, playback status, Home/background then same-activity
return, stopped state with disabled Stop, no automatic resume, explicit restart,
explicit Stop, another restart and real speech-service completion callback.
The setup also verified tutor restoration after process restart and encrypted
session storage. Transient null-root UI dumps were retried with fresh hierarchies.

Captured and visually inspected `artifacts/qa-read-aloud-background.png` and
`artifacts/qa-read-aloud-complete.png`: controls and stopped/finished messages are
readable without clipping at the tested size. Screenshots remain generated local
QA artifacts, not source files. The read-aloud mode exits after these focused
checks and does not claim to run the rest of the mastery suite.

This proves UI/lifecycle behavior and speech-service callbacks, not acoustic
silence, pronunciation, volume, speaker output or listening quality. Audible
verification, longer multi-chunk speech, engine-error injection, lesson replacement,
navigation during playback, TalkBack and broader devices remain open. It is not
UAT acceptance or the separate conversational/animated teacher implementation.

## Playback lifecycle repair

Read-aloud now stops on lifecycle ON_STOP (including backgrounding), lesson-text
replacement, navigation/disposal and explicit Stop. It does not automatically
resume on foregrounding. Stop is enabled only while audio is queued; reading,
finished, stopped and failed statuses are announced through a polite accessibility
live region. Engine disposal still stops and releases the speech service.

Each queued playback uses unique generation/chunk IDs. Completion waits for all
chunks; duplicate callbacks and callbacks from stopped or replaced playback cannot
finish or fail the current playback. An asynchronous error clears the remaining
queue and stops the engine. A failed synchronous queue operation does the same.
The main-thread `SpeechPlayback` policy is independent of Android engine details.

Verification: `:app:assembleDebug :app:testDebugUnitTest :app:lintDebug` passed,
with 115 JVM tests. Four new policy tests cover multi-chunk completion, duplicate
callbacks, stop/restart identity, errors and invalid empty playback. These do not
prove audible output or actual lifecycle event delivery. Device checks still
needed: start long speech, background and verify silence, foreground without auto
resume, restart speech, replace the lesson, navigate away, inject engine failure,
and verify TalkBack/status announcements. No real audio claim is made here.

Voice input now checks the activity result before accepting recognized text.
Cancellation, empty results, missing recognition activities and service permission
failures preserve the typed answer and offer an explicit typed-input fallback.
Accepted text is bounded and the learner is prompted to review it before submission.
The UI discloses that the device speech service may process audio online.

Read-aloud is disabled until engine initialization and English language availability
are confirmed. It displays failure messages, offers Stop, and splits long text into
engine-sized chunks without breaking surrogate pairs. Navigating away stops and
releases the engine. The manifest declares TTS service visibility.

Android build/lint and **22 JVM tests passed** on 2026-09-03. Three new policy tests
cover cancellation/empty results, trimming/length bounds and Unicode-safe chunks.
These are not speech-engine, microphone or acoustic-quality tests. Hardware/service
availability, real recognition, playback, stop/navigation, background lifecycle,
accessibility and animation remain to be verified. This does not implement the
separate free-form conversational teacher requirement.

Official references: [TTS initialization and lifecycle](https://developer.android.com/reference/android/speech/tts/TextToSpeech)
and [recognition activity availability](https://developer.android.com/reference/android/speech/RecognizerIntent).
