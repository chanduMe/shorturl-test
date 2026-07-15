from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from fastapi.responses import RedirectResponse

from app.database import get_sessionmaker
from app.dependencies import UrlServiceDep
from app.repositories.url_repository import UrlRepository

router = APIRouter(tags=["redirect"])


async def _increment_access(alias: str) -> None:
    """Bump the access counter in its own session (runs after the response)."""
    async with get_sessionmaker()() as session:
        await UrlRepository(session).increment_access(alias)


@router.get("/{alias}")
async def redirect(
    alias: str, service: UrlServiceDep, background_tasks: BackgroundTasks
) -> RedirectResponse:
    long_url = await service.resolve(alias)
    if long_url is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alias not found."
        )
    # Count the hit without blocking the redirect response.
    background_tasks.add_task(_increment_access, alias)
    return RedirectResponse(
        url=long_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT
    )
