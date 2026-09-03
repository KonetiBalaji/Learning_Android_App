# Document question types: implemented, device QA pending

2026-09-03: added one selected type per quiz: multiple choice, True/False or
Yes/No. The API defaults omitted type to multiple choice and rejects unknown/null
types. Existing quizzes/questions migrate to multiple choice on repeatable
initialization. Type metadata survives creation, recovery and mistake review.

Live generation validates exact option count and canonical binary labels/order,
checks the correct index, preserves source selection and runs both blind answer
and quality reviews. False/No must be contradicted by source evidence rather than
inferred from absent information. Binary options are not shuffled. Offline mode
rejects binary generation before saving a quiz; it does not fabricate negatives.

## Verification

- 150 backend tests passed. After the final blind-review guidance addition, all
  34 provider/type tests passed again.
- Tests cover type routing, both binary answer indices, invalid labels/order/count,
  invalid correct index, unknown types, legacy migration, creation/resume metadata,
  correct/incorrect grading, invalid answers, identical retries, conflicting retries,
  completion and mistake types. Provider stubs test mechanics, not educational truth.
- Six metered `gpt-5-mini` requests using the approved existing key generated two
  five-item Easy batches and ran both reviews. Both passed automated checks.
  Development-agent review found all ten answers correct against the synthetic
  source, including contradictory evidence for the False/No answers.
- The True/False sample includes one two-tank capacity comparison, which is not
  strict single-fact recall despite the Easy request. It also exposes internal
  excerpt labels in explanations. These remain quality issues, not accepted
  calibration. The Yes/No sample has four Yes and one No answer; balance is not
  currently guaranteed.

Local evidence:

- `artifacts/difficulty-eval-20260903T084316587025Z.json` (True/False)
- `artifacts/difficulty-eval-20260903T084320408647Z.json` (Yes/No)

## Remaining work

Android now provides format radio controls, sends the selection, saves it in
account-scoped device preferences and restores it when opening an uploaded
document. Question/results labels use server-saved metadata, not the current
preference. Missing or unknown server metadata displays unspecified. Existing
dynamic answer rendering supports two or four options without changing grading.
Controls are disabled while loading; the screen explains that binary formats
require live generation. Debug build, lint and 51 JVM tests passed, including
supported preference restoration and unknown/absent format labels. No live API
requests were made for this Android implementation step.

API 36 emulator QA now passes selection/restart for both binary formats, matching
account-scoped preferences, offline rejection without a quiz pointer, switching
back to multiple choice, saved format labels after question/results restart,
conflicting-answer recovery and library reopening. Command:
`scripts/qa-document-recovery.ps1 -ResetTestAppData -VerifyLibrary -VerifyQuestionType`.
Remaining multiple-choice answers were submitted through the API fixture, not
all through Android. The Yes/No selection screenshot was visually inspected:
`artifacts/qa-document-format-yes_no.png`; the run also captured True/False.
An initial run terminated on an ADB daemon connection failure before format
checks. After `adb start-server`, device/boot verification and a fresh disposable
test run, the full script exited successfully. This was a tooling interruption,
not a demonstrated app defect. No live provider requests were made.

Account switching and actual binary answering/recovery on Android remain
unverified. Mixed-format quizzes are not
implemented. Broader materials/counts/difficulties, educator review, actual user
UAT and production acceptance remain open. The shared configuration contract
defines the API; this backend slice does not complete DOC-03.
