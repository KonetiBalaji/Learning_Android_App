"""Validated production server entrypoint used by the container image."""
from __future__ import annotations

import os

import uvicorn


def configured_workers(raw: str | None = None, platform_name: str | None = None) -> int:
    value = os.getenv('LEARNING_WEB_CONCURRENCY', '1') if raw is None else raw
    try:
        workers = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError('LEARNING_WEB_CONCURRENCY must be an integer from 1 to 8') from error
    if not 1 <= workers <= 8:
        raise ValueError('LEARNING_WEB_CONCURRENCY must be an integer from 1 to 8')
    if (platform_name or os.name) == 'nt' and workers > 1:
        raise ValueError('Multiple API workers require the Linux production container')
    return workers


def main() -> None:
    uvicorn.run('app.main:app', host='0.0.0.0', port=8000,
                workers=configured_workers(), access_log=False)


if __name__ == '__main__':
    main()
