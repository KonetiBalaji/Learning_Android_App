# Document selection boundaries

The original `Initial_plan.md` requires entire-document, single/multiple-chapter,
section, page-range and custom-topic selection. The current Android UI exposes
single-chapter selection only. The backend accepts multiple chapter IDs, but this
does not establish full delivery of those selection modes.

Both deterministic and live generation now use `resolve_chapters` to validate
the complete selection. Unknown IDs, empty selections, repeated IDs, ambiguous
stored IDs, invalid source offsets and overlapping/out-of-order selected ranges
are rejected. Selection is resolved in stored source order, independent of click
order. Unselected chapters are not passed to generation. Validation occurs before
live provider access; invalid selections cannot silently become a smaller quiz.

Previously the deterministic generator silently ignored unknown IDs mixed with
valid IDs; the live generator rejected unknown IDs but accepted duplicates.
Both paths now follow the same contract. This does not change question quality
or claim that a generated quiz covers every selected chapter equally.

On 2026-09-03, 105 backend tests passed. New tests cover mixed/duplicate/empty
IDs, bounds, overlap, source order, all-chapter resolution, excluding unselected
text, rejection before either generator runs, and API 422 without saving quizzes
or questions. No live provider requests or Android edits were made.

Remaining work: multi-chapter/entire-document Android controls and persisted
selection; section/page/topic retrieval with explicit boundaries; selection
review/recovery tests; and coverage/quality evaluation over selected material.
This is not UAT or production sign-off.
