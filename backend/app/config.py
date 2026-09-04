from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

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
    max_documents_per_owner: int = 100
    max_document_bytes_per_owner: int = 2 * 1024 * 1024 * 1024
    guardian_invitation_retention_days: int = 30
    orphan_upload_grace_hours: int = 24
    openai_api_key: str | None = field(default=None, repr=False)
    openai_model: str = "gpt-5-mini"
    ai_mode: str = "deterministic"
    google_client_id: str | None = None
    auth_attempts_per_window: int = 30
    auth_window_seconds: int = 60
    max_ai_operations_per_owner_per_day: int = 200
    environment: Literal['development', 'staging', 'production'] = 'development'
    release_revision: str = 'development'
    runtime_configured: bool = True

    def __post_init__(self):
        if self.environment not in {'development', 'staging', 'production'}:
            raise ValueError('LEARNING_ENVIRONMENT must be development, staging or production')
        if not 1 <= self.auth_attempts_per_window <= 1000:
            raise ValueError("Authentication attempt limit must be between 1 and 1000")
        if not 1 <= self.auth_window_seconds <= 3600:
            raise ValueError("Authentication window must be between 1 and 3600 seconds")
        if not 1 <= self.token_minutes <= 60 * 24 * 30:
            raise ValueError('Token lifetime must be between 1 minute and 30 days')
        if not 1 <= self.max_documents_per_owner <= 10_000:
            raise ValueError('Per-owner document count must be between 1 and 10000')
        if not 1 <= self.max_upload_bytes <= 1024 ** 3:
            raise ValueError('Per-document upload bytes must be between 1 byte and 1 GiB')
        if not self.max_upload_bytes <= self.max_document_bytes_per_owner <= 1024 ** 4:
            raise ValueError('Per-owner document bytes must cover one upload and not exceed 1 TiB')
        if not 1 <= self.guardian_invitation_retention_days <= 365:
            raise ValueError('Guardian invitation retention must be between 1 and 365 days')
        if not 1 <= self.orphan_upload_grace_hours <= 720:
            raise ValueError('Orphan upload grace period must be between 1 and 720 hours')
        if not 1 <= self.max_ai_operations_per_owner_per_day <= 100_000:
            raise ValueError('Daily per-owner AI operation limit must be between 1 and 100000')
        if self.environment in {'staging', 'production'}:
            if len(self.jwt_secret) < 32 or self.jwt_secret == 'local-development-secret-change-before-deployment':
                raise ValueError('Staging and production require an explicit JWT secret of at least 32 characters')
            if not self.runtime_configured or not self.runtime_dir.is_absolute():
                raise ValueError('Staging and production require an explicit absolute runtime directory')
            if not re.fullmatch(r'[0-9a-f]{40}', self.release_revision):
                raise ValueError('Staging and production require a full lowercase Git release revision')
        if self.environment == 'production' and (self.ai_mode != 'openai' or not self.openai_api_key):
            raise ValueError('Production requires the reviewed OpenAI provider and a server-side key')

    @property
    def database_path(self) -> Path:
        return self.runtime_dir / "learning.sqlite3"

    @property
    def uploads_dir(self) -> Path:
        return self.runtime_dir / "uploads"


def get_settings() -> Settings:
    configured_runtime = os.getenv("LEARNING_RUNTIME_DIR", "").strip()
    base = Path(configured_runtime or Path(__file__).parents[1] / ".runtime")
    secret = os.getenv("LEARNING_JWT_SECRET", "local-development-secret-change-before-deployment")
    base.mkdir(parents=True, exist_ok=True)
    (base / "uploads").mkdir(exist_ok=True)
    api_key = os.getenv("OPENAI_API_KEY", "").strip() or None
    requested_mode = os.getenv("LEARNING_AI_MODE", "").strip().lower()
    ai_mode = requested_mode or ("openai" if api_key else "deterministic")
    return Settings(
        runtime_dir=base,
        jwt_secret=secret,
        max_upload_bytes=int(os.getenv('LEARNING_MAX_UPLOAD_BYTES', str(50 * 1024 * 1024))),
        token_minutes=int(os.getenv('LEARNING_TOKEN_MINUTES', str(60 * 24))),
        max_documents_per_owner=int(os.getenv('LEARNING_MAX_DOCUMENTS_PER_OWNER', '100')),
        max_document_bytes_per_owner=int(os.getenv('LEARNING_MAX_DOCUMENT_BYTES_PER_OWNER', str(2 * 1024 * 1024 * 1024))),
        guardian_invitation_retention_days=int(os.getenv('LEARNING_GUARDIAN_INVITATION_RETENTION_DAYS', '30')),
        orphan_upload_grace_hours=int(os.getenv('LEARNING_ORPHAN_UPLOAD_GRACE_HOURS', '24')),
        max_ai_operations_per_owner_per_day=int(os.getenv('LEARNING_MAX_AI_OPERATIONS_PER_OWNER_PER_DAY', '200')),
        openai_api_key=api_key,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5-mini").strip() or "gpt-5-mini",
        ai_mode=ai_mode,
        google_client_id=os.getenv("LEARNING_GOOGLE_CLIENT_ID", "").strip() or None,
        auth_attempts_per_window=int(os.getenv("LEARNING_AUTH_ATTEMPTS", "30")),
        auth_window_seconds=int(os.getenv("LEARNING_AUTH_WINDOW_SECONDS", "60")),
        environment=os.getenv('LEARNING_ENVIRONMENT', 'development').strip().lower(),
        release_revision=os.getenv('LEARNING_RELEASE_REVISION', 'development').strip(),
        runtime_configured=bool(configured_runtime),
    )
