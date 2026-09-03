# Exact document excerpt selection

`POST /v1/documents/{document_id}/quizzes` accepts optional `source_ranges` in
addition to the existing `chapter_ids` and quiz settings:

```json
{
  "chapter_ids": ["chapter-1"],
  "source_ranges": [
    {"chapter_id": "chapter-1", "start_character": 120, "end_character": 950}
  ],
  "question_count": 5,
  "difficulty": "easy",
  "question_type": "multiple_choice"
}
```

The example offsets are illustrative, not valid for every document. Offsets are
absolute **Unicode code points**, start-inclusive and end-exclusive, matching
chapter/source-preview offsets. Android must convert UTF-16 text-selection
positions rather than forwarding Kotlin string indices for emoji/non-BMP text.

## Boundaries

- Omit the field or send null for the existing whole-selected-chapter behavior.
  An empty array is invalid, not a fallback to whole chapters.
- Select 1–50 nonblank, disjoint excerpts. Multiple excerpts can belong to the
  same chapter. Adjacent ranges are allowed and remain separate passages.
- Every selected chapter must have at least one excerpt, and no excerpt can
  name an unselected or unknown chapter. No selected chapter is silently omitted.
- Each range must fit wholly inside its named stored chapter. Reversed, empty,
  duplicate, overlapping, noninteger, negative and out-of-bounds ranges fail with
  422. The server never expands, clamps, merges or silently repairs the selection.
- Resolution happens after ownership checks and before either generator runs.
  Excerpts are sorted in source order and passed as distinct bounded passages.
  Excluded gaps and the remainder of a chapter do not become generation material.
  Source references retain absolute offsets. Existing source-grounding validation,
  live 40,000-character limit and question-count/quality checks still apply.
- A short excerpt may not support five distinct questions. Failure must ask for
  more selected material or fewer questions within the existing 5–20 limit;
  generation must not widen the source or fill gaps with outside knowledge.

## Durability and compatibility

The additive nullable `quizzes.source_ranges_json` column stores the original
chapter IDs and sorted excerpt bounds with the quiz in the creation transaction.
`QuizSummary` (including creation replay) and `DocumentQuizState` return
`source_ranges`; legacy quizzes return null. This metadata describes the source
scope used to create the quiz, not an instruction to regenerate it on resume.
Existing Android builds ignore the additional response field and continue
requesting whole selected chapters.

Creation fingerprints include exact excerpt bounds; changing them or removing
them under an already committed request ID returns 409. Reordering identical
excerpts retains the same fingerprint. Requests without excerpts retain the
pre-change fingerprint format, so an outstanding legacy retry is not broken by
the new optional field. Existing chapter-ID order behavior is unchanged.

## Verification and remaining delivery

Backend tests cover disjoint Unicode ranges, excluded gaps, unknown/omitted
chapters, blank/overlapping/out-of-bounds excerpts, exact generation input in
both provider routes, persisted resume, replay without generation, changed-scope
conflicts, other-owner denial and legacy fingerprint compatibility. The live
provider route is stubbed for these tests; no API credits are consumed and this
does not establish live question quality.

On 2026-09-03, the full backend regression suite passed: **230 passed, 1 skipped**
(the existing Windows backup symlink-privilege test), with the existing
Starlette/httpx deprecation warning. The Unicode fixture initially had an
off-by-one expected selection; correcting its supplied offsets made the exact
substring assertion pass. No actual source offset correction was made silently.

This is the server foundation for section/excerpt selection, **not a completed
Android selection feature**. Android text-selection controls, selected-source
review, durable pending request state and device recovery tests remain to be
implemented. It is not semantic topic retrieval or original PDF-page indexing;
those original DOC-02 requirements remain open, as do educator evaluation and UAT.
