# Guided practice answer matching

Practice grading now preserves operators, punctuation and word boundaries. The
previous normalization could turn `3+4` into `34` or `1 2` into `12`, incorrectly
accepting different answers. Matching remains case-insensitive, trims/collapses
whitespace, accepts spaces around `/`, and normalizes the Unicode minus sign.
It does not evaluate expressions or remove units/percent signs.

Each persisted diagnostic item has an `answer_mode`: `exact` (default) or
`number`. Explicit numeric mode compares exact rational values for bounded
integer, decimal, fraction and proper mixed-number literals. For example,
`1 3/20` equals `23/20`, and `9/12` equals `0.75`; no floating-point tolerance
or arbitrary expression evaluation is used. Numeric parsing is limited to 100
characters and 24 digits per component, with positive nonzero denominators.

Only trusted curated addition/subtraction practice and their arithmetic-generated
variants currently opt in. The requested-denominator exercise remains exact:
`4 / 6` is accepted but `2/3` is not. Legacy saved banks lacking the field remain
exact; their prompts/answers are not migrated or silently reinterpreted.

Generated diagnostic items remain exact and their provider schema cannot supply
this policy. Therefore the live-smoke generated question with answer `23/20`
still needs reviewed alternative answers or a validated format policy before
accepting `1 3/20`. The separate blind diagnostic review does not verify practice
keys, teaching text or answer-format constraints. Those remain open quality work;
this change is not universal mathematical grading or teacher UAT evidence.

Verification: backend regression tests cover false positives, rational literals,
requested formats, persistence/legacy compatibility, generated-policy rejection,
and HTTP practice transitions for accepted/rejected answers. Android code and
HTTP response shape are unchanged; on-device checking of this slice is pending.

Full backend verification: `uv run pytest -q --tb=short` passed 351 tests,
with one existing Windows symlink-privilege skip and the existing Starlette/httpx
deprecation warning. No additional live provider calls were made for this slice.
