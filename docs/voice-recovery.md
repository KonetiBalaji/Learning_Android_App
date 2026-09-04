# Voice failure handling

## Accessible animated teacher QA

On 2026-09-04 every app screen gained a persistent teacher status bar, including
a signed-out explanation before account creation. Its visible and accessibility
states are derived from actual request and TTS lifecycle state: ready, thinking
and speaking. Tutor lesson and conversation screens also show a larger native
vector teacher; the lesson avatar is adjacent to the read-aloud controls so the
learner can see its mouth movement while listening. It does not claim phoneme-level
lip synchronization. The TTS pace is set to 0.8 for a clearer teaching cadence
and readiness now also requires the device engine to accept that rate.

`scripts/qa-mastery-resume.ps1 -ResetTestAppData -ExpectRubricFeedback
-VerifyReadAloud` passed on the dedicated API 36 AVD. It verified the persistent
bar while signed out and across grade, subject, diagnostic and tutor navigation,
then ready/speaking rendering, real TTS callbacks, background cancellation, no
automatic resume, explicit restart/stop and completion. Speaking and ready frames
were visually inspected, including correction of an initial status-bar overlap.
Android unit tests, lint and debug assembly passed; 124 JVM tests include
ready/speaking/thinking state precedence and the bounded speech rate.

This is a state-driven animation and device callback check, not acoustic quality,
TalkBack-navigation, phoneme lip-sync, microphone recognition, UAT or production
evidence. TUT-05 and TUT-06 remain partial across broader lessons and devices.

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

API 36 follow-up ran the real recognition activity from a tutor-question draft and
cancelled it with Android Back. The exact typed question remained and the cancellation
message rendered. The harness then temporarily disabled only the emulator speech
package, verified the explicit unavailable-service fallback and unchanged draft,
restored the package in a `finally` block, confirmed that no question was sent, and
deleted the disposable account. The inspected
`artifacts/qa-voice-input-recovery.png` is untracked QA evidence. This proves cancel
and missing-activity recovery, not successful microphone recognition or transcript
quality.

Read-aloud is disabled until engine initialization and English language availability
are confirmed. It displays failure messages, offers Stop, and splits long text into
engine-sized chunks without breaking surrogate pairs. Navigating away stops and
releases the engine. The manifest declares TTS service visibility.

The current Android gate passes **134 JVM tests**, lint and debug assembly. Policy tests
cover cancellation/empty results, trimming/length bounds and Unicode-safe chunks.
Successful microphone recognition and transcript quality, acoustic quality, TalkBack
navigation and physical-device/user acceptance remain open. Read-aloud playback,
stop, completion and background lifecycle plus lesson-scoped conversational teaching
have separate API 36 evidence in this record and the tutor-conversation contract.

Official references: [TTS initialization and lifecycle](https://developer.android.com/reference/android/speech/tts/TextToSpeech)
and [recognition activity availability](https://developer.android.com/reference/android/speech/RecognizerIntent).
