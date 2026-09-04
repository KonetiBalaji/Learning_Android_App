# Find a topic or exact phrase in selected source

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
characters. Search first tries the complete phrase, case-insensitively; punctuation
is escaped rather than interpreted as a pattern and internal whitespace is literal.
If no exact phrase exists, a bounded topic-query fallback removes a small documented
set of English question/connector words and requires **every** remaining distinct
term (up to eight) as a whole word in one source passage, in any order. It never
returns a passage for only some terms and never falls back to the whole document.
It is **not semantic search**, stemming, synonym expansion, spelling correction,
OCR or an authoritative topic/curriculum index. A zero result therefore does not
prove the document lacks a related explanation.

## Response

The response contains `document_id`, trimmed `query`, `matches`, `has_more`, and
`match_mode`, which is `literal_case_insensitive` or
`all_query_terms_case_insensitive`.
Each hit contains:

- `chapter_id`, `title`: the stored chapter identity, not generated labels.
- `start_character`, `end_character`, `text`: the exact bounded source passage.
- `match_start`, `match_end`: the complete phrase, or the span from the first to
  last required topic term, within that passage.
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

## Android query and explicit result selection

The chapter screen now includes **Find a topic or phrase**, a query field and **Search
selected chapters**. Search is disabled for empty chapter selection or invalid
query lengths. The screen explains exact-phrase priority, all-important-term
fallback and that synonyms are not inferred. It searches the whole checked chapters
even when existing quiz selection is in excerpt mode. Search does not automatically
change that selection.

Results show full bounded source passages, chapter names, absolute character
ranges and truncation warnings. Zero matches and additional-result limits have
explicit messages. **Use passage N as excerpt** is the confirmation action: it
replaces whole-chapter selection for the first excerpt or adds to existing
excerpts, using the same overlap rejection and atomic preference save as manual
highlight selection. After confirmation, the result list and query clear and the
screen shows the saved excerpt scope. A passage may still contain insufficient
information for the configured quiz count; selection does not bypass generation
quality/quantity validation.

Android validates document/query/match mode, checked chapter membership, result
count/order, exact Unicode text/range lengths and complete match bounds. It verifies
the exact phrase or every retained topic term inside the reported match span before
accepting results. Confirmation additionally checks that
document, query and selected chapters have not changed. Query/chapter edits and
structure repair invalidate results. Account changes, document deletion/opening,
quiz acceptance/resume and starting another document clear applicable in-memory
query/results. Neither queries nor result passages are stored in preferences;
only explicitly confirmed excerpt IDs/bounds use the existing durable contract.
Unconfirmed searches are not restored after process death.

On 2026-09-03, Android debug build/lint and **85 JVM tests** passed, including seven
new search tests for Unicode matches, query validation, malformed/mismatched
responses, empty/limited results, stale confirmation and deletion cleanup. No live
AI calls were made. Emulator search/confirmation, restart/failure/account-switch,
large-text/TalkBack usability and UAT remain unverified for this new UI. This is
not completion of semantic topic retrieval, PDF page selection or DOC-02 overall.

## API 36 source-search workflow evidence

`scripts/qa-document-recovery.ps1 -ResetTestAppData -VerifyCreationRetry
-VerifySourceSearch` passed on LearnSmart_API36 with APK source `330aa9f` and the
refreshed isolated scripted-QA backend. A no-match query displayed the explicit
empty state without changing chapter IDs or saving an excerpt. Android then
searched for `photosynthesis`, displayed the first Plants passage, and required
**Use passage 1 as excerpt** confirmation. The chosen source range was **324–927**;
its boundaries matched the search API and survived force-stop/restart. The full
visible passage and confirmation label in `artifacts/qa-source-search.png` were
visually inspected. Queries were entered through Android, not by writing app state.

Injected HTTP 503 after committed creation left the request identity pending.
Restart/retry recovered exactly one original quiz with the chosen range and
cleared accepted pending metadata. All ten question references stayed within that
range. Conflict recovery, feedback restart and completed-results restoration
passed; remaining quiz answers were submitted through the API fixture, not all
through Android. Transient UI-dump failures recovered using fresh-dump retries.

This is one synthetic literal-search workflow with no live AI calls. The newer
multi-term topic-query path has backend and JVM coverage but still needs the same
API 36 workflow evidence. Multiple
results/additions, truncated contexts, invalid/malformed/offline responses,
account switching, query editing invalidation on-device, accessibility and user
UAT remain open. It does not verify semantic relevance or full topic coverage.

## Bounded custom-topic query implementation

On 2026-09-04, source lookup gained the all-important-term fallback documented
above. Exact phrase results remain preferred. Tests prove natural question-word
removal, term order independence, whole-word matching, selected-chapter isolation,
the 1,400-character required-term span, no partial-term fallback, exact source
offsets, API ownership/read-only behavior and compatibility with explicit excerpt
selection. Android accepts only the two declared modes and independently requires
every retained topic term inside the reported match span before displaying it.

The complete backend suite passed **531 tests with one Windows symlink-privilege
skip**. Android passed **142 JVM tests**, lint and debug APK assembly. This is
implementation and automated contract evidence; the multi-term path still needs
API 36 interaction evidence, accessibility checks and UAT. Synonyms and semantic
relevance are deliberately not claimed.
