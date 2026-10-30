# Provider outage fallback

Quiz generation distinguishes provider availability from generated-content validity. An HTTP 401/403/404, quota/rate-limit response (429), server error (5xx), or transport failure triggers local passage recall. The fallback preserves the selected source passages, requested question type and count. Its actual difficulty is **Easy**, including when the original request was Hard or Mixed, and the response is labeled `local_practice`.

Android shows the fallback notice during questions and on results. The notice persists on resume, in history results, and on mistake retry. The service health endpoint still describes server configuration; each quiz's mode describes what actually generated that quiz.

Malformed/incomplete model responses, refusals, invalid source references, invalid choices, and independent grounding-review rejection remain generation failures. They do **not** trigger fallback. If selected material cannot support the requested local count, the existing clear generation error is returned rather than inventing filler or silently reducing the count.

No live API key was used for this implementation. Backend tests use `httpx.MockTransport` and exercise simulated authentication, quota, server and network failures, plus unsafe-output rejection. Live generation quality and live difficulty remain NOT VERIFIED.

Fresh verification for this slice: **80 backend tests passed**, **2 Android unit tests passed**, **3 emulator flows passed** (zero failures/errors/skips), debug assembly passed, and lint passed. The third emulator flow requests Hard from the simulated outage fixture, verifies the actual Easy/local response and visible fallback notice, then deletes its disposable account. The other two flows cover the full learning loop and scanned-PDF review. Commands: `.venv/Scripts/python.exe -m pytest backend/tests -q` and `scripts/build-android.ps1 -ConnectedTests`.

## Reproduce the device fixture

The standard learning and OCR emulator flows use a disposable normal backend on port 18763. Run it with `STUDY_GENERATION_MODE=local_practice`, a disposable `STUDY_DATA_DIR`, the prepared local models, and `STUDY_OCR_REVIEW_THRESHOLD=1.0` so the scan-review test always requires confirmation.

The outage flow additionally needs this localhost-only fixture, which always returns a simulated provider 503 without making a network request:

```powershell
.\.venv\Scripts\python.exe scripts/start-fallback-test-backend.py --data-dir work/fallback-device-data
```

Its default port is 18764. With both fixtures available and the Android API 35 emulator running, execute `scripts/build-android.ps1 -ConnectedTests`. Each flow creates and deletes a disposable account. Never deploy the simulated-provider fixture as a real service.
