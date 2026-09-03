# Live interest-example evaluation

Date: 2026-09-03. Provider model: `gpt-5-mini`. Existing server key reused
with the user's approval; no secret was changed, printed or committed.
Only synthetic Grade 8 fraction questions were sent. Nine metered requests
were made in three batches of three, with no SDK retries or scripted fallback.

Reproduce from `backend`: `uv run python scripts/evaluate_interests.py --live`.
Without `--live`, the script refuses to call the provider. It prints the model,
lessons and contract results, not credentials or raw exception messages.
Exit zero means all three responses parsed and retained the original practice
question, NOT that semantic quality passed. Review the actual lesson text.

## Review criteria

Check explanation, example and hint for mathematical correctness; a consistent
whole, equal parts and units; relevant but optional interest framing; neutral,
age-appropriate language; no invented learner traits; and unchanged practice.
This review was performed by the development agent, not a teacher or user.

## Findings and corrections

All nine responses preserved the practice question, but the first two batches
failed semantic review. This demonstrates why schema/contract success alone
cannot establish teaching quality.

Initial batch: sports addition had correct arithmetic but opened with
"You added wrong." Music equivalence had correct arithmetic but a strained
six-beat song scenario. Nature subtraction mixed garden area and picked flowers,
leaving the removed quantity ambiguous. Guidance was expanded to require neutral
next-step feedback, no assumed error process, consistent units and explicit parts.

Second batch: tone and the flower-bed example improved. However, music equated a
whole note with one beat without context, and subtraction called sixteenths
"a different whole." Both were rejected. Guidance now distinguishes part size
from the whole and uses listening duration rather than unsupported music theory.

Final batch (three responses):

| Case | Observed example | Review |
| --- | --- | --- |
| Sports / addition | 3/4 hour of practice plus 1/4 hour equals 1 hour | Correct units, arithmetic and neutral feedback |
| Music / equivalence | A six-minute song: half is 3/6; one third is 2/6 | Explicit equal one-minute parts, correct equivalence |
| Nature / subtraction | One birdseed packet divided into eight equal scoops: five minus one leaves four | Consistent whole and parts; correctly explains changed denominator as changed part size |

All three final explanations and hints were correct in this review and retained
the server-owned practice prompts. Examples are concise and understandable for
foundational Grade 8 remediation; they do not prove Grade 8 curriculum coverage.

## Automated checks and limits

88 backend tests passed after the first prompt refinement; the three interest
tests passed again after the final refinement. Prompt regression assertions cover
neutral wording, no assumed error mechanism, whole/part distinction, consistent
units and avoiding unsupported music definitions. Script help and refusal without
`--live` were exercised without provider calls. No Android code changed.

These are three reused cases, not an independent holdout or statistical safety
evaluation. Prompt changes reduce observed failures but do not enforce semantic
correctness at runtime. Broader subjects, ages, interests, combinations, repeated
runs, adversarial content and educator review remain needed. Saved lessons are
not rewritten. TUT-03 remains partial; no UAT or production sign-off is claimed.
