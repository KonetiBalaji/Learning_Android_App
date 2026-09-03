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

Android page-range controls, explicit review/confirmation, persistence/recovery
device QA, complex-layout PDFs, scanned-material support, accessibility and user
acceptance remain open. The PDF is re-read on each request; safe cache/index
persistence is not implemented. DOC-02 and production gates remain partial.
