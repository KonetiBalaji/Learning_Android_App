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
