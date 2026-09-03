# Grade 8 diagnostic live smoke, 2026-09-03

Command: `uv run python scripts/evaluate_diagnostic.py --live`

Used the existing approved server key and configured `gpt-5-mini` model. No key
was printed or changed. The runner allowed at most three metered requests with
retries disabled: generate a Fractions bank, independently review it, then review
a known bank with a deliberately corrupted answer key. No learner data or database
session was created. The generated bank was returned in tool output for inspection.

## Observations

The generated/reviewed bank passed in 26.50 seconds; the corrupted-key check was
rejected by a complete parsed review in 5.85 seconds. The negative case changed
the answer to `3/4 + 1/4` from `1` to `3/8`, leaving its valid structure intact.
Timeouts and malformed responses are explicitly failures, not successful rejection.

| Sampled question | Returned answer | Arithmetic inspection |
| --- | --- | --- |
| Simplify 42/56 | 3/4 | Both divide by 14 |
| 2/3 + 1/4 | 11/12 | 8/12 + 3/12 |
| Largest of 5/8, 3/5, 7/12, 4/7 | 5/8 | 0.625 exceeds the other values |

The practice answers were also checked with exact rational arithmetic: 36/48 =
3/4, 3/4 + 2/5 = 23/20, and 3/4 > 7/10. The returned explanations were consistent
with those calculations. A wording refinement remains: the simplification item
would be clearer if it explicitly requested "lowest terms", since two distractors
were equivalent but unreduced fractions. The smoke's model-pass flag is not a
claim that every wording or teaching-quality concern has been resolved.

## Scope and limitations

This is one three-question bank and one intentionally wrong-key case, not a
false-pass rate, reproducibility study, broad subject evaluation, curriculum
validation or UAT. No parent/teacher reviewed it. Correct alternative practice
formats, hints, new coaching variants, account behavior and Android interaction
were not exercised. Existing practice-answer matching may not accept every
mathematically equivalent format; the arithmetic check is not a grading test.

The evaluator set generation timeout to 60 seconds with no retries, while the
production provider retains its 20-second request timeout and retry policy. The
review call retained its explicit 20-second timeout. These timings therefore do
not prove production latency or availability. Costs were not measured by the
runner. Future live runs require the explicit `--live` switch and use real credits.

Five added evaluator tests ensure outages/malformed output cannot count as correct
rejection and exceptions expose only their type. The final backend suite passed
**307 tests, 1 existing Windows symlink-privilege skip**, with the existing
Starlette/httpx warning. No Android code changed in this slice.
