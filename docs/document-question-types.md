# Document question types and Android QA

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
preference. Legacy missing server metadata displays unspecified. Existing
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

The opt-in `serve_qa.py --qa-only --binary-fixtures` service now provides clearly
labeled binary UI fixtures. It binds only localhost, uses the isolated QA runtime,
replaces the document provider before serving, and rejects non-binary requests
instead of calling a live provider. Normal application startup never installs
these fixtures. All 154 backend tests passed, including explicit QA opt-in,
fixture labels/choices and refusal to fall back for unsupported formats.

Android response validation now rejects an unconfirmed binary creation format,
unknown saved format, mismatched quiz-level options, noncanonical binary choices,
and empty/duplicate/wrong-count multiple-choice options. Missing type metadata
remains compatible only with legacy four-option questions. Creation validation
occurs before the view model saves a new active quiz pointer. Resume validates
pending/next choices against the saved quiz format; individual question decoding
also validates choices against that question's declared format.

Debug build, lint and 54 JVM tests passed, including supported/legacy formats,
mismatched or missing binary metadata and malformed choices. No live requests
were needed. These pure validation tests do not prove device error recovery for
injected malformed responses. A server may already have committed creation before
Android rejects its response; this change does not implement creation idempotency
or rollback. Cross-response consistency and creation-retry recovery remain open.

Both API 36 fixture runs passed with `-ResetTestAppData -BinaryFixtureType
true_false` and `-ResetTestAppData -BinaryFixtureType yes_no`. Android renders two
choices and the saved format, handles a first-question conflict without overwrite,
submits a wrong answer to question 2, restores that feedback after restart and
continues to question 3. The 2026-09-04 reruns also submit the known correct answer
for question 3 through Android, verify correct feedback, restart and continue to
question 4. Results and saved-format labels restore after completion. Later answers
are submitted by the API fixture. Both question-3 screenshots were visually inspected:
`artifacts/qa-binary-true_false.png` and `artifacts/qa-binary-yes_no.png`.
No metered calls were made. The service was returned to normal isolated QA mode
after these runs; saved disposable fixtures remain explicitly labeled QA.

Account switching and live-provider binary answering/recovery on Android remain
unverified. Mixed-format quizzes are not implemented; one configured format per
quiz is the supported contract. Broader source-material validation, educator review,
actual user UAT and production acceptance remain open. The supported single-format
document quiz contract is QA verified.
