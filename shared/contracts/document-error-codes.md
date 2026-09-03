# Safe document recovery messages

Document selection and deterministic quiz admission may return HTTP 422 with an
optional `X-Learning-Error` header. It contains only a fixed code, never source text,
credentials, paths, model output or a copy of the exception message. Status codes,
authorization checks and existing response bodies remain unchanged.

| Code | Recovery offered by Android |
| --- | --- |
| `insufficient_quiz_material` | Choose fewer questions or more source material. |
| `empty_pdf_pages` | Choose pages with extracted text; OCR is unavailable. |
| `pdf_coverage_gap` | Check for omitted text, then reload and review pages. |
| `too_many_pdf_ranges` | Choose fewer pages to stay within 50 ranges. |

Android reads the code only on non-authentication 422 responses and maps exact
allowlisted values to client-owned messages. It does not interpolate the header,
parse the error body, or display arbitrary server details. Missing, unknown,
combined, wrong-case or whitespace-padded codes use the generic safe message.
Authentication responses and other statuses cannot be overridden by this header.
Error streams are closed and connections disconnected as before. Older servers
and clients continue to use generic errors; no migration is required. Native
Android does not depend on browser CORS header exposure.

The insufficient-material code applies to the deterministic generator's known
sentence/count admission failures, not arbitrary live-provider failures. Other
validation failures remain generic; this is not a claim that every app failure
now has a specific recovery message. No retry, selection widening or quiz creation
is performed by error handling.

Verification covers emitted HTTP codes for blank pages and insufficient material,
unchanged success/unauthorized/schema-error behavior, domain coverage/range-limit
codes, Android allowlist/fallback/authentication behavior and suppression of
synthetic sensitive bodies. The PDF device QA script expects the new messages
and captures each error dialog for visual inspection.

On 2026-09-03, the full backend suite passed 254 tests with one existing Windows
symlink-privilege skip and the existing Starlette/httpx warning. Android debug
build, lint and all 95 JVM tests passed. No live AI calls were made.

## Android message checks

The API 36 rerun against implementation `06b4bec` displayed both the textless-page
and insufficient-question-material messages. Screenshots were visually inspected:
the complete recovery text and dismissal control were readable without clipping
at the emulator's current font scale. Both failures preserved saved selection.
The control labelled Try again dismisses the dialog; it does not automatically
repeat a request. The learner then changes page/count inputs and submits again.

The full run exited zero: five-question count and selected range survived restart;
the simulated committed-response 503 retried into exactly one quiz; all five source
references stayed within page 2 (288–591); conflicting-answer recovery and completed
results restored correctly. Remaining answers were submitted by the API fixture.
Transient uiautomator null-root warnings recovered through fresh-dump retries.

These observations do not cover the omitted-coverage/range-limit messages on a
device, large text, TalkBack, arbitrary network failures or live-provider quality.
Those checks and actual user acceptance remain open.
