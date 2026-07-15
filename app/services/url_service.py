from app.cache.base import Cache
from app.config import Settings
from app.models import Url
from app.repositories.url_repository import AliasExistsError, UrlRepository
from app.utils.alias import generate_alias


class AliasConflictError(Exception):
    """A requested custom alias is already taken."""


class AliasGenerationError(Exception):
    """Could not generate a unique alias within the retry budget."""


class UrlService:
    def __init__(self, repo: UrlRepository, cache: Cache, settings: Settings) -> None:
        self._repo = repo
        self._cache = cache
        self._settings = settings

    async def create(self, long_url: str, custom_alias: str | None) -> Url:
        if custom_alias is not None:
            try:
                url = await self._repo.create(custom_alias, long_url)
            except AliasExistsError:
                # Custom alias taken (possibly by a concurrent request) -> 409.
                raise AliasConflictError(custom_alias)
            await self._cache.set(url.alias, url.long_url)
            return url

        # Auto-generated alias: retry on the rare random collision.
        for _ in range(self._settings.alias_max_retries):
            alias = generate_alias(self._settings.alias_length)
            try:
                url = await self._repo.create(alias, long_url)
            except AliasExistsError:
                continue
            await self._cache.set(url.alias, url.long_url)
            return url
        raise AliasGenerationError()

    async def resolve(self, alias: str) -> str | None:
        """Return the long URL for an alias, using the cache first."""
        cached = await self._cache.get(alias)
        if cached is not None:
            return cached
        url = await self._repo.get_by_alias(alias)
        if url is None:
            return None
        await self._cache.set(url.alias, url.long_url)
        return url.long_url

    async def get_metadata(self, alias: str) -> Url | None:
        return await self._repo.get_by_alias(alias)
