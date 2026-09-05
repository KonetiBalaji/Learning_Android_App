# Semantic source-search evaluation

Status: implemented, automated QA complete, and bounded live-provider, multi-subject
synthetic holdout and API 36 emulator journeys passed. Curriculum-scale relevance,
physical-device QA and UAT remain open.

When exact-phrase and all-important-term lookup both return zero results, OpenAI
mode now performs a quota-counted embedding lookup over deterministic passages from
only the selected chapters. The provider receives the trimmed query and at most
80,000 selected source characters split on paragraph/sentence boundaries into at
most 800-character passages, with a 256-passage admission ceiling.
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

The API 36 journey then uploaded the disposable Biology fixture through Android,
selected only Chapter 2 Plants, and searched for `plant food production`. No exact
phrase or all-important-term span existed, so the live provider returned one
`semantic_embedding` passage. Android displayed the semantic warning, chapter
identity, exact source range and verbatim passage; the result and explicit **Use
passage 1 as excerpt** action were exposed in the TalkBack tree. The user-facing
action selected the passage, and the saved boundaries survived force-stop/restart.

The initial displayed passage also included unrelated fixture prose because the
earlier 1,600-character window crossed a blank-line topic boundary. Follow-up work
now treats blank lines as author-provided boundaries, splits overlong paragraphs at
sentence/word boundaries, caps inputs at 256 passages and uses a 0.25 cutoff. In a
live calibration check the focused Plants paragraph scored 0.336 while the three
unrelated fixture paragraphs scored 0.104–0.156. The repeated API 36 journey passed
and visual inspection confirmed that the result now ends at source character 927,
before the unrelated fixture paragraph. Complete paragraph candidates no longer
claim that their context was cut; only a paragraph actually split by the 800-character
limit carries that warning.

`uv run python scripts/evaluate_semantic_retrieval.py` provides a repeatable live
synthetic holdout without printing source passages, credentials, embeddings or raw
provider responses. The initial 0.30 threshold passed seven of eight positive cases:
`botanical nutrition production` still ranked the correct plant-energy passage far
above its distractors (0.257 versus 0.081) but was incorrectly suppressed. Four
unrelated-query controls scored only 0.097–0.121. At the revised 0.25 production
threshold, all eight positive cases across transport safety, plants, fractions,
urbanization, English adjectives, liquids, representative government and cell
energy passed, and all four negative controls remained rejected. Positive margins
ranged from 0.176 to 0.487.

This is a small authored English synthetic set, not a curriculum-derived benchmark.
It does not establish recall/precision for spelling errors, multilingual queries,
long textbooks, ambiguous topics or educator expectations. The threshold remains
subject to broader labeled evaluation and production monitoring.
