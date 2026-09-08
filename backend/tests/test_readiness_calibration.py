import csv

import pytest

from app.readiness_calibration import CalibrationDataError, evaluate, load_holdout


FIELDS = ["learner_id", "predicted_probability", "outcome", "split"]


def write_rows(path, rows):
    with path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def test_holdout_metrics_are_reproducible_and_remain_review_gated(tmp_path):
    path = tmp_path / "holdout.csv"
    write_rows(path, [
        {"learner_id": "a", "predicted_probability": "0.2", "outcome": "0", "split": "holdout"},
        {"learner_id": "b", "predicted_probability": "0.4", "outcome": "0", "split": "holdout"},
        {"learner_id": "c", "predicted_probability": "0.6", "outcome": "1", "split": "holdout"},
        {"learner_id": "d", "predicted_probability": "0.8", "outcome": "1", "split": "holdout"},
    ])
    result = evaluate(load_holdout(path, minimum_learners=4), bins=2)
    assert result == {
        "learners": 4,
        "mean_prediction": 0.5,
        "outcome_rate": 0.5,
        "calibration_in_the_large": 0.0,
        "brier_score": 0.1,
        "expected_calibration_error": 0.3,
        "bins": [
            {"lower": 0.0, "upper": 0.5, "learners": 2, "mean_prediction": 0.3,
             "outcome_rate": 0.0, "absolute_gap": 0.3},
            {"lower": 0.5, "upper": 1.0, "learners": 2, "mean_prediction": 0.7,
             "outcome_rate": 1.0, "absolute_gap": 0.3},
        ],
        "claim_status": "REVIEW_REQUIRED",
    }


@pytest.mark.parametrize("row, message", [
    ({"learner_id": "a", "predicted_probability": "1.1", "outcome": "1", "split": "holdout"}, "between 0 and 1"),
    ({"learner_id": "a", "predicted_probability": "0.5", "outcome": "2", "split": "holdout"}, "0 or 1"),
    ({"learner_id": "a", "predicted_probability": "0.5", "outcome": "1", "split": "training"}, "untouched holdout"),
])
def test_invalid_rows_fail_closed(tmp_path, row, message):
    path = tmp_path / "bad.csv"
    write_rows(path, [row, {"learner_id": "b", "predicted_probability": "0.2", "outcome": "0", "split": "holdout"}])
    with pytest.raises(CalibrationDataError, match=message):
        load_holdout(path, minimum_learners=2)


def test_duplicates_small_samples_and_one_class_fail_closed(tmp_path):
    path = tmp_path / "bad.csv"
    write_rows(path, [
        {"learner_id": "same", "predicted_probability": "0.1", "outcome": "0", "split": "holdout"},
        {"learner_id": "same", "predicted_probability": "0.9", "outcome": "1", "split": "holdout"},
    ])
    with pytest.raises(CalibrationDataError, match="duplicated"):
        load_holdout(path, minimum_learners=2)
    write_rows(path, [{"learner_id": "a", "predicted_probability": "0.1", "outcome": "0", "split": "holdout"}])
    with pytest.raises(CalibrationDataError, match="at least 2"):
        load_holdout(path, minimum_learners=2)
    write_rows(path, [
        {"learner_id": "a", "predicted_probability": "0.1", "outcome": "0", "split": "holdout"},
        {"learner_id": "b", "predicted_probability": "0.2", "outcome": "0", "split": "holdout"},
    ])
    with pytest.raises(CalibrationDataError, match="both outcome classes"):
        load_holdout(path, minimum_learners=2)
