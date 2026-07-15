from app.cache.base import Cache
from app.cache.memory import InMemoryCache
from app.cache.redis_cache import RedisCache
from app.config import Settings


def build_cache(settings: Settings) -> Cache:
    """Construct the cache implementation selected by settings."""
    if settings.cache_backend == "redis":
        return RedisCache(settings.redis_url, settings.cache_ttl_seconds)
    return InMemoryCache(settings.cache_max_size, settings.cache_ttl_seconds)
