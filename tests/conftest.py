from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.database as db
from app.cache.memory import InMemoryCache
from app.database import Base
from app.main import app


@pytest_asyncio.fixture
async def client(tmp_path) -> AsyncGenerator[AsyncClient, None]:
    # File-based SQLite so concurrent sessions use separate connections and the
    # UNIQUE constraint behaves like it would in Postgres.
    db_path = tmp_path / "test.db"
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        connect_args={"timeout": 30},
    )
    sessionmaker = async_sessionmaker(bind=engine, expire_on_commit=False)

    # Inject the test engine/sessionmaker used by dependencies and background tasks.
    db._engine = engine
    db._sessionmaker = sessionmaker

    from app import models  # noqa: F401  (register models on metadata)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Lifespan is not run by ASGITransport, so set the cache explicitly.
    app.state.cache = InMemoryCache(max_size=1000, ttl_seconds=3600)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await app.state.cache.close()
    await engine.dispose()
    db._engine = None
    db._sessionmaker = None
