# Difficulty evaluation: incomplete

2026-09-03, `gpt-5-mini`, existing approved server key. Only the synthetic
water-tank exercise embedded in `backend/scripts/evaluate_difficulty.py` was sent.
Ten five-question generation attempts ran in three rounds, with at most twenty
metered requests including answer reviews. No SDK retries or QA fallback.

The script requires `--live`, accepts an optional `--levels` subset, and saves
timestamped synthetic results under `artifacts`. Its exit status measures existing
grounding/answer-check acceptance, NOT difficulty quality. Error diagnostics expose
only exception types and an allowlist of validation labels, never raw API errors.

## Observed results

1. Initial Easy/Medium/Hard/Mixed round: only Easy accepted. Its five questions
   correctly recalled explicitly stated volumes/rates. Other failures had no
   detailed diagnostic recorded; do not infer their exact causes.
2. Diagnostic Medium/Hard/Mixed round: all rejected with `Ungrounded quote`.
   Added explicit continuous-substring guidance, including intervening text for
   multi-fact questions. Exact quote validation was not loosened.
3. After quote guidance: all three batches passed exact-quote and blind-answer
   checks. Development-agent review found correct arithmetic in all fifteen
   accepted items, but difficulty quality did NOT pass:
   - Medium mainly used one-step division/subtraction; comparing all four tank
     emptying times was more demanding than the other items.
   - Hard included 15/2 and 12/6 one-step calculations, so most items did not
     establish a distinct multi-step demand.
   - Mixed contained recall and one-step calculations but no clear multi-step item.

The Medium longest-emptying-time question's reference covered only part of the
facts used in its explanation, although the full supplied source supported the
answer. Exact substring validation does not prove citation completeness for every
reasoning step. This remains a separate grounding-quality gap.

## Follow-up and fourth live round

Hard now explicitly requires at least two dependent reasoning steps. A per-item
plan supplies all-Hard demands for Hard or a balanced Easy/Medium/Hard sequence
for Mixed. Prompt instructions reject disguising single arithmetic operations as
Hard. These are guidance changes, not semantic enforcement or calibrated ratings.
The final demand-plan revision received a Hard/Mixed rerun on the same source:
two five-question batches, four metered requests including blind answer reviews.
Both batches passed existing checks, but semantic difficulty acceptance still
FAILED. This reused source is not an independent holdout.

- Hard: combining 60 + 90 litres, dividing by daily demand and finding a remainder
  adds linked operations, but the question does not explain how the tanks' stated
  continuous drainage is reconciled with supplying a garden over twelve days.
  Its intended arithmetic (12 days, 6 litres) is correct only with an unstated
  water-collection/use assumption. The blind reviewer missed this ambiguity.
- Hard: two gardens need 24 litres, requiring two full 15-litre buckets; this
  has a dependent demand-then-capacity calculation. Combining A/B into containers
  similarly yields 23 full containers and 2 litres by linked operations.
- Hard: comparing A/D emptying times repeats the same single division on each
  tank; it does not convincingly establish the required dependent-step demand.
  Dividing 100 litres into containers with a remainder is likewise too close to
  one division operation to establish distinct Hard quality.
- Mixed follows the requested Easy/Medium/Hard/Easy/Medium order nominally, but
  the third item asks how many gardens a full 15-litre bucket supplies. Its answer
  of one garden is a simple capacity comparison, not the required multi-step
  reasoning. The other four items fit direct recall or one-step application.
- All ten references contain the numeric facts used in the intended answers on
  manual inspection. This narrow observation does not resolve the earlier
  citation-completeness failure or prove semantic enforcement.

121 backend tests passed, including prompt fields, balanced plans for counts
5–20, persistence and legacy behavior. Script help was checked without API calls.
No production code changed for this fourth round. The 121-test result above is
from the preceding implementation turn, not a rerun for this documentation update.
Remaining: enforce/review actual demand and source assumptions rather than trust
requested labels, diverse/held-out material, independent educator review,
citation completeness and measured difficulty.
No UAT or production acceptance is claimed.

Local evidence files:

- `artifacts/difficulty-eval-20260903T082001884549Z.json`
- `artifacts/difficulty-eval-20260903T082110244688Z.json`
- `artifacts/difficulty-eval-20260903T082239652891Z.json`
- `artifacts/difficulty-eval-20260903T082901412293Z.json`
