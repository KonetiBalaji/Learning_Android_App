# Generated diagnostic answer review

## Safe rejection diagnostics

Review rejections carry fixed reason codes and zero-based question indices.
Codes distinguish diagnostic ambiguity, topic/grade fit, unresolved answers,
key disagreement, response ordering and practice validity/key/numeric-parsing
failures. All applicable reasons are collected from a complete review. Misordered
responses are not used to infer an answer disagreement. `-1` is unresolved,
not evidence that the reviewer found a different correct answer.

The explicit smoke evaluator emits only those codes/indices on rejection, never
the exception message, raw rejected model output, prompt, answer or credentials.
No new production log or HTTP response fields were added. Raw rejected banks
are not retained. Therefore these diagnostics identify a failure category and
item, not the underlying educational truth or whether rejection was justified.

The deliberate-key negative test now passes only when the review disagrees with
the corrupted diagnostic key at index 0. Rejection for another question, an
unresolved answer, a practice-only problem, malformed output or an outage does
not count. This corrects an overly broad success condition in the prior smoke.
It does not prove the reviewer's alternative answer was correct. Earlier live
negative results without these reason codes remain weaker historical evidence.

### Live diagnostic findings

The instrumented smoke (`gpt-5-mini`, existing key, no retries, three requests)
rejected the generated bank in 21.25 seconds with `practice_key_disagreement`
at indices 0, 1 and 2. The deliberate corruption was detected at diagnostic
index 0 in 9.98 seconds. Rejected content was not captured in this run, so the
cause of those three disagreements cannot be reconstructed.

A separate two-request synthetic-only inspection captured generator and reviewer
JSON in the development console (not production logs or learner sessions).
It exposed a reproducible failure pattern:

- Generated practice: `Find (4/7) ÷ (8/21).`, acceptable answers `3/2` and `1 1/2`.
- Independent review: answer `3/2`, valid true, but answer mode `exact`.
- The server correctly enforced that policy, rejecting the second proposed
  answer. However the policy itself was unnecessarily restrictive: the prompt
  has no representation constraint and 4/7 × 21/8 = 3/2 = 1 1/2.
- The same review assigned exact to unconstrained `Calculate 3/4 + 1/6.`;
  that item passed only because its sole proposed answer matched `11/12`.

This is direct evidence of a false rejection in the reviewed-policy workflow,
not an arithmetic error in the inspected generated keys. It does not establish
the cause of the earlier uncaptured failures. The next required repair is better
explicit classification/validation of prompt format constraints, with positive
and negative regression fixtures. Do not disable the reviewer or make all
fractions numerically equivalent: requested denominators and lowest terms still
need exact representation. Five live calls were made in this diagnostic slice;
generation used a 60-second timeout, reviews 20 seconds, with retries disabled.

Full backend QA for safe diagnostics passed 369 tests with one existing Windows
symlink-privilege skip and the existing Starlette/httpx warning. Device QA, broader
quality evaluation and UAT remain open; this slice does not fix the false rejection.

## Practice-review extension: 2026-09-03

This extension adds practice screening to the same blind review call. The original
implementation/test counts below are historical; the updated behavior is described
throughout this document. Credentials remain server-only under the API-key skill.

Live evidence using the existing approved key and `gpt-5-mini`, no retries:

- `uv run python scripts/evaluate_diagnostic.py --live` rejected the newly generated
  Grade 8 Fractions bank with `DiagnosticReviewRejected` after 28.92 seconds.
  The evaluator does not retain rejected content or identify the particular item,
  so this is not evidence of a specific error or a successful generation. The
  deliberate diagnostic-key corruption was rejected after 9.12 seconds.
- A controlled two-call review used the unchanged three built-in diagnostic
  questions, with practice prompts: `Calculate 3/4 + 2/5.` (key `23/20`), the
  existing `2/3` with denominator 6 exercise (key `4/6`), and
  `Simplify 6/8 to lowest terms.` (key `3/4`). Review accepted the bank and returned
  policies `number`, `exact`, `exact`, respectively. These results are independently
  checkable arithmetic: 15/20 + 8/20 = 23/20; 2/3 = 4/6; 6/8 reduces to 3/4.
- Repeating that controlled review with only the first practice key changed to
  `7/9` produced `Practice answer review rejected the generated bank`. No learner
  session was created by these direct review calls. Both controlled calls used
  the review's 20-second timeout. Five provider requests total were attempted
  across the generation smoke and controlled checks, with no retries.

These are narrow live checks, not a pass rate, latency guarantee or teacher UAT.
The failed generation remains an open quality/availability observation rather
than being hidden by repeated generation attempts. Broad positive/negative
fixtures and better safe rejection diagnostics remain needed.

Final extension QA: `uv run pytest -q --tb=short` passed 362 tests, with one
existing Windows symlink-privilege skip and the existing Starlette/httpx warning.
HTTP coverage verifies rejected practice creates no session and accepted banks
persist the reviewed numeric/exact policy. No Android code changed; device QA
for generated practice and user acceptance remain pending.

Previously the generated diagnostic bank was checked for shape, unique choices
and answer membership, but not independently solved before persistence. Generated
banks now undergo a second structured model call that receives only the requested
grade/subject/chapter, indexed questions/options and practice prompts. The proposed answer key,
concept labels, explanations, hints, examples and practice answers are withheld.

The reviewer returns an answer index plus ambiguity, topic-fit and grade-suitability
judgments for every item. Unknown answers, disagreement with any proposed answer,
false judgments, wrong ordering, partial results, non-strict values, malformed
responses or an outage cannot approve the generated bank. Structural checks still
run first. The bank reaches normal session persistence only after review passes.
Existing fallback behavior remains: Fractions can use the built-in Fractions bank;
unavailable topics cannot silently become Fractions. This does not expand the
deterministic curriculum catalog or certify the suitability of its fallback bank
for every supported grade.

The review now also returns an independently solved practice answer, a validity
judgment (unambiguous, solvable, on-topic and grade-suitable), and an exact/numeric
format policy. Every proposed practice answer must match the independent solution.
Numeric policy additionally requires a bounded parseable rational solution. Format
constraints (lowest terms, requested denominators, rounding, units, named options)
must use exact matching. The policy is persisted only after the whole bank passes.
This expands the existing review call, not the number of calls. See
`docs/practice-answer-matching.md` for matcher details and legacy behavior.

The API-key skill's credential boundary is unchanged: reuse is already authorized,
credentials stay on the server. The initial implementation used mock responses;
the extension's live checks are recorded above. Live diagnostic generation incurs one additional
review request, subject to the existing provider retry policy. Android's diagnostic
creation read timeout is extended to the existing generation budget of 135 seconds;
normal API reads remain at 30 seconds. This is not a server job queue, progress
stream or idempotent diagnostic-creation protocol. Reverse-proxy timeouts, real
latency, costs, failure recovery and request quotas remain deployment work.

## Original implementation evidence and remaining boundaries

Fourteen focused tests cover withheld fields, strict structured output, answer
disagreement, ambiguity, topic/grade rejection, malformed ordering/types, partial
review, outages, actual provider wiring, no wrong-chapter fallback and HTTP
creation refusing to persist a rejected bank. Accepted HTTP responses still omit
the answer key. Android's timeout test checks the bounded generation exception
without changing authentication/upload/read timeouts.

On 2026-09-03 the final full backend suite passed **302 tests, 1 existing Windows
symlink-privilege skip**, with the existing Starlette/httpx warning. Android
assembleDebug, lintDebug and **111 JVM tests** passed. No live model request,
real-device diagnostic timeout test or user acceptance was performed in this slice.

A subsequent bounded live Fractions smoke passed generation/review and rejected
one deliberately wrong key using the existing approved key. See
`docs/diagnostic-live-smoke.md` for exact observations, the timeout difference and
remaining quality concerns. This does not replace the broader evaluation gates.

The same model family can make correlated mistakes in both calls. Agreement is
a filter, not an accuracy guarantee or calibrated confidence score. Grade-fit is
a model judgment, not alignment with an approved country's curriculum. This review
does not verify the generated teaching explanations, worked examples or hints.
Practice review is also a model judgment: correlated errors or misunderstanding
of answer-format constraints can still pass, and equivalent textual synonyms may
be conservatively rejected. Human-reviewed evaluation data, live false-pass testing,
authoritative curriculum grounding and device recovery remain open. ASM-01,
TUT-01 and CUR-01 therefore remain partial.
