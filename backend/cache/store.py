"""Cache en memoria con TTL.

Abstraccion simple que podria reemplazarse por Redis
sin cambiar la interfaz publica.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class _Entry:
    value: Any
    expires_at: float
    cached_at: float


class CacheStore:
    """Key-value en memoria con expiracion por TTL."""

    def __init__(self) -> None:
        self._entries: dict[str, _Entry] = {}

    def get(self, key: str) -> Any | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if time.time() > entry.expires_at:
            del self._entries[key]
            return None
        return entry.value

    def put(self, key: str, value: Any, ttl_seconds: int) -> None:
        now = time.time()
        self._entries[key] = _Entry(
            value=value,
            expires_at=now + ttl_seconds,
            cached_at=now,
        )

    def age(self, key: str) -> float | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        return time.time() - entry.cached_at

    def clear(self) -> None:
        self._entries.clear()
