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

Curated addition/subtraction practice and their arithmetic-generated variants
opt in. Newly generated banks can also opt in after independent practice review.
The requested-denominator exercise remains exact:
`4 / 6` is accepted but `2/3` is not. Legacy saved banks lacking the field remain
exact; their prompts/answers are not migrated or silently reinterpreted.

The generator cannot supply this policy. The blind reviewer independently solves
the practice prompt and specifies exact or numeric matching without seeing its
proposed answers. Every proposed answer must agree with the independent solution;
numeric solutions must also pass the bounded rational parser. Only then is the
policy persisted. Numeric `23/20` can therefore accept `1 3/20`, while a prompt
requiring lowest terms remains exact. This is model-based screening, not proof
that the reviewer understood every constraint. Same-model correlated errors,
false rejection of valid textual synonyms, teaching-text review and broader
human-reviewed evaluation remain open. Old sessions are not re-reviewed.

Verification: backend regression tests cover false positives, rational literals,
requested formats, persistence/legacy compatibility, generated-policy rejection,
and HTTP practice transitions for accepted/rejected answers. Android code and
HTTP response shape are unchanged; on-device checking of this slice is pending.

Full backend verification: `uv run pytest -q --tb=short` passed 351 tests,
with one existing Windows symlink-privilege skip and the existing Starlette/httpx
deprecation warning. No additional live provider calls were made for this slice.
