# Grade 8 Social Studies diagnostic fallback

Status: implemented and automated-QA verified; curriculum authority and UAT remain
open.

The app-owned fallback contains three diagnostic items for each current Grade 8
Social Studies chapter: Geography, History, Civics, and Economics. Questions use
self-contained premises for map scale, chronology, cause and effect, government
roles, majority arithmetic, scarcity, opportunity cost, and budgets. The content does
not assume a particular country's constitution or historical syllabus.

When configured OpenAI generation times out or fails independent review, the resilient
provider uses only the matching trusted Social Studies bank. Stored fallback items keep
their app-owned explanation available during a later provider outage. Economics remains
locked until Civics is mastered.

Focused verification on 2026-09-05 passed 95 provider, diagnostic-quality and catalog
tests. It covers validation and exact fallback for every Social Studies bank, outage
teaching, authenticated HTTP creation for the three ungated chapters, rejection of an
unknown chapter, and a set-equality invariant proving that deterministic fallback keys
cover exactly all 17 chapters in the current catalog.

Further distinct practice after a failed guided attempt still requires the reviewed
provider path. These curriculum-neutral foundation questions are not mapped to a named
board, educator-approved, or user-accepted.
