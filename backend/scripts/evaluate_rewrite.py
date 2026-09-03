"""Explicit opt-in live smoke evaluation; uses synthetic learner answers only.

Run from backend: uv run python scripts/evaluate_rewrite.py --live
Exit 1 if any score misses its expected range. Not a calibrated quality benchmark.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.mastery_service import FRACTION_DIAGNOSTIC
from app.tutor_provider import OpenAITutorProvider


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Authorize metered OpenAI calls for these synthetic cases")
    args = parser.parse_args()
    if not args.live:
        parser.error("Use --live to explicitly enable paid provider requests")
    settings = get_settings()
    if not settings.openai_api_key:
        raise SystemExit("No server API key configured")
    cases = json.loads((Path(__file__).resolve().parents[1] / "evals/rewrite-fractions.json").read_text(encoding="utf-8"))

    def evaluate(case):
        try:
            provider = OpenAITutorProvider(settings.openai_api_key, settings.openai_model)
            assessment = provider.assess_rewrite(8, FRACTION_DIAGNOSTIC[0], case["response"])
            passed = assessment.score is not None and case["min_score"] <= assessment.score <= case["max_score"]
            return {"id": case["id"], "passed": passed, "score": assessment.score, "feedback": assessment.feedback}
        except Exception as error:
            # Do not print provider exceptions: they may contain request details.
            return {"id": case["id"], "passed": False, "error_type": type(error).__name__}

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(evaluate, cases))
    print(json.dumps({"model": settings.openai_model, "passed": sum(r["passed"] for r in results), "total": len(results), "results": results}, indent=2))
    return 0 if all(result["passed"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
