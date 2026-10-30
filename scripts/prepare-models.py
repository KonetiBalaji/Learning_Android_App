"""Warm and verify public local models without any document or API key."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend"))
parser = argparse.ArgumentParser()
parser.add_argument("--verify", action="store_true")
args = parser.parse_args()
directory = Path(os.getenv("STUDY_MODEL_DIR", str(root / ".study-models"))).resolve()
os.environ["STUDY_MODEL_DIR"] = str(directory)
manifest_path = directory / "models-manifest.json"
if not args.verify:
    from study.processing import ocr_engine
    from study.semantic import encoder
    ocr_engine()
    encoder()
files = {}
for path in sorted(directory.rglob("*")):
    if path.is_file() and path.name != manifest_path.name and (path.suffix in {".onnx", ".json"} or path.name == "vocab.txt"):
        files[path.relative_to(directory).as_posix()] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}
if not files:
    raise SystemExit("No prepared model files found. Run model preparation first.")
if args.verify:
    if files != json.loads(manifest_path.read_text(encoding="utf-8"))["files"]:
        raise SystemExit("Public model integrity check failed. Do not serve this cache.")
else:
    manifest_path.write_text(json.dumps({"ocr_package": "rapidocr", "semantic_model": "BAAI/bge-small-en-v1.5", "files": files}, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"models": "verified" if args.verify else "prepared", "public_model_files": len(files)}))
