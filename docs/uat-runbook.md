# Learn Smart AI user acceptance runbook

Status: preparation only. No user acceptance has been recorded. The current debug
APK and localhost QA service are not a production candidate. Automated QA results
must not be entered as user sign-off.

## Candidate gate

Before inviting a tester, record the immutable Git commit, APK SHA-256, package
version, signing-certificate identity, backend deployment/version and provider mode.
Use a reachable, approved staging service and a private APK supplied through an
agreed channel. A physical phone cannot use the emulator's host-only service address.
Do not label a debug build as a signed production release.

Confirm the approved Grade 8 Open OER Foundation catalog, supported subjects and
test materials. Check release-acceptance.md for every original requirement.
Grades 1–7 and 9–12 remain later scope and must stay visibly unavailable.
Resolve release-blocking security, data-loss and learning-correctness issues first.
Record any agreed test-only limitations; they do not silently change product scope.

Use synthetic student profiles and owned/public test documents. Do not use real
children's information until access, consent and retention decisions are approved.
Identify test account ownership and cleanup responsibility. Keep credentials,
provider keys, raw student responses and private documents out of issue reports.
Obtain approval for the test's live-provider budget; deterministic QA is not proof
of live lesson quality. Production operations remain a separate gate.

## Tester journeys

For each journey record PASS, FAIL or NOT TESTABLE, the candidate/device, exact
steps, expected/actual result and issue ID. A missing feature is NOT TESTABLE, not
PASS. The tester, not the coding agent, confirms learning usability and acceptance.

| Journey | User-observable acceptance checks | Current limitations to resolve |
| --- | --- | --- |
| Account and isolation | Register/login, wrong password, sign out/in, switch test accounts; no other student's documents/progress appear | Google login/configuration and broader account-switch verification remain open |
| Curriculum and navigation | Choose Grade 8, each subject and chapter; confirm the Open OER Foundation identity, titles and app-authored content; return and restart | Educator review and later-grade coverage remain open; no national/state board alignment is claimed |
| Learning and mastery | Answer correctly and incorrectly; inspect explanation/example, ask for a hint, practice, submit weak and sound rewrites; verify restart and prerequisite progression | Broad subject coverage and live grading false-pass/age-suitability evaluation remain incomplete |
| Document study | Upload valid PDF/DOCX/TXT; select chapters, highlighted text, literal search passage and physical PDF pages; confirm only chosen content supports questions | Semantic topic/section scope and complex/scanned PDFs remain partial; OCR is unavailable |
| Failure and recovery | Choose a blank page or too many questions for short material; read the message, change the selection/count and recover; interrupt network and restart | New message/device/network cases must have candidate-specific evidence |
| Quiz and results | Choose count/difficulty/format; answer all questions, read feedback, restart mid-quiz and after completion; compare results and source references | Live difficulty/format quality and mixed configuration remain partial |
| Progress and reports | Inspect weak concepts, chapter progress, study time and weekly totals; compare with known test activity | Parent/teacher roles and consent remain undecided; readiness is a heuristic, not a validated exam prediction |
| Voice, visuals and access | Use verbal input, cancel it, deny/unavailable service, listen to teaching, test visible interactive explanations; dark/light, large text and TalkBack | Conversational/animated teaching and full accessibility are not yet verified |
| Deletion | Delete a synthetic document/account and confirm loss of access without affecting another test account | Retention and production cleanup policy still need approval/verification |

Run supported journeys on at least the agreed physical Android device and record
Android version, screen size, font scale, theme and network. Cover both successful
flows and recovery. Screenshot evidence must omit personal data. Report confusing
instructions and educational errors, not just crashes.

## Issue and acceptance record

Create a candidate-bound JSON record only after the signed APK manifest exists:

```powershell
cd backend
uv run python -m app.uat_record init ..\artifacts\private-release\candidate-manifest.json ..\artifacts\private-release\uat-record.json
```

The generated record lists every pre-production acceptance-ledger requirement. Fill
it with physical-device observations and redacted evidence; do not remove rows or
change the copied candidate identity. `SCOPE_ACCEPTED` requires the user's explicit
approval text. Before treating the result as acceptance, run:

```powershell
uv run python -m app.uat_record verify ..\artifacts\private-release\candidate-manifest.json ..\artifacts\private-release\uat-record.json --require-acceptance
```

The validator fails closed for a different APK/backend/commit, missing requirements,
untestable or failed rows, absent evidence, incomplete tester/device identity,
timezone-free dates, unapproved scope changes, and unresolved issues. A passing
record verifies completeness and identity only; it does not replace the tester's
actual observations or decision.

For each issue: `ID / requirement IDs / candidate commit+APK hash / device / steps /
expected / actual / impact / Support ID when shown / redacted evidence / fix commit / tester retest result`.
The Support ID is safe operational correlation metadata; do not copy response bodies,
tokens, learner answers or other private content into the report.
Do not close an issue solely because a unit test passes. Reproduce the user's
journey on the corrected candidate and have the tester confirm the outcome.

Acceptance requires the user's explicit decision for the identified candidate,
with tester name/role, date, completed journey records and remaining issues.
Reconcile **every** row of release-acceptance.md against evidence or an explicit
user-approved scope change. Unexecuted, missing and NOT TESTABLE requirements
prevent full acceptance. Preserve the original scope until the user changes it.

After UAT acceptance, separately verify production HTTPS, secrets, migrations,
retention, backup/restore, rate/cost controls, monitoring, rollback and private APK
distribution. Neither a local QA pass nor a UAT sign-off proves production readiness.
