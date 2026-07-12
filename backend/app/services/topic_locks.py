"""In-process write guards for operations that mutate a topic."""
from __future__ import annotations

from contextlib import contextmanager
from threading import Lock
from typing import Iterator


_registry_lock = Lock()
_topic_locks: dict[int, Lock] = {}


@contextmanager
def claim_topic(topic_id: int, *, blocking: bool) -> Iterator[bool]:
    with _registry_lock:
        lock = _topic_locks.setdefault(topic_id, Lock())
    acquired = lock.acquire(blocking=blocking)
    try:
        yield acquired
    finally:
        if acquired:
            lock.release()
