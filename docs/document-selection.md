# Document selection boundaries

The original `Initial_plan.md` requires entire-document, single/multiple-chapter,
section, page-range and custom-topic selection. Android now exposes chapter
checkboxes, Entire document and Clear selection. Section/page/topic selection
remains missing; chapter-set support does not establish delivery of those modes.

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

Android selection is saved as a JSON array under the existing account-scoped
active-document chapter preference. Legacy single-ID values are read as one
selection. Explicit clearing survives restart; missing or corrupt IDs result in
an empty selection, never silently choosing another chapter. A new/reopened
document initially selects its first chapter. Generating a quiz sends all selected
IDs. Empty selection disables generation; delete/reset paths clear selection.
Entire document selects every detected chapter, subject to the existing live
40,000-character input limit; the UI warns that large selections need splitting.

Android build/lint and 45 JVM tests passed on 2026-09-03, including restoration
order, clearing, missing IDs and document-deletion cleanup.

On 2026-09-03, `scripts/qa-document-recovery.ps1 -ResetTestAppData -VerifyLibrary`
passed on LearnSmart_API36 with the updated debug APK and refreshed scripted
localhost QA backend. The run used a disposable account and synthetic biology
notes through the real Android file picker. Entire document selected both
chapters and survived force-stop/restart. Clear selection remained empty after
another restart, with generation marked disabled. Selecting only Plants then
survived restart, including its saved JSON-array preference. The generated quiz's
source reference matched Plants. Existing quiz restart, conflict recovery,
completion restoration and library reopen checks also passed without duplicate
documents or changes to the previous quiz.

The screenshot `artifacts/qa-document-chapters.png` was visually inspected:
checkboxes, count, selection controls and generation action were readable.
This is agent-run workflow QA, not user UAT, full accessibility evaluation or
live-provider quality evidence. Legacy preference migration on device, account-switch behavior, large-document
limits and physical-device coverage remain pending.

The subsequent API 36 run added `-VerifyMultiChapter` and passed on 2026-09-03.
It selected Plants and Cells individually, restored both saved IDs after restart,
and generated ten questions from Android. The test collected each question's
source reference while completing the disposable quiz through the API: both
selected fixture chapters were represented, and every reference matched one of
them. The existing conflict/restart/results/library checks passed as well.
`artifacts/qa-document-multi-chapters.png` was inspected with both boxes selected.
This is deterministic synthetic-fixture evidence, not a guarantee of proportional
chapter coverage or live generation quality for arbitrary documents.

Remaining work: section/page/topic retrieval with explicit boundaries; selection
review/recovery device tests; and coverage/quality evaluation over selected material.
This is not UAT or production sign-off.

## Detection coverage repair

The detector previously discarded heading ranges shorter than 80 characters and
omitted non-heading introductory text. Selecting every detected chapter could
therefore omit real source content. New analyses now preserve short sections with
confidence 0.55 and expose nonblank introductory material as
`document-introduction`, titled `Introduction / before first heading`. Heading
IDs count headings independently of that introduction. Long sections retain the
existing 0.85 heuristic confidence; these numbers are not calibrated probabilities.

164 backend tests passed, followed by seven focused coverage tests after adding
an upload/reopen integration case. Tests verify short intermediate/final sections,
introductory coverage, contiguous reconstruction, heading IDs, whitespace-only
prefixes, the unheaded fallback and stored structure preservation. No live AI
calls or Android edits were needed for this repair.

Existing stored chapter arrays are intentionally unchanged: silently renumbering
them could invalidate saved selections. Safe reanalysis/migration and a new-device
selection check are still needed. Detection remains a flat heading heuristic, not
a hierarchical section model, PDF page selection or topic retrieval. DOC-02 remains
partial. This repair prevents tested omissions in newly analyzed material; it does
not prove quiz coverage of every included fact.

## Explicit repair for existing stored documents

`POST /v1/documents/{id}/structure/repair` now fills nonblank gaps in existing
stored ranges without changing any existing chapter ID, title, confidence or
offset. New ranges are labeled `Previously omitted text (characters start-end)`
with confidence 0.35, not presented as confidently detected chapters. They are
inserted in source order with stable collision-safe IDs. Repeated repair has the
same result. Blank gaps are ignored.

The endpoint verifies ownership and performs validation/update in one write
transaction. Duplicate IDs, overlaps, out-of-order or out-of-bounds ranges return
422 without modifying the structure. Missing or other-owned documents return
404. Existing quizzes/questions are untouched; this is gap repair, not full
reanalysis or a change to existing question evidence.

172 backend tests passed; all seven repair tests passed again after adding API
rejection-without-mutation coverage. Tests include gap reconstruction, stable
existing metadata, repeatability, ID collisions, empty structure, unsafe ranges,
ownership and exact preservation of existing quiz rows. No live AI calls or real
user-document repairs were performed. Android repair controls and device QA
remain pending, along with richer section/page/topic selection.

## Android explicit repair control

The chapter selection screen now offers `Check for omitted text`, with an
explanation that existing chapters and quizzes remain unchanged. It calls the
owner-authenticated repair endpoint only when selected; it does not run on open.
Recovered ranges remain unselected. Existing selected IDs, quiz settings and the
persisted pending quiz creation identity are not modified. The result reports
the number added or that no omissions were found. Ranges below 0.6 confidence
have a visible review warning, including introductory and recovered text.

The client rejects a different document, duplicate IDs, removed/reordered/changed
existing chapter metadata or a missing selected ID before accepting the response.
The server remains responsible for offset validation. Loading blocks selection
changes; transport/API failures use the existing error/retry path. A lost repair
response can be retried because server repair is idempotent. Reopening or process
restoration obtains the persisted server structure; the result notice itself is
transient.

Android debug build, lint and all 61 JVM tests passed. Three new tests exercise
selection/settings preservation, unchanged quiz creation fingerprint, repeat
repair, empty selection and unsafe response rejection. The viewmodel does not
write the pending creation preference during repair. No live provider requests
were made. Device UI, process recreation and injected repair-response failure
checks remain pending; this is not UAT acceptance. DOC-02 remains partial because
hierarchical section, PDF page-range and topic selection are still missing.

## Android repair recovery device evidence

`scripts/qa-document-recovery.ps1 -ResetTestAppData -VerifyCreationRetry
-VerifyStructureRepair` passed on the dedicated LearnSmart_API36 emulator. The
explicit localhost QA runner created a 40-character tail omission in the
disposable `qa-biology.txt` fixture and replaced the successful repair response
with HTTP 503 after commit. This fixture route is owner-scoped, rejects other
filenames, and is not installed in the normal application.

Verified: Android retains its old list after the failed response; retry displays
one new unselected range; the low-confidence warning is visible; restart restores
the expanded list and original selection; repeated repair reports no omissions;
the pending creation identity, existing quiz question and progress are unchanged.
The subsequent generation retry resumes the same quiz, with exactly one server
quiz. Quiz restart, answer-conflict recovery and completed-results restoration
also passed (remaining answers were submitted by the API fixture).

Inspected `artifacts/qa-structure-repair.png`: the original Plants chapter remains
selected and the recovered 1194–1234 range is unchecked with its warning. All 173
backend tests passed, including owner/non-fixture rejection, post-commit failure
and idempotent retry. No live AI requests or real user documents were involved.
Actual TCP loss, device-level unsafe-structure rejection and user UAT remain
unverified; this evidence does not complete richer selection modes or production.

## Review source text before selection

Android now offers a separate preview action for each chapter, including recovered
low-confidence ranges. An owner-authenticated, read-only endpoint returns verbatim
source text in 2,000-code-point parts without reading neighboring ranges or calling
an AI provider. Previous/next controls do not change the quiz selection or pending
creation identity. These parts are explicitly labeled as text chunks, not PDF
pages. See `shared/contracts/document-preview.md` for bounds and failure behavior.

175 backend tests and Android build/lint/63 JVM tests passed. Device preview
navigation, offline/retry and accessibility checks remain open; no user UAT is
claimed. Original-page rendering and section/page/topic quiz selection remain
separate outstanding requirements.
