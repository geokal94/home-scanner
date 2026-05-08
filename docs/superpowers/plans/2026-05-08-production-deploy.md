# Production Deploy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wrap the Plan 1 backend in a FastAPI HTTP layer, containerize it, deploy to Fly.io with scale-to-zero, and externalise scheduling to GitHub Actions cron — producing a publicly-reachable bot URL plus an hourly scrape pipeline.

**Architecture:** Single Python service grows a `home_scanner.api` module exposing a FastAPI `Application`. Telegram bot switches from long-polling to webhook mode (Telegram POSTs updates to our `/webhook/telegram/<secret>`). Hourly scrapes are triggered by a GitHub Actions workflow that POSTs to our `/internal/scrape` endpoint with a shared bearer secret. All Python continues to run in one container; Fly.io auto-stops it when idle. Sentry captures uncaught exceptions in API, bot handlers, and the notifier.

**Tech Stack:** Adds `fastapi`, `uvicorn`, `sentry-sdk[fastapi]`. Deploys via Docker on Fly.io. CI/cron via GitHub Actions. Frontend deferred to Plan 3.

**Spec reference:** `docs/superpowers/specs/2026-05-08-home-scanner-portfolio-design.md` §4 (Architecture & Operational costs), §8 (Error handling & observability), §9 (CI + daily canary).

**Out of scope (deferred to Plan 3):** Next.js frontend, public `/listings/<slug>` static pages, reliability-pill UI, Playwright smoke test against deployed frontend.

---

## File structure (additions on top of Plan 1)

```
home-scanner/
├── .github/
│   └── workflows/
│       ├── ci.yml                         # NEW — lint + typecheck + tests on PR
│       ├── scrape.yml                     # NEW — hourly cron POSTs to /internal/scrape
│       └── daily-canary.yml               # NEW — daily live spitogatos parser smoke
├── backend/
│   ├── Dockerfile                         # NEW — single-stage python:3.12-slim
│   ├── fly.toml                           # NEW — Fly.io machine config + release_command
│   ├── home_scanner/
│   │   ├── api/                           # NEW package
│   │   │   ├── __init__.py
│   │   │   ├── app.py                     # FastAPI factory + lifespan
│   │   │   ├── deps.py                    # FastAPI dependencies (session, secret auth)
│   │   │   ├── healthz.py                 # GET /healthz
│   │   │   ├── listings.py                # GET /listings with filters
│   │   │   ├── scrape.py                  # POST /internal/scrape (bearer auth)
│   │   │   └── telegram_webhook.py        # POST /webhook/telegram/<secret>
│   │   ├── observability/                 # NEW package
│   │   │   ├── __init__.py
│   │   │   └── sentry.py                  # init_sentry() helper
│   │   ├── bot/
│   │   │   └── app.py                     # MODIFIED — split build_application
│   │   │                                  #   into polling-mode and webhook-mode entrypoints
│   │   ├── cli.py                         # MODIFIED — add `serve` subcommand
│   │   └── settings.py                    # MODIFIED — add SCRAPE_SECRET,
│   │                                      #   TELEGRAM_WEBHOOK_SECRET, SENTRY_DSN, PUBLIC_BASE_URL
│   ├── pyproject.toml                     # MODIFIED — add fastapi, uvicorn, sentry-sdk
│   └── tests/
│       └── api/
│           ├── __init__.py
│           ├── conftest.py                # api_client fixture
│           ├── test_healthz.py
│           ├── test_listings.py
│           ├── test_scrape.py
│           └── test_telegram_webhook.py
└── README.md                              # MODIFIED — deploy section
```

**Files retired:** none. Long-polling `bot` command in `cli.py` stays for local dev — webhook mode is additive.

---

## Task list

11 tasks across 5 phases.

| Phase | Tasks |
|---|---|
| A — Deps & observability | T1 |
| B — FastAPI foundation | T2, T3 |
| C — Bot webhook + scrape endpoint | T4, T5 |
| D — Containerise & deploy | T6, T7 |
| E — CI/cron/canary | T8, T9, T10 |
| F — Polish | T11 |

---

## Phase A — Deps & observability

### Task 1: Add FastAPI/uvicorn/Sentry deps + observability module

**Files:**
- Modify: `backend/pyproject.toml`
- Create: `backend/home_scanner/observability/__init__.py`
- Create: `backend/home_scanner/observability/sentry.py`
- Modify: `backend/home_scanner/settings.py`

- [ ] **Step 1: Add the three new env-var fields to `Settings`**

In `backend/home_scanner/settings.py`, change the dataclass body to add:

```python
@dataclass(frozen=True, slots=True)
class Settings:
    dataimpulse_user: str
    dataimpulse_pass: str
    dataimpulse_host: str
    dataimpulse_port: str
    database_url: str
    telegram_bot_token: str
    log_level: str = "INFO"
    # NEW in Plan 2:
    scrape_secret: str = ""
    telegram_webhook_secret: str = ""
    sentry_dsn: str = ""
    public_base_url: str = ""

    def __init__(self) -> None:  # type: ignore[no-redef]
        object.__setattr__(self, "dataimpulse_user", os.environ["DATAIMPULSE_USER"])
        object.__setattr__(self, "dataimpulse_pass", os.environ["DATAIMPULSE_PASS"])
        object.__setattr__(self, "dataimpulse_host", os.environ["DATAIMPULSE_HOST"])
        object.__setattr__(self, "dataimpulse_port", os.environ["DATAIMPULSE_PORT"])
        object.__setattr__(self, "database_url", os.environ["DATABASE_URL"])
        object.__setattr__(self, "telegram_bot_token", os.environ["TELEGRAM_BOT_TOKEN"])
        object.__setattr__(self, "log_level", os.environ.get("LOG_LEVEL", "INFO"))
        object.__setattr__(self, "scrape_secret", os.environ.get("SCRAPE_SECRET", ""))
        object.__setattr__(self, "telegram_webhook_secret", os.environ.get("TELEGRAM_WEBHOOK_SECRET", ""))
        object.__setattr__(self, "sentry_dsn", os.environ.get("SENTRY_DSN", ""))
        object.__setattr__(self, "public_base_url", os.environ.get("PUBLIC_BASE_URL", ""))
```

The new fields are optional (default `""`) so existing tests don't have to mock them. API endpoints that require them will validate at request-time.

- [ ] **Step 2: Add deps to `backend/pyproject.toml`** — under `[tool.poetry.dependencies]`, append:

```toml
fastapi = "^0.115"
uvicorn = {extras = ["standard"], version = "^0.32"}
"sentry-sdk" = {extras = ["fastapi"], version = "^2.18"}
```

Also append to the example file (Step 5 below).

- [ ] **Step 3: Install and verify**

```bash
cd backend && poetry install
poetry run python -c "import fastapi, uvicorn, sentry_sdk; print('ok')"
```
Expected: `ok`.

- [ ] **Step 4: Implement `home_scanner/observability/sentry.py`**

```python
"""Sentry initialization. No-op when SENTRY_DSN is empty."""
from __future__ import annotations

import structlog

log = structlog.get_logger(__name__)


def init_sentry(*, dsn: str, environment: str = "production") -> None:
    """Initialize Sentry SDK if a DSN is configured. No-op otherwise.

    Called once at process startup (FastAPI lifespan + bot polling startup).
    """
    if not dsn:
        log.info("sentry.disabled", reason="no_dsn")
        return

    import sentry_sdk
    from sentry_sdk.integrations.asyncio import AsyncioIntegration

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        traces_sample_rate=0.0,  # No tracing — only error capture for the free tier budget
        integrations=[AsyncioIntegration()],
    )
    log.info("sentry.enabled", environment=environment)
```

Also create `backend/home_scanner/observability/__init__.py`:

```python
"""Observability utilities (Sentry, structlog already in home_scanner.logging)."""
from .sentry import init_sentry

__all__ = ["init_sentry"]
```

- [ ] **Step 5: Update `backend/.env.example`** — append below the existing block:

```
# Plan 2 — Production deploy (set these for a deployed environment)

# Bearer secret for /internal/scrape; matched against Authorization: Bearer header.
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
SCRAPE_SECRET=

# Random token in the Telegram webhook URL path. Telegram doesn't sign requests, so
# the secret in the URL is the auth. Generate with secrets.token_urlsafe(32).
TELEGRAM_WEBHOOK_SECRET=

# Sentry DSN. Leave empty in local dev — observability is a no-op without it.
SENTRY_DSN=

# Publicly-reachable base URL for the deployed app, e.g. https://home-scanner.fly.dev
# Used at deploy time to register the Telegram webhook with the bot API.
PUBLIC_BASE_URL=
```

- [ ] **Step 6: Run the existing test suite** — make sure adding the optional Settings fields didn't regress anything:

```bash
poetry run pytest -q
```
Expected: 52 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/pyproject.toml backend/.env.example backend/home_scanner/settings.py backend/home_scanner/observability
git commit -m "feat: add fastapi/uvicorn/sentry deps and observability module"
```

---

## Phase B — FastAPI foundation

### Task 2: API scaffold + `/healthz` endpoint

**Files:**
- Create: `backend/home_scanner/api/__init__.py`
- Create: `backend/home_scanner/api/app.py`
- Create: `backend/home_scanner/api/deps.py`
- Create: `backend/home_scanner/api/healthz.py`
- Create: `backend/tests/api/__init__.py`
- Create: `backend/tests/api/conftest.py`
- Create: `backend/tests/api/test_healthz.py`

- [ ] **Step 1: Implement `home_scanner/api/deps.py`** — FastAPI dependency providers

```python
"""FastAPI dependency injection helpers."""
from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session, sessionmaker

from home_scanner.settings import Settings


def get_settings() -> Settings:
    """Override-able in tests via FastAPI's app.dependency_overrides."""
    return Settings()


def get_session_factory(request_state) -> sessionmaker:  # type: ignore[no-untyped-def]
    """Pulled from app.state in real use; tests override directly."""
    raise NotImplementedError("set via Depends(get_session_factory_factory(app))")


def make_get_session(session_factory: sessionmaker):
    """Factory that returns a FastAPI dependency yielding a Session."""
    def _get_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session
    return _get_session


def require_scrape_secret(
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> None:
    """401 unless `Authorization: Bearer <SCRAPE_SECRET>` header matches."""
    if not settings.scrape_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scrape endpoint not configured",
        )
    expected = f"Bearer {settings.scrape_secret}"
    if authorization != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
```

- [ ] **Step 2: Implement `home_scanner/api/healthz.py`**

```python
"""GET /healthz — last scrape, status, listing counts. Used by uptime monitors
and the public landing page's freshness pill (Plan 3 frontend)."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from home_scanner.api.deps import make_get_session
from home_scanner.db.models import Listing, ScrapeRun

router = APIRouter()


def build_router(session_factory) -> APIRouter:  # type: ignore[no-untyped-def]
    get_session = make_get_session(session_factory)
    r = APIRouter()

    @r.get("/healthz")
    def healthz(session: Session = Depends(get_session)) -> dict[str, Any]:
        last_run = session.scalar(
            select(ScrapeRun).order_by(ScrapeRun.started_at.desc()).limit(1)
        )
        active_count = session.scalar(
            select(func.count(Listing.id)).where(Listing.is_active.is_(True))
        ) or 0

        if last_run is None:
            return {
                "status": "down",
                "last_scrape": None,
                "active_listings": active_count,
            }

        now = datetime.now(UTC)
        minutes_ago = int((now - last_run.started_at).total_seconds() / 60)

        if last_run.status == "failed":
            status_str = "down"
        elif minutes_ago > 90:
            status_str = "degraded"
        else:
            status_str = "ok"

        return {
            "status": status_str,
            "last_scrape": {
                "started_at": last_run.started_at.isoformat(),
                "status": last_run.status,
                "minutes_ago": minutes_ago,
            },
            "active_listings": active_count,
        }

    return r
```

- [ ] **Step 3: Implement `home_scanner/api/app.py`** — FastAPI factory

```python
"""FastAPI application factory."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from sqlalchemy.orm import sessionmaker

from home_scanner.api.healthz import build_router as build_healthz_router
from home_scanner.observability import init_sentry
from home_scanner.settings import Settings


def build_app(*, session_factory: sessionmaker) -> FastAPI:
    """Assemble the FastAPI app. `session_factory` is injected so tests can swap
    in a test sessionmaker bound to a testcontainer Postgres."""
    settings = Settings()
    init_sentry(dsn=settings.sentry_dsn)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Hooks for bot startup/shutdown go in T5.
        yield

    app = FastAPI(title="home-scanner", lifespan=lifespan)
    app.state.session_factory = session_factory

    app.include_router(build_healthz_router(session_factory))
    return app
```

- [ ] **Step 4: Implement `home_scanner/api/__init__.py`**

```python
"""FastAPI HTTP layer."""
from .app import build_app

__all__ = ["build_app"]
```

- [ ] **Step 5: Implement `backend/tests/api/conftest.py`**

```python
"""Shared fixtures for API tests."""
from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def session_factory(db_engine: Engine) -> sessionmaker:
    return sessionmaker(bind=db_engine, expire_on_commit=False)


@pytest.fixture
def api_app(session_factory: sessionmaker) -> FastAPI:
    from home_scanner.api import build_app
    return build_app(session_factory=session_factory)


@pytest.fixture
def api_client(api_app: FastAPI) -> Generator[TestClient, None, None]:
    with TestClient(api_app) as client:
        yield client
```

- [ ] **Step 6: Write `backend/tests/api/test_healthz.py`**

```python
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from home_scanner.db.models import Listing, ScrapeRun
from sqlalchemy.orm import Session, sessionmaker


def test_healthz_with_no_scrape_runs(
    api_client: TestClient, db_session: Session
):
    response = api_client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "down"
    assert body["last_scrape"] is None
    assert body["active_listings"] == 0


def test_healthz_recent_ok_run(
    api_client: TestClient,
    session_factory: sessionmaker,
    db_session: Session,
):
    # Insert via session_factory so commit is visible to the API request
    with session_factory() as s:
        s.add(ScrapeRun(
            started_at=datetime.now(UTC) - timedelta(minutes=15),
            finished_at=datetime.now(UTC) - timedelta(minutes=14),
            status="ok",
            errors={"failed": {}},
        ))
        s.commit()

    response = api_client.get("/healthz")
    body = response.json()
    assert body["status"] == "ok"
    assert body["last_scrape"]["status"] == "ok"
    assert 10 <= body["last_scrape"]["minutes_ago"] <= 20


def test_healthz_stale_run_is_degraded(
    api_client: TestClient,
    session_factory: sessionmaker,
):
    with session_factory() as s:
        s.add(ScrapeRun(
            started_at=datetime.now(UTC) - timedelta(minutes=120),
            status="ok",
            errors={"failed": {}},
        ))
        s.commit()

    response = api_client.get("/healthz")
    assert response.json()["status"] == "degraded"


def test_healthz_failed_run_is_down(
    api_client: TestClient,
    session_factory: sessionmaker,
):
    with session_factory() as s:
        s.add(ScrapeRun(
            started_at=datetime.now(UTC) - timedelta(minutes=15),
            status="failed",
            errors={"failed": {"all": "bot_detection"}},
        ))
        s.commit()

    response = api_client.get("/healthz")
    assert response.json()["status"] == "down"


def test_healthz_counts_active_listings(
    api_client: TestClient,
    session_factory: sessionmaker,
):
    now = datetime.now(UTC)
    with session_factory() as s:
        s.add(Listing(
            external_id="a", url="https://x", price_eur=800,
            first_seen_at=now, last_seen_at=now, is_active=True,
        ))
        s.add(Listing(
            external_id="b", url="https://y", price_eur=900,
            first_seen_at=now, last_seen_at=now, is_active=False,
        ))
        s.commit()

    response = api_client.get("/healthz")
    assert response.json()["active_listings"] == 1
```

- [ ] **Step 7: Run tests, expect pass**

```bash
poetry run pytest tests/api/test_healthz.py -v
```
Expected: 5 passed.

- [ ] **Step 8: Commit**

```bash
git add backend/home_scanner/api backend/tests/api
git commit -m "feat: add FastAPI app factory and /healthz endpoint"
```

### Important notes

- **Why a `build_router` factory in `healthz.py`** instead of a module-level `router`: the session-injection dependency needs to bind to the per-app `session_factory`. Using a factory keeps the binding explicit and lets tests override cleanly.
- **`active_listings` counts only `is_active=True`** — listings disappear when a scrape no longer returns them; the count reflects current market.
- **TestClient is the synchronous Starlette test client.** It runs FastAPI's async code under the hood — no `@pytest.mark.asyncio` needed.

---

### Task 3: GET `/listings` with filters

**Files:**
- Create: `backend/home_scanner/api/listings.py`
- Modify: `backend/home_scanner/api/app.py` (register router)
- Create: `backend/tests/api/test_listings.py`

- [ ] **Step 1: Implement `home_scanner/api/listings.py`**

```python
"""GET /listings — paginated browse endpoint with filter query params.

Filters mirror the bot's saved-search dimensions: location_slug, price range,
bedroom range. Used by the Plan 3 React frontend.
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from home_scanner.api.deps import make_get_session
from home_scanner.db.models import Listing


def build_router(session_factory) -> APIRouter:  # type: ignore[no-untyped-def]
    get_session = make_get_session(session_factory)
    r = APIRouter()

    @r.get("/listings")
    def get_listings(
        session: Session = Depends(get_session),
        location: Annotated[str | None, Query(max_length=100)] = None,
        price_min: Annotated[int | None, Query(ge=0)] = None,
        price_max: Annotated[int | None, Query(ge=0)] = None,
        bedrooms_min: Annotated[int | None, Query(ge=0, le=20)] = None,
        bedrooms_max: Annotated[int | None, Query(ge=0, le=20)] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 24,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        # Note: location filtering on listings table is approximate (matches against
        # `location_text`). Spec acknowledges the per-area pages live in the frontend
        # build (Plan 3) and use the location_slug from `locations.yml`.
        q = select(Listing).where(Listing.is_active.is_(True))
        count_q = select(func.count(Listing.id)).where(Listing.is_active.is_(True))

        if location is not None:
            ilike = f"%{location}%"
            q = q.where(Listing.location_text.ilike(ilike))
            count_q = count_q.where(Listing.location_text.ilike(ilike))
        if price_min is not None:
            q = q.where(Listing.price_eur >= price_min)
            count_q = count_q.where(Listing.price_eur >= price_min)
        if price_max is not None:
            q = q.where(Listing.price_eur <= price_max)
            count_q = count_q.where(Listing.price_eur <= price_max)
        if bedrooms_min is not None:
            cond = (Listing.bedrooms.is_(None)) | (Listing.bedrooms >= bedrooms_min)
            q = q.where(cond)
            count_q = count_q.where(cond)
        if bedrooms_max is not None:
            cond = (Listing.bedrooms.is_(None)) | (Listing.bedrooms <= bedrooms_max)
            q = q.where(cond)
            count_q = count_q.where(cond)

        total = session.scalar(count_q) or 0
        rows = session.scalars(
            q.order_by(Listing.first_seen_at.desc()).limit(limit).offset(offset)
        ).all()

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "listings": [_to_dict(row) for row in rows],
        }

    return r


def _to_dict(listing: Listing) -> dict[str, Any]:
    return {
        "id": listing.id,
        "external_id": listing.external_id,
        "url": listing.url,
        "title": listing.title,
        "price_eur": listing.price_eur,
        "bedrooms": listing.bedrooms,
        "area_m2": listing.area_m2,
        "location_text": listing.location_text,
        "first_seen_at": listing.first_seen_at.isoformat(),
        "last_seen_at": listing.last_seen_at.isoformat(),
    }
```

- [ ] **Step 2: Register router in `home_scanner/api/app.py`** — modify `build_app`:

Change the include block to:

```python
from home_scanner.api.healthz import build_router as build_healthz_router
from home_scanner.api.listings import build_router as build_listings_router

# inside build_app, after creating `app`:
app.include_router(build_healthz_router(session_factory))
app.include_router(build_listings_router(session_factory))
```

- [ ] **Step 3: Write `backend/tests/api/test_listings.py`**

```python
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from home_scanner.db.models import Listing
from sqlalchemy.orm import sessionmaker


def _make_listing(
    external_id: str,
    *,
    price: int = 800,
    bedrooms: int | None = 2,
    location: str | None = "Athens",
    is_active: bool = True,
    first_seen_at: datetime | None = None,
) -> Listing:
    now = datetime.now(UTC)
    return Listing(
        external_id=external_id,
        url=f"https://x/{external_id}",
        title=f"Listing {external_id}",
        price_eur=price,
        bedrooms=bedrooms,
        area_m2=60,
        location_text=location,
        first_seen_at=first_seen_at or now,
        last_seen_at=now,
        is_active=is_active,
    )


def test_listings_empty_returns_zero_total(api_client: TestClient):
    response = api_client.get("/listings")
    assert response.status_code == 200
    body = response.json()
    assert body == {"total": 0, "limit": 24, "offset": 0, "listings": []}


def test_listings_returns_active_only(api_client: TestClient, session_factory: sessionmaker):
    with session_factory() as s:
        s.add(_make_listing("a", is_active=True))
        s.add(_make_listing("b", is_active=False))
        s.commit()

    body = api_client.get("/listings").json()
    assert body["total"] == 1
    assert body["listings"][0]["external_id"] == "a"


def test_listings_price_filter(api_client: TestClient, session_factory: sessionmaker):
    with session_factory() as s:
        s.add(_make_listing("cheap", price=500))
        s.add(_make_listing("mid", price=800))
        s.add(_make_listing("expensive", price=1500))
        s.commit()

    body = api_client.get("/listings?price_min=600&price_max=1000").json()
    ids = sorted(l["external_id"] for l in body["listings"])
    assert ids == ["mid"]


def test_listings_bedrooms_filter_keeps_null(
    api_client: TestClient, session_factory: sessionmaker
):
    with session_factory() as s:
        s.add(_make_listing("br2", bedrooms=2))
        s.add(_make_listing("br_null", bedrooms=None))
        s.add(_make_listing("br1", bedrooms=1))
        s.commit()

    body = api_client.get("/listings?bedrooms_min=2").json()
    ids = sorted(l["external_id"] for l in body["listings"])
    assert ids == ["br2", "br_null"]


def test_listings_location_substring(
    api_client: TestClient, session_factory: sessionmaker
):
    with session_factory() as s:
        s.add(_make_listing("a", location="Athens Centre"))
        s.add(_make_listing("b", location="Marousi"))
        s.add(_make_listing("c", location="Athens, Pagrati"))
        s.commit()

    body = api_client.get("/listings?location=Athens").json()
    ids = sorted(l["external_id"] for l in body["listings"])
    assert ids == ["a", "c"]


def test_listings_pagination(api_client: TestClient, session_factory: sessionmaker):
    base = datetime.now(UTC)
    with session_factory() as s:
        for i in range(5):
            s.add(_make_listing(
                f"l{i}", price=800 + i,
                first_seen_at=base - timedelta(minutes=i),
            ))
        s.commit()

    body = api_client.get("/listings?limit=2&offset=0").json()
    assert body["total"] == 5
    assert len(body["listings"]) == 2
    # Ordered by first_seen_at desc → newest is l0
    assert body["listings"][0]["external_id"] == "l0"

    body2 = api_client.get("/listings?limit=2&offset=2").json()
    assert body2["listings"][0]["external_id"] == "l2"


def test_listings_invalid_query_param_rejected(api_client: TestClient):
    # bedrooms_max above 20 should 422 from FastAPI's validation
    response = api_client.get("/listings?bedrooms_max=99")
    assert response.status_code == 422
```

- [ ] **Step 4: Run tests, expect pass**

```bash
poetry run pytest tests/api/test_listings.py -v
```
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/home_scanner/api/listings.py backend/home_scanner/api/app.py backend/tests/api/test_listings.py
git commit -m "feat: add GET /listings with location/price/bedrooms filters and pagination"
```

### Important notes

- **`location_text` is free-form text from the spitogatos card** (e.g. "Exarcheia, Athens Centre"). The `ILIKE %query%` substring match is approximate but adequate for browse — the frontend can use `locations.yml` slugs for the canonical per-area pages later.
- **Bedroom-null pass-through:** the same null-aware logic from T11/T12 of Plan 1 — if Spitogatos didn't expose bedrooms, don't exclude.
- **`limit=24`** matches the wireframe's grid (3 columns × 8 rows).

---

## Phase C — Bot webhook + scrape endpoint

### Task 4: `POST /internal/scrape` with shared-secret auth

**Files:**
- Create: `backend/home_scanner/api/scrape.py`
- Modify: `backend/home_scanner/api/app.py`
- Create: `backend/tests/api/test_scrape.py`

- [ ] **Step 1: Implement `home_scanner/api/scrape.py`**

```python
"""POST /internal/scrape — bearer-secret-authenticated trigger for one scrape cycle.

Called by the GitHub Actions cron workflow. Runs the same notifier.runner cycle
that `python -m home_scanner scrape` does, just over HTTP.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from home_scanner.api.deps import make_get_session, require_scrape_secret
from home_scanner.bot.app import build_application
from home_scanner.notifier.runner import run_one_scrape_cycle
from home_scanner.scraper import SpitogatosClient, scrape_search
from home_scanner.settings import Settings

log = structlog.get_logger(__name__)


def build_router(session_factory) -> APIRouter:  # type: ignore[no-untyped-def]
    get_session = make_get_session(session_factory)
    r = APIRouter()

    @r.post("/internal/scrape", dependencies=[Depends(require_scrape_secret)])
    async def trigger_scrape(session: Session = Depends(get_session)) -> dict[str, Any]:
        settings = Settings()
        app = build_application(session_factory=session_factory)
        client = SpitogatosClient(proxy_url=settings.proxy_url)

        summary = await run_one_scrape_cycle(
            session=session,
            bot=app.bot,
            scrape_search_fn=scrape_search,
            client=client,
            now=datetime.now(UTC),
        )
        session.commit()

        log.info("api.scrape.done",
                 searches=summary.searches_processed,
                 listings=summary.listings_seen,
                 alerts=summary.new_alerts)

        return {
            "searches_processed": summary.searches_processed,
            "listings_seen": summary.listings_seen,
            "new_alerts": summary.new_alerts,
            "errors": summary.errors,
        }

    return r
```

- [ ] **Step 2: Register router in `home_scanner/api/app.py`** — add to the includes:

```python
from home_scanner.api.scrape import build_router as build_scrape_router
# ...
app.include_router(build_scrape_router(session_factory))
```

- [ ] **Step 3: Write `backend/tests/api/test_scrape.py`**

```python
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from home_scanner.db.repositories import create_saved_search, get_or_create_user
from home_scanner.scraper.models import ScrapedListing
from sqlalchemy.orm import Session, sessionmaker


def test_scrape_requires_authorization_header(api_client: TestClient, monkeypatch):
    monkeypatch.setenv("SCRAPE_SECRET", "test-secret")
    response = api_client.post("/internal/scrape")
    assert response.status_code == 401


def test_scrape_rejects_wrong_secret(api_client: TestClient, monkeypatch):
    monkeypatch.setenv("SCRAPE_SECRET", "test-secret")
    response = api_client.post(
        "/internal/scrape",
        headers={"Authorization": "Bearer wrong"},
    )
    assert response.status_code == 401


def test_scrape_returns_503_when_no_secret_configured(
    api_client: TestClient, monkeypatch
):
    monkeypatch.delenv("SCRAPE_SECRET", raising=False)
    response = api_client.post(
        "/internal/scrape",
        headers={"Authorization": "Bearer anything"},
    )
    assert response.status_code == 503


def test_scrape_executes_cycle_with_valid_secret(
    api_client: TestClient,
    db_session: Session,
    session_factory: sessionmaker,
    monkeypatch,
):
    monkeypatch.setenv("SCRAPE_SECRET", "test-secret")
    user = get_or_create_user(db_session, telegram_chat_id=42, telegram_username=None)
    create_saved_search(db_session, user_id=user.id, location_slug="marousi")
    db_session.commit()

    fake_listings = [
        ScrapedListing(
            external_id="ext-1", url="https://x/1", title="t",
            price_eur=900, bedrooms=2, area_m2=60, location_text="Marousi",
        )
    ]

    with patch(
        "home_scanner.api.scrape.scrape_search", return_value=fake_listings
    ), patch(
        "home_scanner.api.scrape.build_application"
    ) as mock_build:
        mock_app = mock_build.return_value
        mock_app.bot = AsyncMock()
        mock_app.bot.send_message.return_value.message_id = 1

        response = api_client.post(
            "/internal/scrape",
            headers={"Authorization": "Bearer test-secret"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["searches_processed"] == 1
    assert body["listings_seen"] == 1
    assert body["new_alerts"] == 1
```

- [ ] **Step 4: Run tests, expect pass**

```bash
poetry run pytest tests/api/test_scrape.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/home_scanner/api/scrape.py backend/home_scanner/api/app.py backend/tests/api/test_scrape.py
git commit -m "feat: add POST /internal/scrape with bearer-secret auth"
```

### Important notes

- **`monkeypatch.setenv("SCRAPE_SECRET", ...)`** sets the env var that `Settings()` reads when the `require_scrape_secret` dependency runs. Because `Settings()` reads env on each instantiation (no caching), this works without overriding `Depends(get_settings)`.
- **`patch("home_scanner.api.scrape.scrape_search")`** mocks the function as imported into `scrape.py`. Note the module path — patching the original definition in `home_scanner.scraper.service` would NOT take effect because `scrape.py` already re-imported the symbol.
- **`build_application` is mocked** because the real one would try to register polling-mode `Application` against the real Telegram API. We only need its `.bot` attribute to be an AsyncMock for `dispatch_alerts` to work.

---

### Task 5: `POST /webhook/telegram/<secret>` (bot webhook adapter)

**Files:**
- Create: `backend/home_scanner/api/telegram_webhook.py`
- Modify: `backend/home_scanner/bot/app.py` (split build into polling + webhook variants)
- Modify: `backend/home_scanner/api/app.py`
- Create: `backend/tests/api/test_telegram_webhook.py`

- [ ] **Step 1: Refactor `home_scanner/bot/app.py`** — split into two factories

Replace the existing single-function file with:

```python
"""telegram.ext.Application factories. Polling for local dev, webhook for prod."""
from __future__ import annotations

from sqlalchemy.orm import sessionmaker
from telegram.ext import Application, CommandHandler

from home_scanner.bot.handlers.list_searches import list_searches
from home_scanner.bot.handlers.manage import delete, pause, resume
from home_scanner.bot.handlers.new_search import build_handler as build_new_handler
from home_scanner.bot.handlers.start_help import help_cmd, start
from home_scanner.settings import Settings


def _register_handlers(app: Application, session_factory: sessionmaker) -> None:
    app.bot_data["session_factory"] = session_factory
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(build_new_handler())
    app.add_handler(CommandHandler("list", list_searches))
    app.add_handler(CommandHandler("pause", pause))
    app.add_handler(CommandHandler("resume", resume))
    app.add_handler(CommandHandler("delete", delete))


def build_application(*, session_factory: sessionmaker) -> Application:
    """Polling-mode Application — used by `python -m home_scanner bot` (local dev)."""
    settings = Settings()
    app = Application.builder().token(settings.telegram_bot_token).build()
    _register_handlers(app, session_factory)
    return app


async def build_webhook_application(*, session_factory: sessionmaker) -> Application:
    """Webhook-mode Application — initialized but NOT polling. The FastAPI
    /webhook/telegram/<secret> endpoint feeds it updates via app.process_update().

    Caller is responsible for `await app.initialize()` / `await app.shutdown()` —
    typically wired through FastAPI's lifespan."""
    settings = Settings()
    app = Application.builder().token(settings.telegram_bot_token).updater(None).build()
    _register_handlers(app, session_factory)
    return app
```

- [ ] **Step 2: Implement `home_scanner/api/telegram_webhook.py`**

```python
"""POST /webhook/telegram/<secret> — Telegram update webhook.

Telegram POSTs JSON-encoded Update objects to this URL. We dispatch them to the
shared `Application` instance which routes them to the registered handlers.

Auth: the secret is in the URL path (Telegram doesn't sign requests). Path is
non-guessable; verifying matching the configured TELEGRAM_WEBHOOK_SECRET on
each request prevents replay from leaked URLs.
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from telegram import Update
from telegram.ext import Application

from home_scanner.settings import Settings

log = structlog.get_logger(__name__)


def build_router(application: Application) -> APIRouter:
    r = APIRouter()
    settings = Settings()

    @r.post("/webhook/telegram/{secret}")
    async def telegram_webhook(secret: str, request: Request) -> dict[str, str]:
        if not settings.telegram_webhook_secret:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Webhook not configured",
            )
        if secret != settings.telegram_webhook_secret:
            log.warning("webhook.bad_secret")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        body = await request.json()
        update = Update.de_json(body, application.bot)
        if update is None:
            return {"status": "ignored"}

        await application.process_update(update)
        return {"status": "ok"}

    return r
```

- [ ] **Step 3: Update `home_scanner/api/app.py`** — wire bot Application via lifespan

Replace the lifespan and includes block:

```python
"""FastAPI application factory."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from sqlalchemy.orm import sessionmaker

from home_scanner.api.healthz import build_router as build_healthz_router
from home_scanner.api.listings import build_router as build_listings_router
from home_scanner.api.scrape import build_router as build_scrape_router
from home_scanner.api.telegram_webhook import build_router as build_webhook_router
from home_scanner.bot.app import build_webhook_application
from home_scanner.observability import init_sentry
from home_scanner.settings import Settings


def build_app(*, session_factory: sessionmaker) -> FastAPI:
    settings = Settings()
    init_sentry(dsn=settings.sentry_dsn)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        bot_app = await build_webhook_application(session_factory=session_factory)
        await bot_app.initialize()
        await bot_app.start()
        app.state.bot_application = bot_app

        # Register webhook router now that the Application exists
        app.include_router(build_webhook_router(bot_app))

        try:
            yield
        finally:
            await bot_app.stop()
            await bot_app.shutdown()

    app = FastAPI(title="home-scanner", lifespan=lifespan)
    app.state.session_factory = session_factory

    app.include_router(build_healthz_router(session_factory))
    app.include_router(build_listings_router(session_factory))
    app.include_router(build_scrape_router(session_factory))
    return app
```

- [ ] **Step 4: Write `backend/tests/api/test_telegram_webhook.py`**

```python
import pytest
from fastapi.testclient import TestClient


def test_webhook_requires_configured_secret(
    api_client: TestClient, monkeypatch
):
    monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)
    response = api_client.post("/webhook/telegram/anything", json={})
    assert response.status_code == 503


def test_webhook_rejects_wrong_secret(api_client: TestClient, monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "right-secret")
    response = api_client.post(
        "/webhook/telegram/wrong-secret", json={"update_id": 1}
    )
    assert response.status_code == 404


def test_webhook_accepts_valid_secret_with_unparseable_body(
    api_client: TestClient, monkeypatch
):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "right-secret")
    # Empty body → Update.de_json returns None → ignored without 500
    response = api_client.post(
        "/webhook/telegram/right-secret", json={}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
```

- [ ] **Step 5: Run tests, expect pass**

```bash
poetry run pytest tests/api/test_telegram_webhook.py -v
```
Expected: 3 passed.

- [ ] **Step 6: Run the FULL suite to make sure the bot/app.py refactor didn't break Plan 1 tests**

```bash
poetry run pytest -q
```
Expected: all prior 52 + 5 healthz + 7 listings + 4 scrape + 3 webhook = 71 tests passing.

If any Plan 1 bot tests fail, the most likely cause is the renamed import paths in `bot/app.py`. Fix imports and rerun.

- [ ] **Step 7: Commit**

```bash
git add backend/home_scanner/api/telegram_webhook.py backend/home_scanner/api/app.py backend/home_scanner/bot/app.py backend/tests/api/test_telegram_webhook.py
git commit -m "feat: add Telegram webhook endpoint and split bot app into polling/webhook factories"
```

### Important notes

- **`Updater(None)`** in `build_webhook_application` disables python-telegram-bot's built-in polling loop. The FastAPI app drives updates via `process_update()`.
- **`Application.start()` is required** — even in webhook mode it kicks off the per-handler queues and `bot_data` initialization.
- **Webhook route is added inside lifespan** because it depends on the Application instance, which is built when the app starts. This is unusual but FastAPI handles it cleanly.
- **`Update.de_json` returns None on empty/malformed input** — handled by returning `{"status": "ignored"}` rather than 400, because Telegram retries 400-class responses.

---

## Phase D — Containerise & deploy

### Task 6: CLI `serve` subcommand + Dockerfile

**Files:**
- Modify: `backend/home_scanner/cli.py`
- Create: `backend/Dockerfile`

- [ ] **Step 1: Add `serve` subcommand to `home_scanner/cli.py`**

Replace the body of `cli.py` with:

```python
"""CLI entrypoints. Run with `poetry run python -m home_scanner <command>`.

Subcommands:
- scrape: Run one full scrape cycle synchronously, then exit
- bot:    Start the Telegram bot in long-polling mode (local dev; blocks)
- serve:  Start the FastAPI HTTP server via uvicorn (production)
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime

import uvicorn

from home_scanner.api import build_app
from home_scanner.bot.app import build_application
from home_scanner.db.session import make_engine, make_session_factory
from home_scanner.logging import configure as configure_logging
from home_scanner.logging import new_correlation_id
from home_scanner.notifier.runner import run_one_scrape_cycle
from home_scanner.scraper import SpitogatosClient, scrape_search
from home_scanner.settings import Settings


async def _scrape_once() -> None:
    settings = Settings()
    new_correlation_id()
    engine = make_engine(settings.database_url)
    sf = make_session_factory(engine)
    app = build_application(session_factory=sf)
    client = SpitogatosClient(proxy_url=settings.proxy_url)
    with sf() as session:
        await run_one_scrape_cycle(
            session=session,
            bot=app.bot,
            scrape_search_fn=scrape_search,
            client=client,
            now=datetime.now(UTC),
        )
        session.commit()


def _run_bot() -> None:
    settings = Settings()
    engine = make_engine(settings.database_url)
    sf = make_session_factory(engine)
    app = build_application(session_factory=sf)
    app.run_polling()


def _run_serve(host: str, port: int) -> None:
    settings = Settings()
    engine = make_engine(settings.database_url)
    sf = make_session_factory(engine)
    fastapi_app = build_app(session_factory=sf)
    uvicorn.run(fastapi_app, host=host, port=port, log_level=settings.log_level.lower())


def main() -> None:
    parser = argparse.ArgumentParser(prog="home-scanner")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("scrape", help="Run one scrape cycle, then exit")
    sub.add_parser("bot", help="Run the Telegram bot in long-polling mode")
    serve_parser = sub.add_parser("serve", help="Run the FastAPI HTTP server")
    serve_parser.add_argument("--host", default="0.0.0.0")  # noqa: S104
    serve_parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    configure_logging(Settings().log_level)

    if args.cmd == "scrape":
        asyncio.run(_scrape_once())
    elif args.cmd == "bot":
        _run_bot()
    elif args.cmd == "serve":
        _run_serve(args.host, args.port)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create `backend/Dockerfile`**

```dockerfile
# syntax=docker/dockerfile:1.7
FROM python:3.12-slim

# Install Poetry
ENV POETRY_VERSION=1.8.5 \
    POETRY_HOME=/opt/poetry \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry \
    && apt-get purge -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first (cached layer)
COPY pyproject.toml ./
COPY README.md ../README.md
RUN poetry install --only main --no-root

# Copy code
COPY home_scanner/ ./home_scanner/
COPY alembic.ini ./
COPY alembic/ ./alembic/

RUN poetry install --only main

# Fly.io provides PORT env var; default to 8080 for local docker run
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "python -m home_scanner serve --port ${PORT}"]
```

- [ ] **Step 3: Build the image locally and verify**

```bash
cd backend
docker build -t home-scanner:dev .
```
Expected: build completes; final image is in the 200–400 MB range.

Then verify the image starts (will fail without env vars but should at least exit cleanly):

```bash
docker run --rm home-scanner:dev python -c "from home_scanner.api import build_app; print('ok')"
```
Expected: `ok`.

- [ ] **Step 4: Run the test suite to verify the CLI changes didn't regress anything**

```bash
poetry run pytest -q
```
Expected: 71 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/home_scanner/cli.py backend/Dockerfile
git commit -m "feat: add CLI serve subcommand and production Dockerfile"
```

### Important notes

- **`POETRY_VIRTUALENVS_CREATE=false`** installs deps directly into the system Python — fine inside an ephemeral container, no isolation needed.
- **`COPY README.md ../README.md`** — pyproject.toml's `readme = "../README.md"` references it; without this copy, `poetry install` complains. The "../" path is relative to the `pyproject.toml` location, which lives in `/app/` after the COPY. Ugly but works.
- **`# noqa: S104`** suppresses Bandit's "binding to 0.0.0.0" warning — required for Fly.io which routes from the gateway's address, not localhost.

---

### Task 7: `fly.toml` + Fly.io deploy steps in README

**Files:**
- Create: `backend/fly.toml`
- Modify: `README.md` (add deploy section)

- [ ] **Step 1: Create `backend/fly.toml`**

```toml
# Fly.io config — see https://fly.io/docs/reference/configuration/

app = "home-scanner"
primary_region = "fra"  # Frankfurt — close to Greek users; pick another if relevant

[build]
  dockerfile = "Dockerfile"

[deploy]
  # Apply migrations on every deploy
  release_command = "alembic upgrade head"

[env]
  PORT = "8080"
  LOG_LEVEL = "INFO"

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = "stop"
  auto_start_machines = true
  min_machines_running = 0
  processes = ["app"]

  [[http_service.checks]]
    interval = "30s"
    timeout = "5s"
    grace_period = "10s"
    method = "GET"
    path = "/healthz"

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 256
```

**IMPORTANT:** the `app = "home-scanner"` line will collide if someone else owns that name. Replace with `home-scanner-<your-handle>` if `flyctl deploy` rejects it.

- [ ] **Step 2: Add a Deploy section to root `README.md`**

Append below the existing "Tests" section:

```markdown
## Deploy (Plan 2)

Requirements: a [Fly.io account](https://fly.io), `flyctl` installed, a [Neon](https://neon.tech) Postgres database (free tier), an [Upptime](https://upptime.js.org)/[BetterStack](https://betterstack.com) uptime monitor URL (optional), a [Sentry](https://sentry.io) project (optional), all credentials populated locally first per "Local setup".

### One-time setup

```bash
cd backend

# Create the Fly app
flyctl apps create home-scanner   # change name if collided

# Set secrets (these become env vars in the running container)
flyctl secrets set \
  DATAIMPULSE_USER=... \
  DATAIMPULSE_PASS=... \
  DATAIMPULSE_HOST=gw.dataimpulse.com \
  DATAIMPULSE_PORT=823 \
  DATABASE_URL=postgresql+psycopg://USER:PASS@HOST/DB \
  TELEGRAM_BOT_TOKEN=... \
  SCRAPE_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" \
  TELEGRAM_WEBHOOK_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" \
  SENTRY_DSN=... \
  PUBLIC_BASE_URL=https://home-scanner.fly.dev

# First deploy (will run alembic upgrade head as release_command)
flyctl deploy

# Register the webhook URL with Telegram (one-shot)
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook?url=https://home-scanner.fly.dev/webhook/telegram/${TELEGRAM_WEBHOOK_SECRET}"
```

### Subsequent deploys

```bash
cd backend && flyctl deploy
```

The release_command (`alembic upgrade head`) runs first; if migrations fail the deploy is aborted and the previous version stays serving.

### Verify

```bash
curl https://home-scanner.fly.dev/healthz
# → {"status": "down" or "ok", ...}

curl -H "Authorization: Bearer $SCRAPE_SECRET" -X POST https://home-scanner.fly.dev/internal/scrape
# → {"searches_processed": 0, ...} on first run
```
```

- [ ] **Step 3: Commit**

```bash
git add backend/fly.toml README.md
git commit -m "feat: add fly.toml and deploy documentation"
```

### Important notes

- **`min_machines_running = 0` + `auto_stop_machines = "stop"`** is the scale-to-zero magic. The machine stops after ~5min idle and re-wakes on incoming traffic.
- **`release_command`** runs in a fresh ephemeral machine before the new version goes live. Alembic uses `DATABASE_URL` from secrets.
- **`primary_region = "fra"`** keeps round-trip to Greek users low. If you're elsewhere, see https://fly.io/docs/reference/regions/.
- **Webhook registration is a one-shot curl** — Telegram remembers the URL until you change it. If you redeploy with a different `TELEGRAM_WEBHOOK_SECRET`, re-run the `setWebhook` curl.

---

## Phase E — CI/cron/canary

### Task 8: GitHub Actions hourly scrape cron

**Files:**
- Create: `.github/workflows/scrape.yml`

- [ ] **Step 1: Create `.github/workflows/scrape.yml`**

```yaml
name: hourly-scrape

on:
  schedule:
    - cron: "0 * * * *"  # Top of every hour
  workflow_dispatch:      # Manual trigger button in the Actions UI

jobs:
  trigger:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - name: Trigger /internal/scrape
        env:
          APP_URL: ${{ secrets.APP_URL }}              # e.g. https://home-scanner.fly.dev
          SCRAPE_SECRET: ${{ secrets.SCRAPE_SECRET }}
        run: |
          set -euo pipefail
          response=$(curl -fsS \
            -X POST "$APP_URL/internal/scrape" \
            -H "Authorization: Bearer $SCRAPE_SECRET" \
            -w "\nHTTP %{http_code}\n")
          echo "$response"
```

- [ ] **Step 2: Document the required GitHub Actions secrets in the README**

In `README.md`'s Deploy section, append:

```markdown
### GitHub Actions secrets (for cron + CI)

In your repo's Settings → Secrets and variables → Actions, add:

- `APP_URL` — public URL of the deployed app (e.g. `https://home-scanner.fly.dev`)
- `SCRAPE_SECRET` — same value used in `flyctl secrets set SCRAPE_SECRET=...`
- `FLY_API_TOKEN` — for CI deploy hooks (Plan 2 doesn't auto-deploy from CI; reserved for v2)
```

- [ ] **Step 3: Validate the workflow YAML locally**

```bash
# Either install actionlint (https://github.com/rhysd/actionlint) or use the GitHub UI
# to lint after pushing. For a quick syntax check:
python -c "import yaml; yaml.safe_load(open('.github/workflows/scrape.yml'))"
```
Expected: no exception.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/scrape.yml README.md
git commit -m "ci: add hourly scrape cron workflow"
```

### Important notes

- **GitHub Actions cron runs on UTC** and is best-effort — drift of 5–15 minutes under platform load is normal. Acceptable given the 1-hour cadence target from the spec.
- **`workflow_dispatch`** lets you manually trigger a scrape from the Actions UI without waiting for the next cron tick. Useful during deploys.
- **60-day inactivity caveat:** GitHub auto-disables Actions schedules on repos with no commits for 60 days. Dependabot's monthly PRs (set up by default on most public repos) keep the repo "active" and prevent this.

---

### Task 9: GitHub Actions CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create `.github/workflows/ci.yml`**

```yaml
name: ci

on:
  pull_request:
  push:
    branches: [main]

jobs:
  backend:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: home_scanner
          POSTGRES_PASSWORD: home_scanner
          POSTGRES_DB: home_scanner
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U home_scanner"
          --health-interval 5s
          --health-timeout 3s
          --health-retries 10
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install Poetry
        run: pipx install poetry==1.8.5

      - name: Cache Poetry dependencies
        uses: actions/cache@v4
        with:
          path: ~/.cache/pypoetry
          key: poetry-${{ runner.os }}-${{ hashFiles('backend/poetry.lock') }}

      - name: Install deps
        working-directory: backend
        run: poetry install --no-root

      - name: Lint
        working-directory: backend
        run: poetry run ruff check .

      - name: Test
        working-directory: backend
        env:
          DATAIMPULSE_USER: ci
          DATAIMPULSE_PASS: ci
          DATAIMPULSE_HOST: localhost
          DATAIMPULSE_PORT: "1080"
          DATABASE_URL: postgresql+psycopg://home_scanner:home_scanner@localhost:5432/home_scanner
          TELEGRAM_BOT_TOKEN: ci-test-token
        run: poetry run pytest -v
```

- [ ] **Step 2: Validate**

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add lint+test workflow on PR and push to main"
```

### Important notes

- **Postgres-as-service** in CI replaces the local testcontainer. The `DATABASE_URL` env var points at it; test code uses the same `db_session` fixture but the underlying engine is the CI-provided container. Existing tests should pass without modification.
- **Ruff lint is non-blocking warning today** (we cleaned everything up at end of Plan 1, so ruff check passes). If a future PR introduces a lint violation, CI will fail — that's the intended behaviour.
- **Mypy is omitted from CI** because strict mode still has unresolved errors after Plan 1's removal of the broken pydantic plugin. Add `poetry run mypy home_scanner` as a CI step in a follow-up PR once those are addressed.

---

### Task 10: Daily live canary workflow

**Files:**
- Create: `.github/workflows/daily-canary.yml`
- Create: `backend/scripts/canary.py`

- [ ] **Step 1: Implement `backend/scripts/canary.py`**

```python
"""Live Spitogatos parser canary.

Hits a known-busy rental search URL through DataImpulse and asserts the parser
returns at least N listings. Run from CI; non-zero exit if the assertion fails.

Per spec §9, this is the alarm that catches Spitogatos HTML changes within 24h
rather than weeks.
"""
from __future__ import annotations

import sys

from home_scanner.scraper import SearchFilter, SpitogatosClient, scrape_search
from home_scanner.settings import Settings

MIN_EXPECTED_LISTINGS = 10
CANARY_LOCATION = "athina-kentro"  # Always-busy reference search


def main() -> int:
    settings = Settings()
    client = SpitogatosClient(proxy_url=settings.proxy_url)
    f = SearchFilter(location_slug=CANARY_LOCATION)

    listings = scrape_search(f, client=client)
    print(f"canary: parsed {len(listings)} listings from {CANARY_LOCATION}")

    if len(listings) < MIN_EXPECTED_LISTINGS:
        print(
            f"canary: FAIL — expected at least {MIN_EXPECTED_LISTINGS}, got {len(listings)}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Create `.github/workflows/daily-canary.yml`**

```yaml
name: daily-canary

on:
  schedule:
    - cron: "0 6 * * *"  # 06:00 UTC daily
  workflow_dispatch:

jobs:
  parse-canary:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install Poetry
        run: pipx install poetry==1.8.5

      - name: Install deps
        working-directory: backend
        run: poetry install --only main --no-root

      - name: Run canary
        working-directory: backend
        env:
          DATAIMPULSE_USER: ${{ secrets.DATAIMPULSE_USER }}
          DATAIMPULSE_PASS: ${{ secrets.DATAIMPULSE_PASS }}
          DATAIMPULSE_HOST: ${{ secrets.DATAIMPULSE_HOST }}
          DATAIMPULSE_PORT: ${{ secrets.DATAIMPULSE_PORT }}
          DATABASE_URL: postgresql+psycopg://placeholder:placeholder@localhost/placeholder
          TELEGRAM_BOT_TOKEN: placeholder
        run: poetry run python scripts/canary.py

      - name: Open issue on failure
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            const today = new Date().toISOString().slice(0, 10);
            await github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: `[canary] Spitogatos parser broken on ${today}`,
              body: `Daily canary failed: parser returned fewer than ${10} listings for athina-kentro.\n\nSpitogatos HTML may have changed. Investigate \`backend/home_scanner/scraper/parser.py\`.\n\nLog: ${context.serverUrl}/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId}`,
              labels: ['canary', 'bug'],
            });
```

- [ ] **Step 3: Validate**

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/daily-canary.yml'))"
```

- [ ] **Step 4: Commit**

```bash
git add backend/scripts/canary.py .github/workflows/daily-canary.yml
git commit -m "ci: add daily live canary that opens an issue on parser breakage"
```

### Important notes

- **Required GitHub secrets:** `DATAIMPULSE_USER`, `DATAIMPULSE_PASS`, `DATAIMPULSE_HOST`, `DATAIMPULSE_PORT` — same values from `flyctl secrets set`. Add them in the repo's Actions secrets.
- **`actions/github-script@v7`** auto-generates an issue creation event using the workflow's `GITHUB_TOKEN` — no extra credentials needed.
- **Placeholder DB/Telegram env vars** are needed because `Settings()` is strict; the canary script never connects to either. Acceptable.

---

## Phase F — Polish

### Task 11: README polish + final smoke test

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update the `## Status` section in `README.md`**

Replace:
```markdown
## Status

Backend MVP complete (see [`docs/superpowers/specs/...`]).

Plan 2 (production deploy) and Plan 3 (Next.js frontend) are upcoming.
```

With:
```markdown
## Status

- ✅ **Plan 1 — Backend MVP** complete
- ✅ **Plan 2 — Production deploy** complete (FastAPI, Fly.io, GitHub Actions cron + CI + canary)
- 🔜 **Plan 3 — Next.js frontend** upcoming

See `docs/superpowers/specs/2026-05-08-home-scanner-portfolio-design.md` for the full design and `docs/superpowers/plans/` for build plans.
```

- [ ] **Step 2: Manual smoke test of deployed app**

After running `flyctl deploy`, run through the following:

1. `curl https://home-scanner.fly.dev/healthz` → returns 200
2. `curl https://home-scanner.fly.dev/listings` → returns `{"total": 0, ...}` initially
3. Open Telegram, send `/start` to your bot → receive welcome message (proves webhook works)
4. Run `/new` flow with location "Athens centre" → bot saves the search and replies with cold-start digest
5. Trigger an out-of-band scrape: `curl -H "Authorization: Bearer $SCRAPE_SECRET" -X POST https://home-scanner.fly.dev/internal/scrape` → returns summary JSON
6. Wait for or manually trigger the GitHub Actions hourly-scrape workflow → verify in the Actions tab that it 200s

If any step fails, debug locally (`flyctl logs`, `flyctl ssh console`), fix, redeploy.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: mark Plan 2 complete in README status"
```

---

## Self-review

After writing the plan, fresh-eyes pass:

**1. Spec coverage:**
- §4 Architecture: FastAPI endpoints (`/listings`, `/healthz`, `/webhook/telegram/<secret>`, `/internal/scrape`) — covered by T2, T3, T4, T5.
- §4 Deploy: Fly.io scale-to-zero — covered by T7. Webhook secret in URL path — T5. GitHub Actions cron — T8. Auto-pause Neon — documented in T7's README.
- §4 Operational costs: not directly buildable, but T7's README captures the actual setup.
- §8 Sentry — covered by T1. Circuit breaker on 5 consecutive 403/429s — **NOT in this plan**. Already partially in Plan 1 (the per-search isolation), but the "5 consecutive runs → circuit-broken state" needs a counter persisted somewhere. **Adding as future v2 concern, not blocking**.
- §8 Secrets discipline (Fly secrets, no `config.py`) — covered by T7's README.
- §9 CI workflow — T9. Daily canary — T10.

**2. Placeholder scan:** none. Every step has full code or full commands.

**3. Type consistency:**
- `build_router(session_factory)` signature consistent across `healthz.py`, `listings.py`, `scrape.py` (T2/T3/T4).
- `build_router(application)` signature in `telegram_webhook.py` is different — takes the bot Application, not the session_factory. Documented in the task's "Important notes". Intentional.
- `build_application` (polling) and `build_webhook_application` (webhook) — naming distinct. Both accept `session_factory`. ✓
- `Settings.scrape_secret`, `Settings.telegram_webhook_secret`, `Settings.sentry_dsn`, `Settings.public_base_url` introduced in T1, used in T4/T5/T1/T7. ✓

**4. Gap caught:** `Update.de_json` requires the bot — but in T5's webhook test, we don't pass an Application instance. The TestClient lifespan SHOULD initialise the bot Application (via T5's modified `build_app` lifespan). Verified by reading T5 Step 3 again — yes, the lifespan creates the bot_app and includes the webhook router. The test fixture `api_client` uses a `with TestClient(api_app):` block which triggers lifespan startup/shutdown. Good.

**5. Migration safety:** `release_command = "alembic upgrade head"` in `fly.toml` runs migrations on every deploy. If a migration is broken, the new version doesn't go live — the previous version keeps serving. Safe.

No issues found.
