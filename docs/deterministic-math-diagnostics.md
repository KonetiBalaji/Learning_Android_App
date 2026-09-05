# Grade 8 Mathematics diagnostic fallback

Status: implemented and automated-QA verified; curriculum authority and UAT remain
open.

The app-owned fallback now contains three diagnostic items for every current Grade 8
Mathematics chapter: Fractions, Decimals, Percentages, Algebra and Geometry. Each item
has four unique choices, one exact correct choice, a concept-specific explanation,
self-contained worked example, non-answer-revealing hint and one objective text-field
practice answer. Numeric equivalence is enabled only on explicitly curated items;
format- or unit-constrained practice remains exact.

When configured OpenAI generation times out or fails independent review, the resilient
provider may use the matching trusted Mathematics bank. Stored items from these banks
also keep app-owned teaching available during a later provider outage. Unsupported
chapters do not receive a misleading Mathematics fallback and remain retryably
unavailable.

Focused verification on 2026-09-05 passed 21 provider/catalog tests. It validates all
five banks, outage fallback and teaching behavior, unsupported-chapter failure, and
authenticated HTTP creation without provider credentials for the four non-gated
starting chapters. Geometry remains governed by its Algebra mastery prerequisite.

These are curriculum-neutral foundation questions written for product continuity.
They have not been approved against a named board, reviewed by an educator, or accepted
by the user, and they do not replace live-generation quality evaluation.
