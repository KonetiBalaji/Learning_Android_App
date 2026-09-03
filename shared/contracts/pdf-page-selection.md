# Original PDF page selection

Page numbers here are **1-based physical pages in the uploaded PDF**, not printed
page labels, chapter numbers or the 2,000-character text-preview chunks. DOCX/TXT
documents do not have stable original PDF pages and are rejected by these routes.

`GET /v1/documents/{id}/pdf-pages` returns `document_id` and `pages`, each with
`page`, `start_character`, `end_character` and `has_text`. Offsets use the existing
absolute Unicode code-point convention, with an exclusive end. Blank/scanned
pages remain in physical page order; an empty page can have equal start/end.
Inter-page newlines match the existing upload extraction format exactly.

`POST /v1/documents/{id}/pdf-pages/selection` accepts:

```json
{"first_page": 2, "last_page": 4}
```

Both ends are inclusive and must be ordered positive integers within the PDF.
The read-only response contains `document_id`, `first_page`, `last_page`,
`chapter_ids`, `source_ranges` and `empty_pages`. It does not save a selection or
create a quiz. After explicit client confirmation, send its chapter IDs and ranges
through the existing excerpt quiz contract. Current quiz persistence records the
exact source ranges, not an independently persisted page-label field.

## Source safety

- Ownership is checked before reading the file: missing credentials return 401;
  missing/other-owner documents return 404. Paths must resolve directly inside
  configured uploads and must not be file symlinks. Service-owned storage and
  absence of hostile concurrent path mutation remain deployment assumptions.
- The PDF is re-extracted, and joining all page text must exactly equal stored
  extracted text before offsets are returned. Changed/corrupt/protected files,
  parser extraction drift and unsupported types return 422 rather than guessing.
  Missing/unreadable storage returns 503. No stored text or chapter ID is rewritten.
- Indexing currently limits files to the configured upload byte limit, 1,000
  physical pages, 200,000 characters per page and 2,000,000 total source characters.
  These are page-index admission checks, not a parser sandbox or strict peak-memory
  bound. Parser timeouts/process isolation and abuse limits remain production work.
- The chosen physical-page span is intersected with stored chapter boundaries,
  including chapters that cross pages and multiple chapters on the same page.
  Nonblank gaps in detected chapter coverage fail with a repair instruction.
  No nonblank selected text is silently omitted or expanded into adjacent pages.
- Blank-only selections fail; mixed selections report empty pages explicitly.
  OCR is not implemented. At most 50 nonblank ranges can be returned; choose fewer
  pages if that limit is exceeded. Quiz question-count/grounding limits still apply.

## Verification and remaining work

Tests create synthetic in-memory PDFs and verify physical-page offsets against
upload extraction, blank-page handling, exact page-2 quiz sources excluding page 1,
cross-page chapter clipping, invalid ranges/types, missing/corrupt/changed storage,
owner denial and read-only selection behavior. No AI requests are required.

On 2026-09-03 the full backend suite passed **250 tests, with 1 existing Windows
symlink-privilege test skipped** and the existing Starlette/httpx warning. After
adding the cross-page chapter test, all eight focused PDF-page tests passed.

The PDF skill's rendering check was also applied to a separate ReportLab fixture
created by `scripts/create-pdf-page-fixture.py` in `artifacts/tmp/pdfs/`.
Poppler reported three physical pages; all three rendered PNGs were inspected:
Cells on page 1, Plants on page 2, and an intentionally blank page 3. Text was
legible and unclipped. Poppler emitted missing Symbol/ArialUnicode display-font
warnings, but the fixture uses Helvetica and its rendered text was intact.
The page index returned `[true, true, false]` text flags, and selecting page 2
mapped only to `chapter-2`, characters 288–591. This is synthetic QA, not a learner
document or a visual PDF viewer delivered in the app.

Android page-range controls and confirmation are now wired as described below.
Persistence/recovery device QA, complex-layout PDFs, scanned-material support, accessibility and user
acceptance remain open. The PDF is re-read on each request; safe cache/index
persistence is not implemented. DOC-02 and production gates remain partial.

## Android page API validation layer

Android now has typed page-index and page-scope models plus API methods for both
routes, now connected to the page controls described below. Before accepting
an index, the client checks document identity, 1-based sequential pages, upload's
inter-page newline offsets, size limits and consistency of nonempty-page flags.
Page inputs reject noninteger/out-of-bounds/reversed values.

Before accepting a resolved scope, Android checks the requested document/pages,
exact empty-page report, known chapter IDs, canonical disjoint excerpt ranges,
range containment within the requested pages and at least one intersecting range
for every selected page marked as containing text. These checks detect malformed
responses but do not independently prove full text coverage: the server's verified
extraction and gap checks remain authoritative for that.

Debug build/lint and **91 JVM tests** passed, including six new page-validation
tests. No live API calls or PDF artifact changes occurred in this Android slice.
This was API-layer evidence only; the subsequent UI slice is recorded below.

## Android review and confirmation

PDF documents now show an explicit Load original PDF page index action, inclusive
first/last physical-page inputs, and a Review original page range action. Review
shows chapter titles, exact source offsets and empty-page warnings; it does not
change the current selection. Confirmation explicitly replaces whole-chapter or
existing excerpt selections with the reviewed ranges, saving chapter IDs and
encoded offsets in one account-scoped preferences commit through the existing
excerpt recovery workflow. No source text or API key is saved with this selection.

Editing either input invalidates the review. Confirmation revalidates the current
document, requested pages, chapter IDs and source bounds. Document changes, chapter
selection, structure repair, deletion, quiz creation and sign-out clear the draft.
Failed index/review requests leave the prior confirmed selection untouched and
allow retry through the same actions. Unconfirmed input/review state is ephemeral;
confirmed source offsets persist, not physical-page label metadata.

Debug build, lint and **93 JVM tests** passed after wiring the UI. Tests cover
confirmation with stale/missing reviews, changed document/chapter identity,
encoded-range round trips and deletion isolation. Subsequent device evidence is
recorded below; page-endpoint network retry, accessibility and actual UAT remain open.
This is not a visual PDF viewer and does not implement OCR or printed page labels.

## Device QA fixture and admission limits

`scripts/qa-document-recovery.ps1 -ResetTestAppData -VerifyCreationRetry -VerifyPdfPages`
uses the synthetic `artifacts/tmp/pdfs/page-boundary-fixture.pdf`, produced by
`scripts/create-pdf-page-fixture.py`, on the dedicated LearnSmart_API36 emulator
with the isolated `backend/scripts/serve_qa.py --qa-only` backend. It never calls
the live provider. The script refuses missing fixtures or incompatible source modes.

The first device run verified range review and restart persistence but stopped
before the lost-response check: it requested ten questions from five source
sentences, correctly receiving 422 before quiz creation. The test now checks that
admission failure and explicitly selects five questions through Android before
testing the injected creation-response failure. It does not expand the source
scope or weaken distinct-question validation to obtain a pass.

Usability gap observed in that QA run: Android intentionally suppresses arbitrary server error bodies
to avoid exposing sensitive validation data, but its generic 422 message does not
explain insufficient material or blank-only page selections. Safe structured error
codes with actionable, client-owned messages are now implemented in
`document-error-codes.md`; their updated device checks remain pending.

The full backend regression suite passed **251 tests, 1 Windows symlink-privilege
test skipped**, with the existing Starlette/httpx deprecation warning on 2026-09-03.

The corrected API 36 run completed successfully against Android implementation
`8f11cba` on 2026-09-03:

- The Android picker uploaded the three-page PDF; chapter/empty selections survived
  restart, and generation was disabled for an empty selection.
- Page 3 alone returned validation failure without modifying saved selection;
  out-of-bounds input disabled review. Pages 2–3 displayed the blank-page warning.
- After editing and reviewing pages 2–2, the displayed Plants range was 288–591.
  Review left preferences unchanged; explicit confirmation saved this scope and
  process restart restored it as one excerpt.
- Ten-question generation was rejected without changing that range; choosing five
  through Android persisted. The simulated post-commit 503 retained the pending
  creation identity through restart. Retry recovered exactly one quiz, with the
  same source range and no remaining pending selection metadata.
- Conflicting-answer recovery preserved the committed answer. All five questions
  referenced the confirmed page-2 range; remaining answers were submitted through
  the API fixture, then Android restarted into completed results.

The review, restored excerpt and resumed-question screenshots were visually
inspected: displayed text and source boundaries were legible. Uiautomator emitted
transient null-root warnings; existing fresh-dump retries recovered and the script
exited zero. This does not verify complex PDFs, multi-range page scopes on device,
page-endpoint network failures, account switching, large-text/TalkBack behavior,
live generation quality or UAT. Physical-page metadata still is not persisted
separately from exact source offsets. DOC-02 and production remain partial.
