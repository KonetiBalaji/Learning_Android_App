# Provider outage fallback

Quiz generation distinguishes provider availability from generated-content validity. An HTTP 401/403/404, quota/rate-limit response (429), server error (5xx), or transport failure triggers local passage recall. The fallback preserves the selected source passages, requested question type and count. Its actual difficulty is **Easy**, including when the original request was Hard or Mixed, and the response is labeled `local_practice`.

Android shows the fallback notice during questions and on results. The notice persists on resume, in history results, and on mistake retry. The question screen also displays the difficulty returned for that question. The service health endpoint describes server configuration, and each quiz's mode describes how it was generated.

Malformed or incomplete model responses, refusals, invalid citations or choices, insufficient Mixed difficulty variety, and independent grounding-review rejection return generation errors. Mixed quizzes require two distinct labels for two questions and all three labels for three or more questions. When the selected material supports too few local questions, the server returns a generation error and keeps the requested count.

No live API key was used for this implementation. Backend tests use `httpx.MockTransport` and exercise simulated authentication, quota, server and network failures, plus unsafe-output rejection. Live generation quality and live difficulty remain NOT VERIFIED.

## Live difficulty review

Use held-out source passages and request Easy, Medium, Hard, and Mixed quizzes separately. Record the tested revision, model, requested count, generation mode, and accepted and rejected counts. Score the actual reasoning needed for each item before checking its label. An Easy item can be answered by direct recall from a passage. A Medium item requires applying or explaining a relationship supported by the material. A Hard item requires a defensible inference or combining more than one source-supported fact. A reviewer should also check that the marked answer is uniquely correct, the citation supports it, and the explanation adds no unsupported claim. Report accuracy by requested difficulty and, within Mixed quizzes, by item label. Track fallback separately. The automated Mixed rule checks label diversity only.

Fresh verification for this slice: **80 backend tests passed**, **2 Android unit tests passed**, **3 emulator flows passed** (zero failures/errors/skips), debug assembly passed, and lint passed. The third emulator flow requests Hard from the simulated outage fixture, verifies the actual Easy/local response and visible fallback notice, then deletes its disposable account. The other two flows cover the full learning loop and scanned-PDF review. Commands: `.venv/Scripts/python.exe -m pytest backend/tests -q` and `scripts/build-android.ps1 -ConnectedTests`.

## Reproduce the device fixture

The standard learning and OCR emulator flows use a disposable normal backend on port 18763. Run it with `STUDY_GENERATION_MODE=local_practice`, a disposable `STUDY_DATA_DIR`, the prepared local models, and `STUDY_OCR_REVIEW_THRESHOLD=1.0` so the scan-review test always requires confirmation.

The outage flow additionally needs this localhost-only fixture, which always returns a simulated provider 503 without making a network request:

```powershell
.\.venv\Scripts\python.exe scripts/start-fallback-test-backend.py --data-dir work/fallback-device-data
```

Its default port is 18764. With both fixtures available and the Android API 35 emulator running, execute `scripts/build-android.ps1 -ConnectedTests`. Each flow creates and deletes a disposable account. Never deploy the simulated-provider fixture as a real service.
