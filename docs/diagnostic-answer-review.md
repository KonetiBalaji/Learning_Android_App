# Generated diagnostic answer review

Previously the generated diagnostic bank was checked for shape, unique choices
and answer membership, but not independently solved before persistence. Generated
banks now undergo a second structured model call that receives only the requested
grade/subject/chapter and indexed questions/options. The proposed answer key,
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

The API-key skill's credential boundary is unchanged: reuse is already authorized,
credentials stay on the server, and verification in this slice uses mock responses
with no live provider calls. Live diagnostic generation now incurs one additional
review request, subject to the existing provider retry policy. Android's diagnostic
creation read timeout is extended to the existing generation budget of 135 seconds;
normal API reads remain at 30 seconds. This is not a server job queue, progress
stream or idempotent diagnostic-creation protocol. Reverse-proxy timeouts, real
latency, costs, failure recovery and request quotas remain deployment work.

## Evidence boundaries

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
does not verify the generated teaching explanations, worked examples, hints or
practice answer sets. Human-reviewed evaluation data, live false-pass testing,
authoritative curriculum grounding and device recovery remain open. ASM-01,
TUT-01 and CUR-01 therefore remain partial.
