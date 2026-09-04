"""Atomic per-owner daily admission control for provider-backed operations."""
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException

from .database import connection


def consume_ai_operation(settings, owner_id: str, *, at: datetime | None = None) -> None:
    if settings.ai_mode != 'openai':
        return
    current = (at or datetime.now(UTC)).astimezone(UTC)
    day = current.date().isoformat()
    with connection(settings.database_path) as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT operations FROM ai_usage_days WHERE owner_id = ? AND day = ?',
                         (owner_id, day)).fetchone()
        used = row['operations'] if row else 0
        if used >= settings.max_ai_operations_per_owner_per_day:
            tomorrow = datetime.combine(current.date() + timedelta(days=1), datetime.min.time(), UTC)
            retry = max(1, int((tomorrow - current).total_seconds()))
            raise HTTPException(429, 'Daily AI learning limit reached. Try again tomorrow.',
                                headers={'Retry-After': str(retry), 'X-Learning-Error': 'daily_ai_limit'})
        db.execute('''INSERT INTO ai_usage_days(owner_id, day, operations) VALUES (?, ?, 1)
                      ON CONFLICT(owner_id, day) DO UPDATE SET operations = operations + 1''',
                   (owner_id, day))
