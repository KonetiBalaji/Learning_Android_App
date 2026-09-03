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

## Android selection and persistence

Android now exposes a read-only source text field in chapter preview. Long-press
and highlight text, then explicitly choose **Use highlighted excerpt instead of
whole chapters**. In excerpt mode, **Add highlighted excerpt** adds another
disjoint range. The first confirmation replaces whole-chapter selection; simply
viewing, highlighting or paging does not commit anything. A selection is limited
to the currently displayed preview part, but additional parts can be added.

The chapter screen labels excerpt mode and lists chapter names and absolute
offsets. Its checkbox, Entire document and Clear selection controls explicitly
reset excerpt mode, as explained on-screen. Selecting overlapping/repeated or
blank excerpts produces an error instead of merging or widening the source.

Confirmed selections atomically save chapter IDs and canonical excerpt ranges in
account/document-scoped preferences. They contain no copied source text. Reopening
the active upload restores them; malformed saved data fails rather than falling
back to whole chapters. Opening another document starts a new selection. Deletion
clears its stored selection; quiz creation clears local excerpt metadata only
after the server confirms the requested ranges on both POST and authoritative GET.
Saved quizzes load their scope from the server. Request identity includes bounds
but retains the old fingerprint for whole-chapter requests.

Selection indices are converted from Android UTF-16 into server Unicode code
points, with split surrogate pairs rejected. Pending highlight gestures are not
durable; only the explicitly confirmed selection is saved. The backend must be
upgraded before this Android build: an older server may ignore unknown fields
and create a whole-chapter quiz, but Android will reject its unconfirmed scope
and keep the pending identity instead of presenting that quiz as selected text.

Debug build, lint and 78 JVM tests passed. Added tests cover emoji/reversed
selection, partial surrogate/empty/whitespace rejection, disjoint persistence,
corrupt preferences, overlap limits, scope-aware request IDs and deletion cleanup.
No live calls were made. Device text-highlight usability, restart/account-switch,
lost-response recovery, malformed-response injection and accessibility QA remain
open. This implementation is not yet device-verified or UAT accepted.

## API 36 excerpt recovery evidence

`scripts/qa-document-recovery.ps1 -ResetTestAppData -VerifyCreationRetry
-VerifyExcerpts` passed on LearnSmart_API36 with APK source `689807a` and the
updated isolated scripted-QA backend. It uploaded the synthetic preview fixture
through Android's picker, selected the first Plants preview part using Android's
Ctrl+A text-selection command, and explicitly confirmed excerpt mode. This
selected characters **307–2307**, leaving the remainder of the chapter excluded.
Confirmed preferences and the displayed boundaries survived force-stop/restart.
`artifacts/qa-document-excerpt.png` was visually inspected and its labels were
readable; the image is a local QA artifact, not a committed learner document.

The test injected HTTP 503 after quiz creation committed. The pending identity
survived restart; retry opened the same quiz, with exactly one server quiz and
the exact saved source range. Accepted creation cleared pending local excerpt
metadata. Question restart, conflicting-answer recovery and feedback restart
passed. All ten question references matched only the selected excerpt. Remaining
answers were submitted by the API fixture, then Android restored the completed
results. This is not a claim that every answer was entered through Android.

Transient `null root node` dump errors recovered; the document harness now retries
for a fresh dump instead of reading stale XML. No live AI calls occurred. This
verifies one whole-preview-part excerpt, not touch-handle dragging, partial-part
selection, multiple excerpts, account switching, TalkBack/large text, live quality
or UAT. Those device/acceptance checks and original page/topic retrieval remain open.
