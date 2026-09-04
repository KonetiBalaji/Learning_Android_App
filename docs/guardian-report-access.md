# Consent-based guardian report access

## Access model

Every authenticated account remains an independent account and may act as a learner,
a guardian, or both. A learner explicitly creates a 15-minute, single-use sharing
code and passes it directly to the intended parent or teacher. The recipient must
sign in to a separate account and redeem that code. Creating a new code invalidates
the learner's earlier unredeemed code.

Redemption creates a directional guardian-to-learner link. It grants only these
read-only aggregate endpoints for the selected grade:

- progress dashboard;
- seven-day report.

The link does not authorize mastery-session reads or writes, tutor conversations,
diagnostic/practice/rewrite submissions, interests, uploaded documents, quizzes,
answers, account changes, or sharing on the learner's behalf. Those existing routes
continue to scope ownership to the caller. An unauthorized learner report returns a
concealed 404 rather than revealing whether the learner account exists.

Both parties can remove the relationship. The learner sees each account that can
view their report and can revoke it; the guardian can remove a linked learner.
Revocation is server-side and takes effect on the next request. Deleting either
account cascades the link and outstanding learner invitations.

The learner-owned `GET /v1/guardian/access-history` endpoint records each access
grant and whether the learner or guardian revoked it. Grant/revocation records are
committed atomically with link changes and remain after ordinary unlinking. If a
guardian deletes their account, deletion first records a guardian revocation and
then removes the deleted account identifier and email from prior events. Deleting
the learner cascades their history. Guardians cannot use this endpoint to inspect
a learner's history, including for a currently linked learner.

The learner-owned `GET /v1/guardian/access-history/export` endpoint downloads the
same ordered audit history as UTF-8 CSV. It sends `Cache-Control: no-store`, omits
event, learner, and guardian database identifiers, represents a deleted guardian
as `Deleted account`, and neutralizes spreadsheet-formula prefixes. The export
contains only the timestamp, fixed event type, and guardian account label. A
guardian calling it receives that account's own empty learner-side history, never
a linked learner's record.

## Code handling and retention

Codes contain 128 bits of randomness and use 32 lowercase hexadecimal characters
so they can be typed reliably on a phone. Only the SHA-256 digest is stored. The raw
code is returned once and shown in the learner's current UI state; it is not written
to Android preferences and cannot be recovered. Regeneration deletes older
unredeemed codes. Startup and the periodic runtime worker remove invitation rows 30
days after their expiry by default. Deployments can configure 1 to 365 days with
`LEARNING_GUARDIAN_INVITATION_RETENTION_DAYS`; invalid values fail configuration.
Account deletion removes its outstanding invitations immediately.

The code is a possession credential. The UI tells learners to provide it directly,
but this implementation does not verify a real-world parent/teacher identity, child
age, legal guardian status, or institutional authorization. Production child-consent
requirements remain a policy/UAT gate.

## Verification

Backend tests prove hashing/no raw storage, replacement, expiry, single use,
self-link rejection, duplicate protection, separate-account listing, linked report
equivalence, denial to unrelated accounts, inability to read a mastery session or
document library, immediate learner/guardian revocation, learner-owned access
history, deleted-guardian identity minimization, and deletion cascade.
The full backend regression passed 451 tests with one existing Windows skip after
the retention worker and configuration bounds were added.

On the dedicated API 36 emulator, `scripts/qa-guardian-access.ps1
-ResetTestAppData` signed into a separate guardian account, redeemed a learner's
fresh code through the Android UI, opened the Grade 8 read-only report, verified the
privacy disclosure, removed the learner, and confirmed both server-side access lists
were empty. Disposable accounts were deleted and app data cleared. The inspected
`artifacts/qa-guardian-access.png` shows a readable report and uncalibrated-readiness
disclosure; it is untracked QA evidence, not APK content.
Android verification passed 128 JVM tests with zero failures/skips, lint, and debug
assembly; the PowerShell harness parsed without errors.

A follow-up API 36 run extended that same isolated journey through guardian-side
unlink, learner sign-in and consent-history recovery. The harness verified the
API contained exactly the grant followed by `revoked_by_guardian`, then found both
events through Android. The inspected `artifacts/qa-guardian-history.png` shows no
active report access, newest-first plain-language history, readable dates and a
bounded long test email. Android verification now passes **141 JVM tests** with
zero failures/skips, lint and debug APK assembly. The emulator occasionally
reported a null accessibility root while dumping UI state, but the bounded retry
recovered and the journey completed; no application request failed.

The API 36 guardian journey now continues through the Android system document
picker, saves `report-access-history.csv`, and reads the saved file back from the
emulator. It verifies the header, grant and guardian-revocation rows, guardian
account label, and absence of the internal guardian identifier, then removes the
export and disposable accounts. The privacy-bounded audit CSV therefore has
backend authorization/privacy automation and API 36 device verification.

This remains development and emulator QA evidence. Parent/teacher identity policy, physical-device accessibility,
real-user UAT, external notification policy, broader student-data retention, and
production deployment remain open. PARENT-01 is
therefore partial, not UAT accepted or production verified.
