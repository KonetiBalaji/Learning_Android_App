"""Shared fail-fast admission for untrusted parser children in one API process."""

import threading
from contextlib import contextmanager


class ParserCapacityError(RuntimeError):
    pass


_pool_guard = threading.Lock()
_pools: dict[int, threading.BoundedSemaphore] = {}


def _pool(limit: int) -> threading.BoundedSemaphore:
    if not 1 <= limit <= 16:
        raise ValueError('Concurrent parser limit must be between 1 and 16')
    with _pool_guard:
        return _pools.setdefault(limit, threading.BoundedSemaphore(limit))


@contextmanager
def parser_slot(limit: int):
    pool = _pool(limit)
    if not pool.acquire(blocking=False):
        raise ParserCapacityError('Document parser capacity is currently full')
    try:
        yield
    finally:
        pool.release()
