# Voice failure handling

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
