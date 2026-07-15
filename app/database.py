from collections.abc import AsyncGenerator
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None

# libpq query params that asyncpg does not accept in the URL and must be
# translated (or dropped) so managed providers like Neon work out of the box.
_LIBPQ_SSL_MODES = {"require", "verify-ca", "verify-full", "prefer", "allow"}


def _normalize_database_url(url: str) -> tuple[str, dict[str, object]]:
    """Return an asyncpg-friendly URL and matching ``connect_args``.

    Accepts standard libpq/Neon connection strings (``postgresql://`` with
    ``sslmode``/``channel_binding`` query params) and converts them to the
    ``postgresql+asyncpg://`` form, since asyncpg does not understand those
    query params and instead expects SSL to be passed as a connect arg.
    """
    parts = urlsplit(url)
    scheme = parts.scheme

    # Ensure the async driver is used.
    if scheme in ("postgres", "postgresql"):
        scheme = "postgresql+asyncpg"

    connect_args: dict[str, object] = {}
    query = parse_qs(parts.query)

    # Translate libpq sslmode -> asyncpg ssl connect arg, then drop it.
    sslmode = query.pop("sslmode", [None])[0]
    if sslmode and sslmode.lower() in _LIBPQ_SSL_MODES:
        connect_args["ssl"] = "require"

    # channel_binding is a libpq-only knob asyncpg cannot parse; drop it.
    query.pop("channel_binding", None)

    new_query = urlencode({k: v[-1] for k, v in query.items()})
    normalized = urlunsplit(
        (scheme, parts.netloc, parts.path, new_query, parts.fragment)
    )
    return normalized, connect_args


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        url, connect_args = _normalize_database_url(settings.database_url)
        _engine = create_async_engine(
            url,
            pool_pre_ping=True,
            future=True,
            connect_args=connect_args,
        )
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            bind=get_engine(), expire_on_commit=False, class_=AsyncSession
        )
    return _sessionmaker


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async DB session."""
    async with get_sessionmaker()() as session:
        yield session


async def create_schema() -> None:
    """Create any missing tables from ORM metadata (no migration tool for now).

    Existing tables are left untouched: we inspect the database first and only
    issue DDL for tables that are not already present, so repeated startups are
    a no-op once the schema exists.
    """
    # Import models so they register on Base.metadata before create_all.
    from app import models  # noqa: F401

    def _create_missing(conn) -> None:
        inspector = inspect(conn)
        existing = set(inspector.get_table_names())
        missing = [
            table
            for name, table in Base.metadata.tables.items()
            if name not in existing
        ]
        if not missing:
            return
        Base.metadata.create_all(conn, tables=missing, checkfirst=False)

    async with get_engine().begin() as conn:
        await conn.run_sync(_create_missing)


async def dispose_engine() -> None:
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None
