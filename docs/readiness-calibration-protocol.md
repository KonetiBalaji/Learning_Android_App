# Grade 8 readiness calibration protocol

The current learner and guardian screens show an **uncalibrated learning
indicator**, not an exam prediction. `readiness_is_calibrated` must remain false
until this protocol is completed for the exact curriculum catalog and target
outcome.

## Candidate public sources

- NCES NAEP publishes released Grade 8 questions, national/state performance
  tools and technical documentation. Some person-level secondary-analysis files
  are restricted-use, so released aggregate results alone cannot calibrate an
  individual app score.
- The TIMSS & PIRLS International Study Center publishes public-use Grade 8
  mathematics/science achievement and context databases. Those data still need
  test-curriculum matching and do not cover this app's English and Social Studies
  launch content by themselves.

These sources are candidates, not approvals. Their achievement levels must not
be relabeled as this application's exam readiness without a documented target,
curriculum match and qualified review.

## Required evidence

1. Name the country/board or explicitly approve an international benchmark.
2. Freeze the exact Grade 8 catalog version and map every evaluated concept to
   the external assessment framework. Record exclusions.
3. Define one binary target outcome before analysis. Do not tune the target after
   seeing results.
4. Collect consented, de-identified app predictions paired with that outcome.
   Synthetic learners and the training/tuning split are prohibited.
5. Reserve at least 100 unique learners as an untouched holdout containing both
   outcome classes. Larger, representative samples are normally required before
   a production claim.
6. Run from `backend`:

   `uv run python -m app.readiness_calibration HOLDOUT.csv --output REPORT.json`

7. Review Brier score, calibration-in-the-large, expected calibration error,
   every bin, subgroup coverage, uncertainty and drift with an educator and a
   qualified measurement/statistics reviewer. The evaluator intentionally emits
   `claim_status: REVIEW_REQUIRED`; it cannot approve itself.
8. Record reviewer identity, dated approval, dataset/version/hash, target,
   exclusions and acceptable operating thresholds in a separate signed release
   artifact. Only a later reviewed implementation may consume that artifact.

The holdout CSV contains exactly:

`learner_id,predicted_probability,outcome,split`

`learner_id` must be a de-identified unique study identifier; prediction is from
0 to 1; outcome is 0 or 1; and every accepted row must be marked `holdout`.
