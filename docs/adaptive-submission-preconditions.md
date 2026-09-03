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

Limitations: this is conditional mutation, not idempotent response replay. Legacy
requests without a token remain accepted and lack delayed-retry protection.
Mandatory enforcement needs a coordinated client/QA-script migration. A real
Android lost-response/stale-screen test and account-switch test remain pending.
No physical-device, UAT or production completion is claimed. No live AI calls
or credential changes were made in this slice.
