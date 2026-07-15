from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Url


class AliasExistsError(Exception):
    """Raised when inserting an alias that already exists (unique violation)."""


class UrlRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, alias: str, long_url: str) -> Url:
        """Insert a new mapping.

        Relies on the DB UNIQUE constraint on `alias` as the single arbiter for
        collisions. Concurrent inserts of the same alias: exactly one commits,
        the rest raise AliasExistsError.
        """
        url = Url(alias=alias, long_url=long_url)
        self._session.add(url)
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise AliasExistsError(alias) from exc
        await self._session.refresh(url)
        return url

    async def get_by_alias(self, alias: str) -> Url | None:
        result = await self._session.execute(select(Url).where(Url.alias == alias))
        return result.scalar_one_or_none()

    async def increment_access(self, alias: str) -> None:
        """Atomically bump access_count and stamp last_accessed_at."""
        await self._session.execute(
            update(Url)
            .where(Url.alias == alias)
            .values(
                access_count=Url.access_count + 1,
                last_accessed_at=datetime.now(timezone.utc),
            )
        )
        await self._session.commit()
