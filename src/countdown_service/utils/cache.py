"""In-memory caching utilities."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any, Callable, Dict, Optional, Tuple


@dataclass
class CacheEntry:
    value: Any
    expires_at: datetime


@dataclass
class CacheStats:
    items: int
    ttl_seconds: int


class TTLCache:
    """Very small in-memory TTL cache suitable for demos/tests."""

    def __init__(self, ttl_seconds: int = 60):
        self._ttl = timedelta(seconds=ttl_seconds)
        self._store: Dict[str, CacheEntry] = {}
        self._lock = Lock()

    @property
    def ttl_seconds(self) -> int:
        return int(self._ttl.total_seconds())

    def _purge_expired_locked(self) -> None:
        now = datetime.now(timezone.utc)
        expired_keys = [key for key, entry in self._store.items() if entry.expires_at < now]
        for key in expired_keys:
            self._store.pop(key, None)

    def get(self, key: str) -> Optional[CacheEntry]:
        with self._lock:
            self._purge_expired_locked()
            return self._store.get(key)

    def set(self, key: str, value: Any) -> CacheEntry:
        with self._lock:
            expires = datetime.now(timezone.utc) + self._ttl
            entry = CacheEntry(value=value, expires_at=expires)
            self._store[key] = entry
            return entry

    def get_or_set(self, key: str, factory: Callable[[], Any]) -> Tuple[Any, CacheEntry, bool]:
        entry = self.get(key)
        if entry:
            return entry.value, entry, True
        value = factory()
        entry = self.set(key, value)
        return value, entry, False

    def stats(self) -> CacheStats:
        with self._lock:
            self._purge_expired_locked()
            return CacheStats(items=len(self._store), ttl_seconds=self.ttl_seconds)
