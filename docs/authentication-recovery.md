# Authentication failure and recovery

Authenticated HTTP 401 responses invalidate the in-memory session, clear both
encrypted and legacy token preferences, reset visible learner state and route to
sign-in. Account-scoped mastery resume pointers are retained for reauthentication;
server progress is not deleted by session expiry. Login's own 401 is treated as
incorrect credentials, not another session-expiry transition. No-content requests
(including account deletion) use the same failure policy as JSON and upload calls.

HTTP failures use client-owned messages, never raw server response bodies. This
avoids displaying input values echoed by validation errors and tolerates HTML or
empty proxy errors. Offline failures have a connection/retry message. Redirects
are disabled on authenticated connections. Response streams/connections are
closed on success and failure; coroutine cancellation is propagated.

Only one ViewModel operation runs at a time. This limits overlapping UI requests
but is **not** server-side exactly-once processing or safe automatic retry of
mutations whose response was lost. That work remains in ASM-01.

## Evidence (2026-09-03)

- Backend `uv run pytest -q`: **42 passed**. New expiry regression checks read,
  practice and deletion rejection; fresh login recovers the identical tutor
  state and can continue practice. Existing deletion tests cover other-owner
  preservation and invalidation of deleted-account credentials.
- Android `:app:assembleDebug :app:testDebugUnitTest :app:lintDebug` passed,
  **14 JVM tests** total. Six HTTP failure tests cover authenticated versus login
  401, response closure, secret-bearing 422 bodies, HTML/empty errors, 204/redirect
  handling and network exceptions. They do not instantiate the ViewModel.
- Repeatable device scenario: `scripts/qa-mastery-resume.ps1 -ResetTestAppData
  -ExpectRubricFeedback -VerifyDeletedSession`. Restricted to the named QA emulator
  and deterministic/scripted localhost backend. It creates a synthetic account,
  verifies the learning flow, deletes only that run's account through the API,
  requests progress from the still-signed-in app, verifies sign-in routing and
  token removal across restart, and verifies the invalid-login message.
  This scenario completed with exit 0 on `LearnSmart_API36`: all learning-flow,
  encrypted-storage and deleted-session assertions passed. Only its disposable
  synthetic account and associated learning data were deleted; no user account
  was used. Deleted synthetic data is not recoverable through the app.

Still needed: timed token expiry and reauthentication on-device, saved-session
recovery across account switches, token-store failure injection, and network-loss
mutation reconciliation. This is QA, not user UAT acceptance or production proof.
