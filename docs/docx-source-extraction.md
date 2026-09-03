# DOCX body and table extraction

The previous extractor read `document.paragraphs` only, silently omitting tables.
New uploads now traverse body paragraphs and tables in document order, including
paragraphs and nested tables inside cells. Paragraph-only separator behavior is
preserved. Table cells are separated with tabs and rows with newlines; ordinary
paragraph text is not rewritten. Horizontally and vertically merged cells contribute
their text once, with blank positions for repeated layout cells, rather than
duplicating evidence. This is linearized source text, not an exact layout model.

Processing rejects, rather than truncates, excessive content: eight nested table
levels, 20,000 cumulative occupied cell positions and at most two million output
characters. Span values are bounded before expanding merged cells. Existing ZIP
member/count/size/ratio/CRC admission checks still run before parsing. These limits
bound this traversal but do not replace process-isolated XML parsing or serving
resource limits. The project now requires python-docx 1.2+, matching the existing
locked 1.2.0 installation and its document-order traversal API.

Source offsets refer to the stored extracted text, including tab/newline
separators, not to Word pages or XML byte positions. Old documents are not
re-extracted or migrated: doing so would invalidate saved quiz/excerpt offsets.
Users must upload a new copy to include tables omitted by the old extractor.

## Remaining limitations

Headers, footers, floating text boxes, revision-mark containers, images, OCR and
equation semantics are not added here. Omitted grid cells and complex merged-table
relationships are not fully modeled; linear text can lose visual associations.
The source-preview and quality-review gates still matter, and the feature must not
be described as complete fidelity for arbitrary textbooks. Android visual table
preview, on-device DOCX upload recovery, real model quality on tables and UAT
remain open. No new AI request or API-key change was needed for this correction.

## Verification

Eight focused tests cover paragraph compatibility, body order, table row/cell
order, nested-cell order, horizontal/vertical merging, rejection limits and a
table-only DOCX upload/search round trip. The latter checks search text and match
positions against the database's extracted source. Fixtures are generated entirely
in memory inside the tests; no user documents are used or changed.

On 2026-09-03 all eight focused tests and the full backend suite passed:
**285 passed, 1 existing Windows symlink-privilege skip**, with the existing
Starlette/httpx warning. This is backend extraction/search evidence, not device,
AI-output-quality or user-acceptance evidence.

References: python-docx's [document API](https://python-docx.readthedocs.io/en/latest/api/document.html)
and [table guide](https://python-docx.readthedocs.io/en/latest/user/tables.html)
describe ordered traversal and the complications of merged and nested cells.
