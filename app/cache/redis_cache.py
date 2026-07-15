import redis.asyncio as redis


class RedisCache:
    """Shared cache backed by Redis (works across multiple instances)."""

    _PREFIX = "shorturl:alias:"

    def __init__(self, redis_url: str, ttl_seconds: int) -> None:
        self._ttl = ttl_seconds
        self._client: redis.Redis = redis.from_url(
            redis_url, encoding="utf-8", decode_responses=True
        )

    def _key(self, key: str) -> str:
        return f"{self._PREFIX}{key}"

    async def get(self, key: str) -> str | None:
        return await self._client.get(self._key(key))

    async def set(self, key: str, value: str) -> None:
        await self._client.set(self._key(key), value, ex=self._ttl)

    async def delete(self, key: str) -> None:
        await self._client.delete(self._key(key))

    async def close(self) -> None:
        await self._client.aclose()
