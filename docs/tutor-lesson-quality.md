# Tutor lesson quality gate

Generated learner-visible remediation now requires a second structured review
before delivery. The reviewer independently compares the proposed explanation,
worked example and hint with the verified question, correct answer, method and
example. It fails closed on inaccurate reasoning, method drift, invalid examples,
grade mismatch, concept drift, shaming or assumed learner reasoning, weak hints,
unsupported facts, or claims not directly entailed by the verified evidence.
All supplied fields are treated as untrusted data and response storage is disabled.

If generation, parsing or review fails, curated Fractions content can be used
locally. Provider-generated diagnostic items can reach storage only
after the blind diagnostic audit independently solves their questions and practice
prompts and approves every explanation, example and hint for accuracy, grade fit,
concept match and source-boundedness. Thus fallback does not turn unchecked generated
teaching into learner-visible content. For a legacy generated session that predates
this gate, stored teaching support must pass a fresh provider review at delivery.
If that review is rejected or unavailable, the wrong answer is not committed and
the API returns a safe retryable `503`; it never silently exposes unchecked fallback.

## Verification on 2026-09-04

Nine strict review dimensions have individual rejection tests. Malformed or extra
review fields fail validation; safe logs contain fixed codes rather than lesson or
provider text. Tests also cover accepted and unavailable legacy fallback plus HTTP
state preservation. The complete backend suite passed 494 tests with one existing
Windows privilege skip.

Three bounded `gpt-5-mini` cross-subject runs used the existing approved server key
without printing or committing it. Each four-case run used one generation and one
review request per case. The initial reviewer allowed an unsupported Science claim
about squirrel muscle cells, so development review rejected that batch. A separate
`source_bounded` decision was added. The next run rejected all four rather than
allowing uncertain elaboration. Generation was then limited to facts entailed by the
verified method/example and optional neutral relabeling.

In the final run, Math linear equations, English complete subjects and Geography
reference lines passed the runtime gate and development review. Science again added
an unsupported muscle-cell claim and was correctly rejected with fixed codes; the
runtime would deliver reviewed diagnostic support (or keep the answer retryable if
that support came from an unreviewed legacy session and could not be checked). This
is a successful safety result, not a 4/4 generation-quality claim.

The expanded blind diagnostic smoke then generated three Grade 8 Fractions items.
All answers, practice keys, explanations, examples and hints passed the gate and
manual arithmetic review. A deliberately corrupted key was rejected at item 0.

Reproduce from `backend` with `python scripts/evaluate_tutor_lessons.py --live`
and `python scripts/evaluate_diagnostic.py --live`. Both refuse metered work without
`--live`. Limits remain: generator and reviewer use the same model family, four
held-out topics and one generated bank are not statistical calibration, Grade 8 does
not cover Grades 1–12, and no educator or user approved the wording. TUT-01 is QA
verified for the enforced runtime contract, not UAT accepted or curriculum certified.
