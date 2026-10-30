"""Real local-embedding evaluation. No OpenAI call or API key is used."""
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend"))
from study.documents import structure
from study.semantic import build_index, search

specification = json.loads((root / "shared/semantic-evaluation.json").read_text())
document = structure("sample.txt", [(root / "shared/sample-study-material.txt").read_text()])
index = build_index(document["passages"])
report = {"model": specification["model"], "scope": specification["scope"], "threshold": specification["threshold"]}
for group in ["calibration", "holdout"]:
    results = []
    for case in specification[group]:
        hits = search(document["passages"], index, case["query"], limit=1, threshold=specification["threshold"])
        matched = bool(hits and any(term in hits[0]["quote"] for term in case["expected"])) if case["expected"] else not hits
        results.append({"query": case["query"], "passed": matched, "source_id": hits[0]["source_id"] if hits else None,
                        "score": hits[0]["score"] if hits else None})
    report[group] = {"passed": sum(result["passed"] for result in results), "total": len(results), "results": results}
print(json.dumps(report, indent=2))
sys.exit(0 if all(report[group]["passed"] == report[group]["total"] for group in ["calibration", "holdout"]) else 1)
