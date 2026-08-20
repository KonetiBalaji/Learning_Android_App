from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    runtime_dir: Path
    jwt_secret: str
    jwt_issuer: str = "learning-api"
    token_minutes: int = 60 * 24
    max_upload_bytes: int = 50 * 1024 * 1024

    @property
    def database_path(self) -> Path:
        return self.runtime_dir / "learning.sqlite3"

    @property
    def uploads_dir(self) -> Path:
        return self.runtime_dir / "uploads"


def get_settings() -> Settings:
    base = Path(os.getenv("LEARNING_RUNTIME_DIR", Path(__file__).parents[1] / ".runtime"))
    secret = os.getenv("LEARNING_JWT_SECRET", "local-development-secret-change-before-deployment")
    base.mkdir(parents=True, exist_ok=True)
    (base / "uploads").mkdir(exist_ok=True)
    return Settings(runtime_dir=base, jwt_secret=secret)
