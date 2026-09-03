# Document source preview

`GET /v1/documents/{document_id}/chapters/{chapter_id}/preview?page=0`
requires the document owner's bearer token. It is read-only and invokes no AI.

Response: `document_id`, `chapter_id`, `title`, zero-based `page`, `total_pages`,
absolute `start_character`, exclusive `end_character`, and verbatim `text`.
Each part contains at most 2,000 Unicode code points from the stored chapter
range. Concatenating all parts reconstructs that range exactly, including
whitespace. Parts are text chunks, not original PDF pages. Adjacent chapters are
not included. Original file layout and images are not rendered.

Missing/other-owned/deleted document or missing chapter: 404. Missing/invalid
authentication: 401. Negative/out-of-range page or invalid source bounds: 422.
The selected range and duplicate IDs are validated before slicing source text.

Android provides a separate preview action for each chapter and recovered range.
Previous/next controls fetch one part at a time; previewing never changes selected
IDs, quiz settings or pending creation identity. Client decoding checks response
identity, requested part, page count and Unicode character length against offsets.
Failed navigation retains the prior screen/part and uses the normal error dialog.
Preview text is not stored in preferences; process recreation restores chapter
selection, not the preview position. Reopening another document or deleting the
active document clears the in-memory preview. Sign-out clears application state.

Verification: 175 backend tests, Android build/lint and 63 JVM tests passed.
Tests include exact multi-part Unicode source reconstruction, boundary isolation,
ownership, deleted documents, invalid pages and malformed client payloads.
On-device pagination, offline retry and large-font/accessibility checks remain
pending. This endpoint does not implement PDF page-range quiz selection.
