import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "shared" / "contracts" / "openmaic-adaptations.json"


def test_selective_openmaic_adaptations_remain_pinned_licensed_and_resolvable():
    contract = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert contract["upstream_repository"] == "https://github.com/THU-MAIC/OpenMAIC"
    license_text = (ROOT / contract["license_file"]).read_text(encoding="utf-8")
    assert "MIT License" in license_text and "THU-MAIC" in license_text

    adaptations = contract["adaptations"]
    assert [item["id"] for item in adaptations] == ["OA-01", "OA-02", "OA-03"]
    for item in adaptations:
        assert re.fullmatch(r"[0-9a-f]{40}", item["revision"])
        assert item["sources"] and len(item["sources"]) == len(set(item["sources"]))
        assert item["excluded"] and len(item["excluded"]) == len(set(item["excluded"]))
        for local_path in item["local_implementations"]:
            resolved = (ROOT / local_path).resolve()
            assert resolved.is_relative_to(ROOT) and resolved.is_file(), local_path


def test_native_action_adaptation_covers_the_full_grade_eight_catalog_boundary():
    explorer_source = (ROOT / "android" / "app" / "src" / "main" / "java" / "com" /
                       "konetibalaji" / "learning" / "InteractiveLessonExplorer.kt").read_text(
                           encoding="utf-8")
    route_pairs = set(re.findall(r'\("([a-z]+)"\s+to\s+"([a-z-]+)"\)\s+to\s+ExplorerKind\.',
                                 explorer_source))
    assert len(route_pairs) == 17
    assert {subject for subject, _ in route_pairs} == {"math", "science", "english", "social"}
