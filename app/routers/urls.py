from fastapi import APIRouter, HTTPException, status

from app.dependencies import SettingsDep, UrlServiceDep
from app.models import Url
from app.schemas import CreateUrlRequest, UrlResponse
from app.services.url_service import AliasConflictError, AliasGenerationError

router = APIRouter(prefix="/api/urls", tags=["urls"])


def _to_response(url: Url, base_url: str) -> UrlResponse:
    return UrlResponse(
        alias=url.alias,
        short_url=f"{base_url}/{url.alias}",
        long_url=url.long_url,
        created_at=url.created_at,
        access_count=url.access_count,
        last_accessed_at=url.last_accessed_at,
    )


@router.post("", response_model=UrlResponse, status_code=status.HTTP_201_CREATED)
async def create_url(
    payload: CreateUrlRequest, service: UrlServiceDep, settings: SettingsDep
) -> UrlResponse:
    try:
        url = await service.create(payload.url, payload.custom_alias)
    except AliasConflictError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Alias '{payload.custom_alias}' is already taken.",
        )
    except AliasGenerationError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not generate a unique alias; please retry.",
        )
    return _to_response(url, settings.base_url)


@router.get("/{alias}", response_model=UrlResponse)
async def get_url_metadata(
    alias: str, service: UrlServiceDep, settings: SettingsDep
) -> UrlResponse:
    url = await service.get_metadata(alias)
    if url is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alias not found."
        )
    return _to_response(url, settings.base_url)
