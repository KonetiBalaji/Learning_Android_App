# Find literal topic text in selected source

`POST /v1/documents/{document_id}/search` is an authenticated, owner-scoped,
read-only source lookup. It does not invoke a provider, generate questions, save
search history or change document/quiz state. The request body keeps query text
out of ordinary URL/access-log paths, though production body logging must still
be configured not to capture learner queries.

```json
{
  "chapter_ids": ["chapter-1"],
  "query": "photosynthesis",
  "limit": 20
}
```

Chapter IDs are required and validated in full before searching. Unknown,
duplicate, empty, overlapping or invalid stored selections fail instead of being
silently dropped. Search never extends into an unselected chapter. No credentials
returns 401; another owner's or missing document returns 404; invalid input 422.

The trimmed query must contain 2–120 Unicode code points without control
characters. Matching is literal and case-insensitive using Python regular
expression case handling; punctuation is escaped, not interpreted as a pattern.
Internal whitespace is literal. It is **not semantic search**, stemming, synonym
expansion, spelling correction, OCR or an authoritative topic/curriculum index.
For example, zero matches for a topic's name do not prove the document lacks
related explanations. An empty result never falls back to the whole document.

## Response

The response contains `document_id`, trimmed `query`,
`match_mode: "literal_case_insensitive"`, `matches` and `has_more`.
Each hit contains:

- `chapter_id`, `title`: the stored chapter identity, not generated labels.
- `start_character`, `end_character`, `text`: the exact bounded source passage.
- `match_start`, `match_end`: a representative matching phrase within that passage.
- `context_truncated`: whether the 2,000-code-point context limit cuts a source
  line/paragraph at either edge.

Offsets are absolute Unicode code points, start-inclusive and end-exclusive.
The algorithm prefers the source line/paragraph containing a match, with at most
300 preceding characters when the paragraph is long, and caps each result at
2,000 characters. Results follow source order, not a relevance score. Matches
already covered by a returned passage are not repeated. A phrase straddling the
previous context boundary is retained in full; those adjacent result contexts
can overlap slightly and must not be blindly combined into an excerpt selection.

The limit is 1–20 passages (default 20), not a count of occurrences. `has_more`
means another result passage exists beyond the limit, not an estimated total.
Refine the phrase or chapter selection to narrow results; pagination is not yet
implemented. Returned ranges can be explicitly reviewed and submitted through
the existing `source_ranges` quiz contract. Overlap/insufficient-material checks
still apply; search alone never selects text or broadens quiz scope.

## Verification and remaining work

Tests verify selected-chapter isolation, exact Unicode snippets and match offsets,
literal metacharacters, zero-result behavior, result limits, long/truncated
paragraphs, boundary-straddling matches, invalid input, owner denial, no persisted
quiz changes, and compatibility with explicit excerpt selection. Generation is
replaced with failing test doubles to ensure it is not called.

On 2026-09-03, `uv run pytest -q` passed: **243 passed, 1 skipped**
(the existing Windows symlink-privilege test), with the existing Starlette/httpx
deprecation warning. No live provider calls or Android changes were made in this
backend slice.

Android query/results controls, explicit result confirmation, restart/failure and
accessibility QA remain to be implemented. This endpoint advances source lookup
for topic selection but does not complete the original DOC-02 topic/page/section
workflow, semantic relevance evaluation, UAT or production acceptance.
