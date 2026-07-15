from typing import Protocol, runtime_checkable


@runtime_checkable
class Cache(Protocol):
    """Minimal async cache interface used for redirect lookups."""

    async def get(self, key: str) -> str | None: ...

    async def set(self, key: str, value: str) -> None: ...

    async def delete(self, key: str) -> None: ...

    async def close(self) -> None: ...
