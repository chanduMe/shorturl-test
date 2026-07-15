import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.cache.factory import build_cache
from app.config import get_settings
from app.database import create_schema, dispose_engine
from app.routers import redirect, urls

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("shorturl")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.cache = build_cache(settings)
    logger.info("Cache backend: %s", settings.cache_backend)
    if settings.create_schema_on_startup:
        await create_schema()
        logger.info("Database schema ensured.")
    try:
        yield
    finally:
        await app.state.cache.close()
        await dispose_engine()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Short-URL Service",
        version="1.0.0",
        description="Create, resolve, and inspect shortened URLs.",
        lifespan=lifespan,
    )

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    # API routes first; the catch-all redirect route is registered last.
    app.include_router(urls.router)
    app.include_router(redirect.router)
    return app


app = create_app()
