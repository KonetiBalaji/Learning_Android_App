"""Disposable emulator fixture: provider always returns a simulated 503.

No real provider traffic or credentials. Bind only to localhost; never deploy.
"""
import argparse
from pathlib import Path
import sys

import httpx
import uvicorn

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend"))
from study import api
from study.provider import OpenAIProvider

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--data-dir", type=Path, required=True)
parser.add_argument("--port", type=int, default=18764)
args = parser.parse_args()
api.configured_provider = lambda: OpenAIProvider("fixture-not-a-credential", "simulated-unavailable",
    httpx.MockTransport(lambda request: httpx.Response(503, text="simulated outage")))
uvicorn.run(api.create_app(args.data_dir), host="127.0.0.1", port=args.port)
