# Cross-subject written-explanation evaluation

The live rewrite evaluation now combines the original eight like-fractions cases
with twelve held-out cases covering Grade 8 Science (nucleus and DNA), English
(sentence subjects) and Social Geography (Equator and latitude). The added set
includes correct applied explanations, correct concepts without application,
fundamental misconceptions, keyword lists, irrelevant text, contradictions and
instruction injection. Every case has a predeclared acceptable 0–4 score range.

On 2026-09-04, `scripts/evaluate_rewrite.py --live` used the existing server-side
OpenAI credential and `gpt-5-mini`. The first 20/20 scoring run exposed that
full-credit model comments could add facts or guidance outside the supplied lesson.
No score expectation was weakened. Learner-visible feedback is now server-owned at
every score: fixed actionable hints for 0–3 and a concise grounded confirmation for
4. A second live run passed all 20/20 score ranges and verified the fixed full-credit
message for every score-4 case.

The evaluation uses synthetic text only, sends no learner or account data, requests
no response storage, and prints no credential. Unit tests reject malformed scores,
separate untrusted learner instructions from the rubric, and prove neither incomplete
nor full-credit model comments can reach the learner.

## Deterministic-mode false-credit repair (2026-09-05)

The fallback grader previously accepted any response of at least eight words that
contained one long word from a non-Fractions concept. That generic overlap was not
evidence of understanding and could advance a deterministic development session.
Non-Fractions rewrites now fail closed as assessment unavailable unless the strict
provider rubric runs. The three explicitly curated Fractions concepts retain separate
offline checks for concept and method evidence: addition, equivalence, and subtraction.

Focused provider/mastery/grading QA passed 81 tests. An authenticated Cells journey
proves a long response repeating the concept receives 503, remains in rewrite, writes
no rewrite attempt, and cannot advance mastery. Positive and repetition-negative cases
cover all three curated Fractions rubrics. Production already requires OpenAI mode;
this repair protects deterministic development and test operation without treating
keyword overlap as mastery.

This is a small regression and false-pass screen, not statistical calibration. It
does not establish curriculum correctness, multilingual grading, fairness, educator
approval, physical-device behavior or UAT. Those remain separate acceptance gates.
