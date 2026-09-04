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

## Account-switch and timed-expiry device evidence (2026-09-04)

`scripts/qa-account-switch.ps1 -ResetTestAppData` passed on LearnSmart_API36
against an isolated deterministic backend. Android created two synthetic accounts,
saved Sports for Account A and Music for Account B, signed out/in, and restarted.
Account A restored exactly one selection (Sports) while Music remained unselected;
direct owner-authenticated profiles independently matched both values. The inspected
account-switch screenshot contains no email or credential. Both successful accounts
and one leftover account from a failed harness attempt were deleted.

`LEARNING_TOKEN_MINUTES=1` plus `scripts/qa-session-expiry.ps1
-ResetTestAppData` then exercised an actual server-issued expiry. Before expiry the
device preference held one encrypted session envelope and no plaintext assertion was
printed. After 65 seconds, Android's real progress request received 401, showed the
safe expired-session message, removed encrypted and legacy credentials, and stayed
signed out after force-stop/restart. Password reauthentication succeeded so the
disposable account could be deleted. This was not a fabricated error response.

Token lifetime is now configurable from 1 minute through 30 days and rejects values
outside that range. Still needed: AndroidKeyStore/provider failure injection and
physical-device/user UAT. Network-loss mutation reconciliation belongs to ASM-01,
not basic authentication acceptance. This is QA, not UAT or production proof.
