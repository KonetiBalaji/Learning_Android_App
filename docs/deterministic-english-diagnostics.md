# Grade 8 English diagnostic fallback

Status: implemented and automated-QA verified; curriculum authority and UAT remain
open.

The app-owned fallback contains three diagnostic items for each current Grade 8
English chapter: Grammar, Reading Comprehension, Vocabulary, and Writing. Reading
questions carry their complete short passages in the prompt. Grammar and vocabulary
items use explicit sentence context. Writing items test objective topic-sentence,
transition, and concise-revision decisions.

When configured OpenAI generation times out or fails independent review, the resilient
provider uses only the matching trusted English bank. Stored fallback items keep their
app-owned explanation available during a later provider outage. Writing remains locked
until Vocabulary is mastered.

Focused verification on 2026-09-05 passed 86 provider, diagnostic-quality and catalog
tests. It covers validation and exact fallback for all four banks, outage teaching,
authenticated HTTP creation for the three ungated chapters, and retryable failure for
an as-yet uncurated Social Studies chapter.

The Writing diagnostic covers objective mechanics and organization only. It does not
replace the separate server-side four-point assessment of a learner's written
explanation. Further distinct practice after a failed guided attempt still requires
the reviewed provider path. These foundation questions are not mapped to a named
board, educator-approved, or user-accepted.
