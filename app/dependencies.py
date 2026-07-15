from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.base import Cache
from app.config import Settings, get_settings
from app.database import get_session
from app.repositories.url_repository import UrlRepository
from app.services.url_service import UrlService


def get_cache(request: Request) -> Cache:
    return request.app.state.cache


SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]
CacheDep = Annotated[Cache, Depends(get_cache)]


def get_url_service(
    session: SessionDep, cache: CacheDep, settings: SettingsDep
) -> UrlService:
    return UrlService(UrlRepository(session), cache, settings)


UrlServiceDep = Annotated[UrlService, Depends(get_url_service)]
