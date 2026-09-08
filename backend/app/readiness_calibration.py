"""Evaluate an independent Grade 8 readiness holdout without enabling claims.

This module deliberately computes descriptive calibration evidence only.  Product
code must continue returning ``readiness_is_calibrated=False`` until a reviewed
report is approved for the exact curriculum catalog and target outcome.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path


class CalibrationDataError(ValueError):
    """Raised when a holdout cannot support an honest calibration review."""


@dataclass(frozen=True)
class Observation:
    learner_id: str
    predicted_probability: float
    outcome: int


def load_holdout(path: Path, *, minimum_learners: int = 100) -> list[Observation]:
    if minimum_learners < 2:
        raise CalibrationDataError("minimum_learners must be at least 2")
    try:
        with path.open(newline="", encoding="utf-8-sig") as source:
            reader = csv.DictReader(source)
            required = {"learner_id", "predicted_probability", "outcome", "split"}
            if set(reader.fieldnames or ()) != required:
                raise CalibrationDataError(
                    "holdout CSV must contain exactly learner_id, predicted_probability, outcome, split"
                )
            observations: list[Observation] = []
            seen: set[str] = set()
            for line, row in enumerate(reader, start=2):
                learner_id = row["learner_id"].strip()
                if not learner_id or learner_id in seen:
                    raise CalibrationDataError(f"line {line}: learner_id is empty or duplicated")
                if row["split"].strip().casefold() != "holdout":
                    raise CalibrationDataError(f"line {line}: only an untouched holdout split is accepted")
                try:
                    prediction = float(row["predicted_probability"])
                    outcome = int(row["outcome"])
                except ValueError as exc:
                    raise CalibrationDataError(f"line {line}: prediction/outcome is not numeric") from exc
                if not math.isfinite(prediction) or not 0 <= prediction <= 1:
                    raise CalibrationDataError(f"line {line}: prediction must be finite and between 0 and 1")
                if outcome not in {0, 1}:
                    raise CalibrationDataError(f"line {line}: outcome must be 0 or 1")
                seen.add(learner_id)
                observations.append(Observation(learner_id, prediction, outcome))
    except OSError as exc:
        raise CalibrationDataError("holdout CSV could not be read") from exc
    if len(observations) < minimum_learners:
        raise CalibrationDataError(
            f"holdout has {len(observations)} learners; at least {minimum_learners} are required"
        )
    if len({item.outcome for item in observations}) != 2:
        raise CalibrationDataError("holdout must contain both outcome classes")
    return observations


def evaluate(observations: list[Observation], *, bins: int = 10) -> dict[str, object]:
    if not observations:
        raise CalibrationDataError("holdout is empty")
    if bins < 2:
        raise CalibrationDataError("bins must be at least 2")
    count = len(observations)
    mean_prediction = sum(item.predicted_probability for item in observations) / count
    outcome_rate = sum(item.outcome for item in observations) / count
    brier = sum((item.predicted_probability - item.outcome) ** 2 for item in observations) / count
    buckets: list[dict[str, object]] = []
    weighted_gap = 0.0
    for index in range(bins):
        lower, upper = index / bins, (index + 1) / bins
        members = [item for item in observations if lower <= item.predicted_probability < upper
                   or index == bins - 1 and item.predicted_probability == 1]
        if not members:
            continue
        predicted = sum(item.predicted_probability for item in members) / len(members)
        observed = sum(item.outcome for item in members) / len(members)
        gap = abs(predicted - observed)
        weighted_gap += len(members) / count * gap
        buckets.append({
            "lower": lower, "upper": upper, "learners": len(members),
            "mean_prediction": round(predicted, 6), "outcome_rate": round(observed, 6),
            "absolute_gap": round(gap, 6),
        })
    return {
        "learners": count,
        "mean_prediction": round(mean_prediction, 6),
        "outcome_rate": round(outcome_rate, 6),
        "calibration_in_the_large": round(mean_prediction - outcome_rate, 6),
        "brier_score": round(brier, 6),
        "expected_calibration_error": round(weighted_gap, 6),
        "bins": buckets,
        "claim_status": "REVIEW_REQUIRED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("holdout", type=Path)
    parser.add_argument("--minimum-learners", type=int, default=100)
    parser.add_argument("--bins", type=int, default=10)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = evaluate(load_holdout(args.holdout, minimum_learners=args.minimum_learners), bins=args.bins)
    except CalibrationDataError as exc:
        parser.exit(2, f"Calibration evaluation failed: {exc}\n")
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
