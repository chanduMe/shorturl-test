import asyncio
import time
from collections import OrderedDict


class InMemoryCache:
    """Thread/async-safe LRU cache with per-entry TTL.

    Single-instance only (state is per-process). Suitable for local dev or a
    single worker; use RedisCache for multi-instance deployments.
    """

    def __init__(self, max_size: int, ttl_seconds: int) -> None:
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._store: OrderedDict[str, tuple[str, float]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> str | None:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if expires_at < time.monotonic():
                del self._store[key]
                return None
            self._store.move_to_end(key)
            return value

    async def set(self, key: str, value: str) -> None:
        async with self._lock:
            self._store[key] = (value, time.monotonic() + self._ttl)
            self._store.move_to_end(key)
            while len(self._store) > self._max_size:
                self._store.popitem(last=False)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)

    async def close(self) -> None:
        async with self._lock:
            self._store.clear()
