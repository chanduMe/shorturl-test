# Short-URL Service

A production-ready URL shortener built with **FastAPI** and **PostgreSQL**.

- Create short URLs (auto-generated or custom aliases)
- Safe concurrent creation via a DB `UNIQUE` constraint (no app-level locking)
- Fast redirects with a pluggable cache (in-memory locally, Redis in production)
- Metadata: creation time and access counts

## Architecture

```
Client → FastAPI → UrlService → Cache (memory | redis)
                              → UrlRepository → PostgreSQL
```

- `POST /api/urls` — create a short URL.
- `GET /{alias}` — 307 redirect to the original URL (cache-first lookup).
- `GET /api/urls/{alias}` — metadata (creation time, access count, last access).
- `GET /health` — health check.
- Swagger UI at `/docs`.

### How collisions and races are handled

The `urls.alias` column has a `UNIQUE` constraint, which is the single source of
truth for uniqueness. On insert:

- **Auto-generated alias**: a random base62 string (default length 7). On the
  rare collision, the service retries with a new alias (bounded by
  `ALIAS_MAX_RETRIES`).
- **Custom alias**: attempted directly. If it already exists — including when two
  users request the same alias at the exact same moment — exactly one INSERT
  commits and the others receive a clean `409 Conflict`.

This is race-proof because the database performs the uniqueness check atomically;
a "SELECT then INSERT" check in application code would have a time-of-check to
time-of-use race and is intentionally avoided.

### Caching & access counts

- Redirects check the cache first (`alias → long_url`); on a miss the DB is
  queried and the cache is populated with a TTL.
- Access counts are incremented with an atomic SQL `UPDATE ... SET access_count =
  access_count + 1` in a background task, so redirects stay fast and counts stay
  correct under concurrency.

## Run locally

Requires Python 3.12+ and Docker (for PostgreSQL).

```bash
# 1. Start PostgreSQL
docker-compose up -d postgres

# 2. Install dependencies
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. (optional) copy env defaults
cp .env.example .env

# 4. Run the API (schema is auto-created on startup)
uvicorn app.main:app --reload
```

Then open http://localhost:8000/docs.

### Example

```bash
# Create
curl -X POST http://localhost:8000/api/urls \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://example.com/a/very/long/link"}'

# Create with a custom alias
curl -X POST http://localhost:8000/api/urls \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://example.com", "custom_alias": "promo"}'

# Redirect (follow it)
curl -L http://localhost:8000/promo

# Metadata
curl http://localhost:8000/api/urls/promo
```

## Tests

Tests run against SQLite, so no external services are needed:

```bash
pytest
```

They cover creation, custom aliases, collision handling (409), concurrent
custom-alias safety, redirect + access counting, metadata, and input validation.

## Configuration

Set via environment variables (see `.env.example`):

| Variable | Default | Description |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+asyncpg://shorturl:shorturl@localhost:5432/shorturl` | Async SQLAlchemy DB URL |
| `CACHE_BACKEND` | `memory` | `memory` (single instance) or `redis` (shared) |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection (when `CACHE_BACKEND=redis`) |
| `CACHE_TTL_SECONDS` | `3600` | Cache entry TTL |
| `CACHE_MAX_SIZE` | `10000` | In-memory LRU capacity |
| `ALIAS_LENGTH` | `7` | Length of generated aliases |
| `ALIAS_MAX_RETRIES` | `5` | Retries on random-alias collision |
| `BASE_URL` | `http://localhost:8000` | Used to build returned `short_url` |
| `CREATE_SCHEMA_ON_STARTUP` | `true` | Auto-create tables on startup |

## Production

The service is container-ready. A production-like stack (API + PostgreSQL +
Redis) is available via the compose `prod` profile:

```bash
docker-compose --profile prod up --build
```

This runs the API under `gunicorn` with `uvicorn` workers and uses Redis as the
shared cache (`CACHE_BACKEND=redis`), so the cache works correctly across
multiple instances.

### Notes / next steps

- **Schema management**: tables are auto-created on startup for now. Before
  evolving the schema in production, introduce a migration tool (e.g. Alembic).
- **Hot-link counters**: for very hot links, buffer access counts in Redis and
  flush them to PostgreSQL periodically to reduce write load.
