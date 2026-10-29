"""Run from the repository root after installing backend dependencies."""
import json
import sys
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend"))
from study.api import create_app

with tempfile.TemporaryDirectory() as directory:
    app = create_app(Path(directory))
    contract = app.openapi()
    (root / "shared" / "contracts" / "openapi.json").write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    app.state.store.db.close()
