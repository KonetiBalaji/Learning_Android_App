# Grade 8 Science diagnostic fallback

Status: implemented and automated-QA verified; curriculum authority and UAT remain
open.

The app-owned fallback contains three diagnostic items for each current Grade 8
Science chapter: Cells and Living Things, Matter and Materials, Force and Motion,
and Ecosystems. Each item has four unique choices, one exact correct choice,
concept-specific teaching support and an objective text-field practice answer.

When configured OpenAI generation times out or fails independent review, the resilient
provider uses only the matching trusted Science bank. Stored fallback items keep their
app-owned explanation available during a later provider outage. No Science content is
substituted for another subject or chapter. Ecosystems remains locked until its Force
and Motion prerequisite is mastered.

Focused verification on 2026-09-05 passed 78 provider, diagnostic-quality and catalog
tests. It covers validation of all four banks, exact chapter fallback, teaching during
provider outage, authenticated HTTP creation for the three ungated chapters, matching
fallback after generated-content rejection, and retryable failure for an uncurated
English chapter.

The initial diagnostic, teaching, and first guided-practice content is locally
available. Additional materially distinct practice after a failed guided attempt still
requires the reviewed provider path; an outage cannot invent or approve new content.
These foundation questions are not mapped to a named board, educator-approved, or
user-accepted.
