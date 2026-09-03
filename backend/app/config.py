from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


BACKEND_ROOT = Path(__file__).parents[1]
load_dotenv(BACKEND_ROOT / ".env.local", override=False)


@dataclass(frozen=True)
class Settings:
    runtime_dir: Path
    jwt_secret: str
    jwt_issuer: str = "learning-api"
    token_minutes: int = 60 * 24
    max_upload_bytes: int = 50 * 1024 * 1024
    openai_api_key: str | None = field(default=None, repr=False)
    openai_model: str = "gpt-5-mini"
    ai_mode: str = "deterministic"

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
    api_key = os.getenv("OPENAI_API_KEY", "").strip() or None
    requested_mode = os.getenv("LEARNING_AI_MODE", "").strip().lower()
    ai_mode = requested_mode or ("openai" if api_key else "deterministic")
    return Settings(
        runtime_dir=base,
        jwt_secret=secret,
        openai_api_key=api_key,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5-mini").strip() or "gpt-5-mini",
        ai_mode=ai_mode,
    )
