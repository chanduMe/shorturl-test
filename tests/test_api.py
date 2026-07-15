import asyncio

import pytest
from httpx import AsyncClient

LONG_URL = "https://example.com/some/really/long/path?with=query&and=more"


async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_create_and_metadata(client: AsyncClient) -> None:
    resp = await client.post("/api/urls", json={"url": LONG_URL})
    assert resp.status_code == 201
    body = resp.json()
    alias = body["alias"]
    assert len(alias) == 7
    assert body["short_url"].endswith(alias)
    assert body["long_url"] == LONG_URL
    assert body["access_count"] == 0
    assert body["created_at"]

    meta = await client.get(f"/api/urls/{alias}")
    assert meta.status_code == 200
    assert meta.json()["long_url"] == LONG_URL


async def test_redirect_and_count(client: AsyncClient) -> None:
    alias = (await client.post("/api/urls", json={"url": LONG_URL})).json()["alias"]

    for _ in range(3):
        r = await client.get(f"/{alias}")
        assert r.status_code == 307
        assert r.headers["location"] == LONG_URL

    meta = await client.get(f"/api/urls/{alias}")
    assert meta.json()["access_count"] == 3
    assert meta.json()["last_accessed_at"] is not None


async def test_custom_alias(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/urls", json={"url": LONG_URL, "custom_alias": "my-link"}
    )
    assert resp.status_code == 201
    assert resp.json()["alias"] == "my-link"


async def test_custom_alias_conflict(client: AsyncClient) -> None:
    payload = {"url": LONG_URL, "custom_alias": "dup"}
    first = await client.post("/api/urls", json=payload)
    assert first.status_code == 201
    second = await client.post("/api/urls", json=payload)
    assert second.status_code == 409


async def test_concurrent_custom_alias(client: AsyncClient) -> None:
    payload = {"url": LONG_URL, "custom_alias": "race"}
    results = await asyncio.gather(
        *(client.post("/api/urls", json=payload) for _ in range(8))
    )
    statuses = [r.status_code for r in results]
    # Exactly one insert wins; all others get a clean 409 (no duplicates).
    assert statuses.count(201) == 1
    assert statuses.count(409) == 7


@pytest.mark.parametrize("bad_url", ["ftp://example.com", "not-a-url", ""])
async def test_invalid_url_rejected(client: AsyncClient, bad_url: str) -> None:
    resp = await client.post("/api/urls", json={"url": bad_url})
    assert resp.status_code == 422


@pytest.mark.parametrize("alias", ["api", "ab", "bad space", "x" * 33])
async def test_invalid_custom_alias_rejected(client: AsyncClient, alias: str) -> None:
    resp = await client.post("/api/urls", json={"url": LONG_URL, "custom_alias": alias})
    assert resp.status_code == 422


async def test_unknown_alias_404(client: AsyncClient) -> None:
    assert (await client.get("/does-not-exist")).status_code == 404
    assert (await client.get("/api/urls/does-not-exist")).status_code == 404
