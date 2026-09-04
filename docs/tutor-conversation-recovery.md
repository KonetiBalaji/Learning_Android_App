# Tutor conversation response-loss recovery

Status: Android API 36 QA verified for a scripted post-commit HTTP failure.

## Contract exercised

The QA-only backend middleware lets the tutor endpoint finish and persist a
reply, then substitutes one HTTP 503 response. The Android client must retain
the same pending request ID, expose **Check reply**, and recover the saved turn
without issuing a new tutor request. The QA route is owner-scoped, one-shot and
is not installed in the production application.

The device script also verifies that the conversation remains outside mastery:
the tutor state and zero score are unchanged. A separate provider failure is
shown as failed and **Use this question again** only prepares a draft; it does
not silently send another request.

## Evidence

Run on 2026-09-04 against the dedicated `LearnSmart_API36` AVD and the isolated
scripted QA server:

```powershell
.\scripts\qa-mastery-resume.ps1 -ResetTestAppData -ExpectRubricFeedback -VerifyTutorResponseLoss
```

The run passed:

- forced process restart and encrypted-session restoration;
- one persisted complete tutor turn after the substituted 503;
- recovery using the same saved request ID;
- saved conversation history and explicit provider-failure behavior;
- unchanged tutor phase and mastery score.

The recovery and failed-turn screenshots were visually inspected. Full backend
regression passed with 409 tests and one existing Windows symlink skip. Android
unit tests, lint and debug assembly also passed.

## Limits

This is an HTTP failure after the server committed, not a raw TCP disconnect or
process crash. It uses scripted tutor content, so it is not evidence of live
answer quality, speech quality, educator acceptance, UAT or production
availability.
