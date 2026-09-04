# Adaptive submission preconditions

The previous transaction lock rejected overlapping computations but could not
identify a delayed duplicate arriving after commit. Adaptive responses now carry
a session-scoped token derived from status, question index, correct-answer count
and coaching rounds. All current transitions change at least one of those fields.
No schema migration or secret is required; the token is not an authorization key.

The backend checks the supplied expected state after ownership validation and
before provider calls, then retains its existing atomic snapshot check at commit.
Tokens in mutation responses describe that mutation's resulting state, without a
racy post-commit reread. See `shared/contracts/adaptive-mastery.md` for protocol.

Android retains tokens per session in its API layer. All three adaptive POST
paths insert the expected token. Failed network/HTTP requests retain the old
token; successful start, resume and mutation responses update it. Missing state
prevents submission. Sign-out clears tokens, and a process restart must start or
resume before submitting. Existing 409 handling resumes without resubmitting.

Verification on 2026-09-03: 92 backend tests passed. Android debug build, lint
and 40 JVM tests passed.
Two new JVM tests cover cache retention, replacement, session separation and
clearing. Backend delayed-retry tests use repeated valid answer options so option
validation cannot conceal answering the wrong question. They verify no second
attempt or state change for stale diagnostic, practice and rewrite requests,
and no provider call on rejection. Fresh repeated practice remains permitted.
Additional tests cover session-scoped tokens and malformed values. Existing
three concurrent-submission tests now send preconditions as well.

Follow-up implementation now persists the successful result for each session,
operation and pre-transition token in the same transaction as the attempt. An
identical delayed retry receives that exact result with no second attempt or
provider call; different content under the consumed token receives 409. Concurrent
identical submissions both receive the winning response and commit once, although
provider computations can overlap before the transaction winner is known.

Legacy requests without a token remain accepted and lack delayed-retry protection.
Mandatory enforcement needs a coordinated client/QA-script migration. A real
Android TCP-response-loss test remains pending.
No physical-device, UAT or production completion is claimed. No live AI calls
or credential changes were made in this slice.

## Android stale-screen verification

On 2026-09-03, ran:

```powershell
.\scripts\qa-mastery-resume.ps1 -ResetTestAppData -ExpectRubricFeedback -VerifyWeeklyReport -VerifyStaleSubmission
```

Passed on the dedicated LearnSmart_API36 emulator with the updated debug APK
and refreshed localhost scripted QA backend. Only disposable test-app data was
reset; the test created a new synthetic account. Scripted grading is not evidence
of live AI quality.

The app submitted the initial wrong answer, restored its tutor after force stop,
completed practice and rewrite, and restored question 2 with rubric feedback.
The script then answered question 2 through a second authenticated API client,
using the current state token, while Android still displayed question 2.
Android's stale submission produced an actual HTTP 409 in the server log,
followed by its automatic GET resume. The app showed question 3 without an error
dialog or an additional attempt; the server token remained equal to the second
client's resulting token. Another force stop restored question 3 correctly.

The screenshot `artifacts/qa-mastery-stale.png` was inspected: question 3, its
four choices and the saved rubric feedback were readable; no option was selected.
The script then completed question 3 and verified 100% chapter progress.
The weekly API report contained exactly five learning responses and one unique
mastered chapter, with the uncalibrated-readiness disclosure visible in Android.

This proves the tested diagnostic stale-screen/409 recovery path, not dropped
response bytes, repeated practice/rewrite recovery on device, account switching,
or legacy-client protection. Those cases remain distinct QA work.

## Post-commit failed-response verification

On 2026-09-03, the same dedicated emulator passed:

```powershell
.\scripts\qa-mastery-resume.ps1 -ResetTestAppData -ExpectRubricFeedback -VerifyWeeklyReport -VerifyFailedResponse
```

The explicit localhost QA runner installs `scripts/qa_response_fault.py`; the
production application does not install its route or middleware. The fault's
authenticated arm route verifies session ownership and is limited to 100 pending
paths. It substitutes a single 503 for a successful diagnostic answer response
after the endpoint has committed. It does not simulate a TCP disconnect, timeout
or partial JSON payload. No live AI calls were made.

Android submitted question 2, displayed its safe service-unavailable message and
canonical Support ID, and retained the old question and answer. A separate GET
confirmed that question 3 was already pending on the server. After dismissing the
error and resubmitting, the 2026-09-04 rerun received the saved 200 outcome
directly. The server token did not change during that replay, and a process restart
retained question 3. The run then completed
mastery and verified exactly five weekly learning responses and one mastered
chapter, demonstrating no duplicate response credit in this scenario.

Focused idempotency, transition and concurrency tests passed 14/14, including all
three adaptive operations, different-content conflicts, owner scope and cascade
cleanup. Earlier tests also prove the fault acts after success, fires once, rejects
another session and is not installed in the production app. Android code was
unchanged from the current 135-test/lint/build verification.
TCP loss, malformed successful responses, practice/rewrite failure injection,
physical-device coverage and user acceptance remain unverified.

## Decoding before acknowledging a response

The API layer previously remembered a token immediately after parsing the JSON
envelope, before reading required result fields. A valid new token with missing
answer fields could therefore leave the old question on screen but acknowledge
the newer server state. Adaptive start/resume/answer/practice/rewrite now accept
their token only after constructing their decoded result. A thrown decoding
error retains the previous token (or no token for a failed first response).

On 2026-09-03, Android build/lint and 42 JVM tests passed, including two new
decoding-failure tests. The QA fault regression test also passed after adding
the `malformed` mode. The production server does not install this fault.

The API 36 emulator passed the previous failed-response command with additional
`-MalformedResponse`. The server committed question 2 but returned HTTP 200 with
only the new `state_token`, deliberately omitting the result fields. Android
displayed its generic safe error, retained question 2 and retried with the old
token. Server logs confirmed 409 followed by GET resume. Question 3 remained
unchanged across retry and restart; completing it produced exactly five learning
responses and one mastered chapter in the weekly report.

This verifies the tested missing-required-field decode failure, not every
semantically inconsistent payload. Unknown actions and inconsistent optional
fields require further validation. No AI requests, physical-device validation,
user acceptance or production deployment were performed.
