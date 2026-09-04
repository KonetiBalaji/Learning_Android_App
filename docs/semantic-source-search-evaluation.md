# Semantic source-search evaluation

Status: implemented, automated QA complete, and one bounded live-provider check
passed. Android device verification, broad relevance evaluation and UAT remain open.

When exact-phrase and all-important-term lookup both return zero results, OpenAI
mode now performs a quota-counted embedding lookup over deterministic passages from
only the selected chapters. The provider receives the trimmed query and at most
80,000 selected source characters split into at most 1,600-character passages.
It does not choose offsets, rewrite text, select an excerpt or create a quiz.

Automated tests cover synonymous ranking without lexical overlap, selected-chapter
isolation, exact Unicode source-range reconstruction, fixed provider model/options,
oversized-scope rejection before a provider call, and count, dimension, zero-vector
and non-finite-vector failures. HTTP coverage proves exact hits remain provider-free,
one semantic miss consumes exactly one owner/day AI operation, no quiz is created,
and the explicit `semantic_embedding` mode is returned. Android accepts only the
three declared modes, requires semantic match bounds to cover the complete verbatim
passage, rejects malformed bounds/modes, and tells learners to verify relevance
before selecting a result.

On 2026-09-04, a live `text-embedding-3-small` check used only synthetic text. The
query `automobile occupant protection` did not occur in either candidate. Retrieval
selected the safety passage describing cars, seat belts, crumple zones, collisions
and injury, while excluding a plant/chlorophyll/energy distractor. The returned
passage exactly matched its stored source offsets. No API key, vector, similarity
score, learner content or raw provider response was printed or retained.

This single controlled pair is not a statistical relevance benchmark, multilingual
or spelling evaluation, curriculum review, device-network recovery test, educator
approval or user acceptance. The fixed similarity threshold must remain subject to
broader labeled evaluation before production acceptance.
