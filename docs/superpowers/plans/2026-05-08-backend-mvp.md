# Backend MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the home-scanner backend MVP end-to-end runnable on a developer's laptop — Spitogatos scraper, Postgres-backed data model, Telegram bot with `/new` wizard, alert notifier, and a CLI entrypoint that performs a hand-triggered hourly scrape.

**Architecture:** Single Python package `home_scanner` containing five modules — `scraper`, `db`, `bot`, `notifier`, plus a thin CLI. SQLAlchemy + Alembic for persistence, `python-telegram-bot` (long-polling for local dev — webhook adapter comes in Plan 2), `tenacity` for retries, `respx` for HTTP mocking in tests, `testcontainers` for Postgres-backed integration tests.

**Tech Stack:** Python 3.12, Poetry, SQLAlchemy 2, Alembic, Postgres, `python-telegram-bot` ≥21, `httpx`, `beautifulsoup4`, `tenacity`, `pyyaml`, `rapidfuzz`, `structlog`, `pytest`, `pytest-asyncio`, `respx`, `testcontainers[postgresql]`, `ruff`, `mypy`.

**Spec reference:** `docs/superpowers/specs/2026-05-08-home-scanner-portfolio-design.md`.

**Out of scope for this plan (deferred to Plans 2–3):** FastAPI HTTP service, `/internal/scrape` and `/webhook/telegram` endpoints, Fly.io deploy, GitHub Actions cron, Sentry wiring, frontend.

---

## File structure (target after Plan 1)

```
home-scanner/
├── README.md                              # Updated with setup + run instructions
├── .gitignore
├── docs/
├── backend/
│   ├── pyproject.toml                     # Replaces root pyproject.toml. Adds ruff/mypy/pytest tooling
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 0001_initial_schema.py
│   ├── home_scanner/
│   │   ├── __init__.py
│   │   ├── settings.py                    # Env-var-based config (replaces config.py)
│   │   ├── locations.yml                  # Greek areas → Spitogatos slugs (seed data)
│   │   ├── locations.py                   # Loader + fuzzy matcher
│   │   ├── logging.py                     # structlog setup + correlation IDs
│   │   ├── cli.py                         # `python -m home_scanner ...` entrypoint
│   │   ├── scraper/
│   │   │   ├── __init__.py
│   │   │   ├── models.py                  # ScrapedListing dataclass
│   │   │   ├── search_url.py              # Build Spitogatos URLs from filters
│   │   │   ├── parser.py                  # HTML → list[ScrapedListing]
│   │   │   ├── client.py                  # httpx + DataImpulse proxy + retries
│   │   │   └── service.py                 # Orchestrate URL → fetch → parse
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── models.py                  # SQLAlchemy ORM (5 tables)
│   │   │   ├── session.py                 # Engine + sessionmaker
│   │   │   └── repositories.py            # CRUD helpers
│   │   ├── bot/
│   │   │   ├── __init__.py
│   │   │   ├── app.py                     # Build telegram.ext.Application (polling)
│   │   │   ├── messages.py                # Outgoing-message formatters
│   │   │   └── handlers/
│   │   │       ├── __init__.py
│   │   │       ├── start_help.py          # /start + /help
│   │   │       ├── new_search.py          # /new ConversationHandler
│   │   │       ├── list_searches.py       # /list with inline keyboard
│   │   │       └── manage.py              # /pause /resume /delete
│   │   └── notifier/
│   │       ├── __init__.py
│   │       ├── diff.py                    # Pure: compute alerts to send
│   │       ├── dispatch.py                # Send Telegram messages, write alerts_sent
│   │       └── runner.py                  # Top-level: scrape → diff → dispatch
│   ├── .env.example
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py                    # Postgres container, factories, async loop
│       ├── fixtures/
│       │   └── spitogatos/
│       │       ├── athens-centre-page1.html
│       │       ├── studio.html
│       │       ├── missing-bedrooms.html
│       │       └── empty-results.html
│       ├── test_locations.py
│       ├── scraper/
│       │   ├── test_search_url.py
│       │   ├── test_parser.py
│       │   ├── test_client.py
│       │   └── test_service.py
│       ├── db/
│       │   ├── test_models.py
│       │   └── test_repositories.py
│       ├── notifier/
│       │   ├── test_diff.py
│       │   ├── test_dispatch.py
│       │   └── test_runner.py
│       └── bot/
│           ├── test_new_wizard.py
│           ├── test_list_searches.py
│           └── test_manage.py
```

**Files retired:**
- `main.py` (root) — content moves into `backend/home_scanner/scraper/`.
- `pyproject.toml` (root) — replaced by `backend/pyproject.toml`.
- `config.py` pattern — superseded by env vars + `home_scanner.settings`.

---

## Task list

The plan has 20 tasks across 7 phases. Run them in order.

| Phase | Tasks |
|---|---|
| A — Foundation | T1, T2, T3, T4 |
| B — Scraper | T5, T6, T7, T8 |
| C — DB layer | T9, T10, T11 |
| D — Notifier | T12, T13, T14 |
| E — Bot | T15, T16, T17, T18 |
| F — Wire-up | T19 |
| G — Polish | T20 |

---

## Phase A — Foundation

### Task 1: Restructure repo into `backend/` and modernize tooling

**Files:**
- Move: `pyproject.toml` → `backend/pyproject.toml` (rewrite contents per below)
- Move: `main.py` content → reference for Task 6 (parser); root `main.py` deleted
- Create: `backend/.env.example`
- Modify: `.gitignore` (add `.env`, `backend/.env`)

- [ ] **Step 1: Create `backend/` directory and move root pyproject.toml in**

```bash
cd /Users/giorgos/Projects/home-scanner
mkdir -p backend
git mv pyproject.toml backend/pyproject.toml
```

- [ ] **Step 2: Replace `backend/pyproject.toml` with the modernized version**

```toml
[tool.poetry]
name = "home-scanner"
version = "0.1.0"
description = "Telegram alerts for new Greek apartment rentals on spitogatos.gr"
authors = ["Giorgos Kallis <giorgos.kallis.gr@gmail.com>"]
readme = "../README.md"
package-mode = true
packages = [{include = "home_scanner"}]

[tool.poetry.dependencies]
python = "^3.12"
httpx = "^0.27"
beautifulsoup4 = "^4.12"
sqlalchemy = "^2.0"
alembic = "^1.13"
"psycopg[binary]" = "^3.2"
"python-telegram-bot" = {extras = ["job-queue"], version = "^21"}
tenacity = "^9.0"
pyyaml = "^6.0"
rapidfuzz = "^3.10"
structlog = "^24.4"
python-dotenv = "^1.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.3"
pytest-asyncio = "^0.24"
respx = "^0.22"
"testcontainers" = {extras = ["postgresql"], version = "^4.8"}
ruff = "^0.8"
mypy = "^1.13"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "C4", "SIM", "RUF"]

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

- [ ] **Step 3: Create `backend/.env.example`**

```bash
# DataImpulse proxy credentials (https://dataimpulse.com)
DATAIMPULSE_USER=
DATAIMPULSE_PASS=
DATAIMPULSE_HOST=gw.dataimpulse.com
DATAIMPULSE_PORT=823

# Postgres (local dev: use docker postgres or a Neon dev branch)
DATABASE_URL=postgresql+psycopg://home_scanner:home_scanner@localhost:5432/home_scanner

# Telegram bot token from @BotFather
TELEGRAM_BOT_TOKEN=

# Logging
LOG_LEVEL=INFO
```

- [ ] **Step 4: Update `.gitignore` to ignore `.env` files**

Modify `.gitignore`, add:
```
.env
backend/.env
.venv/
backend/.venv/
```

- [ ] **Step 5: Delete the now-stale root `main.py` (content preserved in git history; will reappear inside the parser in T6)**

```bash
git rm main.py
```

- [ ] **Step 6: Bootstrap empty package**

```bash
mkdir -p backend/home_scanner backend/tests
touch backend/home_scanner/__init__.py backend/tests/__init__.py
```

Set `backend/home_scanner/__init__.py` to:
```python
"""home-scanner: Telegram alerts for new Greek rentals on spitogatos.gr."""

__version__ = "0.1.0"
```

- [ ] **Step 7: Install deps and verify**

```bash
cd backend
poetry install
poetry run python -c "import home_scanner; print(home_scanner.__version__)"
```
Expected: `0.1.0`.

- [ ] **Step 8: Commit**

```bash
git add backend .gitignore
git commit -m "refactor: restructure project under backend/ with modern Python tooling"
```

---

### Task 2: Settings module (env-var-based config)

**Files:**
- Create: `backend/home_scanner/settings.py`
- Create: `backend/tests/test_settings.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_settings.py`:
```python
import pytest
from home_scanner.settings import Settings


def test_loads_required_env_vars(monkeypatch):
    monkeypatch.setenv("DATAIMPULSE_USER", "u")
    monkeypatch.setenv("DATAIMPULSE_PASS", "p")
    monkeypatch.setenv("DATAIMPULSE_HOST", "gw.example.com")
    monkeypatch.setenv("DATAIMPULSE_PORT", "823")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@h:5432/db")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")

    s = Settings()

    assert s.dataimpulse_user == "u"
    assert s.proxy_url == "http://u:p@gw.example.com:823"
    assert s.database_url == "postgresql+psycopg://u:p@h:5432/db"
    assert s.telegram_bot_token == "t"
    assert s.log_level == "INFO"  # default


def test_raises_on_missing_required(monkeypatch):
    monkeypatch.delenv("DATAIMPULSE_USER", raising=False)
    with pytest.raises(KeyError):
        Settings()
```

- [ ] **Step 2: Run the test, expect failure**

```bash
cd backend && poetry run pytest tests/test_settings.py -v
```
Expected: ImportError — module doesn't exist.

- [ ] **Step 3: Implement `home_scanner/settings.py`**

```python
"""Centralised settings, loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()  # No-op in production; reads .env in local dev


@dataclass(frozen=True, slots=True)
class Settings:
    dataimpulse_user: str
    dataimpulse_pass: str
    dataimpulse_host: str
    dataimpulse_port: str
    database_url: str
    telegram_bot_token: str
    log_level: str = "INFO"

    def __init__(self) -> None:  # type: ignore[no-redef]
        # frozen dataclass + env-driven init: bypass __setattr__ via object.__setattr__
        object.__setattr__(self, "dataimpulse_user", os.environ["DATAIMPULSE_USER"])
        object.__setattr__(self, "dataimpulse_pass", os.environ["DATAIMPULSE_PASS"])
        object.__setattr__(self, "dataimpulse_host", os.environ["DATAIMPULSE_HOST"])
        object.__setattr__(self, "dataimpulse_port", os.environ["DATAIMPULSE_PORT"])
        object.__setattr__(self, "database_url", os.environ["DATABASE_URL"])
        object.__setattr__(self, "telegram_bot_token", os.environ["TELEGRAM_BOT_TOKEN"])
        object.__setattr__(self, "log_level", os.environ.get("LOG_LEVEL", "INFO"))

    @property
    def proxy_url(self) -> str:
        return (
            f"http://{self.dataimpulse_user}:{self.dataimpulse_pass}"
            f"@{self.dataimpulse_host}:{self.dataimpulse_port}"
        )
```

- [ ] **Step 4: Run tests, expect pass**

```bash
poetry run pytest tests/test_settings.py -v
```
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/home_scanner/settings.py backend/tests/test_settings.py
git commit -m "feat: add Settings module loading from environment variables"
```

---

### Task 3: Locations registry — YAML + fuzzy matcher

**Files:**
- Create: `backend/home_scanner/locations.yml`
- Create: `backend/home_scanner/locations.py`
- Create: `backend/tests/test_locations.py`

- [ ] **Step 1: Create `backend/home_scanner/locations.yml` with seed data**

```yaml
# Greek apartment search locations → spitogatos.gr URL slugs.
# Add entries via PR. Slug must match the trailing path segment in the spitogatos URL.

# Major cities
- name: "Athens"
  aliases: ["athina", "αθήνα"]
  slug: "athens"
- name: "Athens Centre"
  aliases: ["athens center", "athina kentro", "kentro athinas", "αθήνα κέντρο"]
  slug: "athina-kentro"
- name: "Thessaloniki"
  aliases: ["thessaloniki", "θεσσαλονίκη"]
  slug: "thessaloniki"
- name: "Thessaloniki Centre"
  aliases: ["thessaloniki kentro", "θεσσαλονίκη κέντρο"]
  slug: "thessaloniki-kentro"
- name: "Patras"
  aliases: ["patra", "πάτρα"]
  slug: "patra"
- name: "Heraklion"
  aliases: ["iraklio", "ηράκλειο"]
  slug: "iraklio"
- name: "Larissa"
  aliases: ["larisa", "λάρισα"]
  slug: "larisa"

# Athens neighbourhoods (sample seed; extend as needed)
- name: "Marousi"
  aliases: ["maroussi", "μαρούσι"]
  slug: "marousi"
- name: "Nea Smyrni"
  aliases: ["nea smirni", "νέα σμύρνη"]
  slug: "nea-smyrni"
- name: "Kallithea"
  aliases: ["kallithéa", "καλλιθέα"]
  slug: "kallithea"
- name: "Pagrati"
  aliases: ["pangrati", "παγκράτι"]
  slug: "pagrati"
- name: "Exarcheia"
  aliases: ["exarchia", "εξάρχεια"]
  slug: "exarcheia"
- name: "Koukaki"
  aliases: ["κουκάκι"]
  slug: "koukaki"
- name: "Kolonaki"
  aliases: ["κολωνάκι"]
  slug: "kolonaki"
- name: "Glyfada"
  aliases: ["glifada", "γλυφάδα"]
  slug: "glyfada"
- name: "Piraeus"
  aliases: ["pireas", "πειραιάς"]
  slug: "pireas"
```

- [ ] **Step 2: Write the failing test**

`backend/tests/test_locations.py`:
```python
import pytest
from home_scanner.locations import Location, find_locations, load_locations


def test_load_locations_returns_list_of_location():
    locs = load_locations()
    assert len(locs) > 10
    assert all(isinstance(loc, Location) for loc in locs)
    assert all(loc.slug and loc.name for loc in locs)


def test_find_locations_exact_match_returns_top():
    matches = find_locations("Marousi")
    assert matches[0].slug == "marousi"


def test_find_locations_alias_match():
    matches = find_locations("Παγκράτι")
    assert matches[0].slug == "pagrati"


def test_find_locations_typo_returns_close_matches():
    matches = find_locations("athin centre")
    slugs = [m.slug for m in matches[:3]]
    assert "athina-kentro" in slugs


def test_find_locations_empty_query_returns_empty():
    assert find_locations("") == []


def test_find_locations_no_match_returns_empty():
    matches = find_locations("xyzzy nowhere")
    assert matches == []
```

- [ ] **Step 3: Run, expect failure**

```bash
poetry run pytest tests/test_locations.py -v
```
Expected: ImportError.

- [ ] **Step 4: Implement `home_scanner/locations.py`**

```python
"""Greek-area location registry, sourced from `locations.yml`.

Provides Spitogatos URL-slug lookup with fuzzy matching for the bot's /new wizard.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml
from rapidfuzz import fuzz, process

_YAML_PATH = Path(__file__).parent / "locations.yml"
_FUZZ_CUTOFF = 70  # 0–100; below this we report no match


@dataclass(frozen=True, slots=True)
class Location:
    name: str
    slug: str
    aliases: tuple[str, ...]

    @property
    def search_terms(self) -> tuple[str, ...]:
        return (self.name.lower(), *self.aliases)


@lru_cache(maxsize=1)
def load_locations() -> list[Location]:
    raw = yaml.safe_load(_YAML_PATH.read_text(encoding="utf-8"))
    return [
        Location(
            name=entry["name"],
            slug=entry["slug"],
            aliases=tuple(a.lower() for a in entry.get("aliases", [])),
        )
        for entry in raw
    ]


def find_locations(query: str, limit: int = 5) -> list[Location]:
    """Return up to `limit` Locations whose name or aliases best match `query`.

    Returns empty list if `query` is empty or no match passes the cutoff.
    """
    query = query.strip().lower()
    if not query:
        return []

    locations = load_locations()
    # Build a flat list of (search_term → location) pairs for fuzzy matching
    term_to_loc: dict[str, Location] = {}
    for loc in locations:
        for term in loc.search_terms:
            term_to_loc[term] = loc

    matches = process.extract(
        query,
        term_to_loc.keys(),
        scorer=fuzz.WRatio,
        limit=limit * 3,  # over-fetch to dedupe
        score_cutoff=_FUZZ_CUTOFF,
    )

    seen_slugs: set[str] = set()
    out: list[Location] = []
    for term, _score, _idx in matches:
        loc = term_to_loc[term]
        if loc.slug not in seen_slugs:
            seen_slugs.add(loc.slug)
            out.append(loc)
            if len(out) == limit:
                break
    return out
```

- [ ] **Step 5: Run tests, expect pass**

```bash
poetry run pytest tests/test_locations.py -v
```
Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/home_scanner/locations.yml backend/home_scanner/locations.py backend/tests/test_locations.py
git commit -m "feat: add locations registry with fuzzy matching for Greek areas"
```

---

### Task 4: pytest infrastructure (conftest with Postgres testcontainer)

**Files:**
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Create `backend/tests/conftest.py`**

```python
"""Shared pytest fixtures.

Spins up a real Postgres container per test session for DB-backed tests.
Tests that don't need a DB simply don't request the `db_session` fixture.
"""
from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    with PostgresContainer("postgres:16-alpine", driver="psycopg") as pg:
        yield pg


@pytest.fixture(scope="session")
def db_engine(postgres_container: PostgresContainer) -> Engine:
    url = postgres_container.get_connection_url()
    return create_engine(url, future=True)


@pytest.fixture
def db_session(db_engine: Engine) -> Generator[Session, None, None]:
    """A fresh transactional session per test; rolls back at end."""
    SessionLocal = sessionmaker(bind=db_engine, expire_on_commit=False)
    connection = db_engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def freeze_now(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Freeze datetime.utcnow / now() in tests via the project's clock helper."""
    # The project uses home_scanner.clock.now() everywhere; we'll patch it here once
    # the clock module exists. For now this is a placeholder used by future tests.
    from datetime import UTC, datetime

    fixed = datetime(2026, 5, 8, 12, 0, 0, tzinfo=UTC)
    yield fixed
```

- [ ] **Step 2: Verify the container starts (skip if Docker isn't running)**

```bash
poetry run pytest tests/conftest.py --collect-only
```
Expected: collects 0 tests but no errors.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/conftest.py
git commit -m "test: add pytest conftest with Postgres testcontainer"
```

---

## Phase B — Scraper

### Task 5: Build Spitogatos search URL from filters (TDD)

**Files:**
- Create: `backend/home_scanner/scraper/__init__.py`
- Create: `backend/home_scanner/scraper/models.py`
- Create: `backend/home_scanner/scraper/search_url.py`
- Create: `backend/tests/scraper/__init__.py`
- Create: `backend/tests/scraper/test_search_url.py`

- [ ] **Step 1: Create `backend/home_scanner/scraper/models.py`**

```python
"""Domain models used by the scraper module."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SearchFilter:
    location_slug: str
    min_price: int | None = None
    max_price: int | None = None
    min_bedrooms: int | None = None
    max_bedrooms: int | None = None


@dataclass(frozen=True, slots=True)
class ScrapedListing:
    external_id: str
    url: str
    title: str | None
    price_eur: int
    bedrooms: int | None
    area_m2: int | None
    location_text: str | None
```

- [ ] **Step 2: Write the failing test**

`backend/tests/scraper/test_search_url.py`:
```python
from home_scanner.scraper.models import SearchFilter
from home_scanner.scraper.search_url import build_search_url


def test_minimal_filter_uses_location_only():
    f = SearchFilter(location_slug="marousi")
    assert build_search_url(f) == "https://www.spitogatos.gr/enoikiaseis-katoikies/marousi"


def test_with_price_range():
    f = SearchFilter(location_slug="athina-kentro", min_price=600, max_price=1200)
    url = build_search_url(f)
    assert url.startswith("https://www.spitogatos.gr/enoikiaseis-katoikies/athina-kentro?")
    assert "priceMin=600" in url
    assert "priceMax=1200" in url


def test_with_bedrooms_range():
    f = SearchFilter(location_slug="thessaloniki", min_bedrooms=2, max_bedrooms=3)
    url = build_search_url(f)
    assert "bedroomsMin=2" in url
    assert "bedroomsMax=3" in url


def test_only_min_bound():
    f = SearchFilter(location_slug="marousi", min_price=800)
    url = build_search_url(f)
    assert "priceMin=800" in url
    assert "priceMax" not in url
```

- [ ] **Step 3: Run, expect failure**

```bash
poetry run pytest tests/scraper/test_search_url.py -v
```
Expected: ImportError.

- [ ] **Step 4: Implement `home_scanner/scraper/search_url.py`**

```python
"""Build Spitogatos rental-search URLs from a SearchFilter."""
from __future__ import annotations

from urllib.parse import urlencode

from .models import SearchFilter

_BASE = "https://www.spitogatos.gr/enoikiaseis-katoikies"


def build_search_url(f: SearchFilter) -> str:
    base = f"{_BASE}/{f.location_slug}"

    params: list[tuple[str, str]] = []
    if f.min_price is not None:
        params.append(("priceMin", str(f.min_price)))
    if f.max_price is not None:
        params.append(("priceMax", str(f.max_price)))
    if f.min_bedrooms is not None:
        params.append(("bedroomsMin", str(f.min_bedrooms)))
    if f.max_bedrooms is not None:
        params.append(("bedroomsMax", str(f.max_bedrooms)))

    if not params:
        return base
    return f"{base}?{urlencode(params)}"
```

- [ ] **Step 5: Run tests, expect pass**

```bash
poetry run pytest tests/scraper/test_search_url.py -v
```
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/home_scanner/scraper backend/tests/scraper/test_search_url.py backend/tests/scraper/__init__.py
git commit -m "feat: build Spitogatos rental search URLs from SearchFilter"
```

---

### Task 6: Parser — HTML to ScrapedListing list (TDD with fixtures)

**Files:**
- Create: `backend/tests/fixtures/spitogatos/athens-centre-page1.html`
- Create: `backend/tests/fixtures/spitogatos/empty-results.html`
- Create: `backend/home_scanner/scraper/parser.py`
- Create: `backend/tests/scraper/test_parser.py`

- [ ] **Step 1: Capture a real Spitogatos HTML page as a fixture**

Run a one-off script to fetch and save a real page (uses your DataImpulse creds from `.env`):

```bash
cd backend
poetry run python - <<'PY'
import os
import httpx
from dotenv import load_dotenv

load_dotenv()
proxy = (
    f"http://{os.environ['DATAIMPULSE_USER']}:{os.environ['DATAIMPULSE_PASS']}"
    f"@{os.environ['DATAIMPULSE_HOST']}:{os.environ['DATAIMPULSE_PORT']}"
)
url = "https://www.spitogatos.gr/enoikiaseis-katoikies/athina-kentro"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.spitogatos.gr/",
}
resp = httpx.get(url, headers=headers, proxy=proxy, timeout=30.0)
resp.raise_for_status()
print(f"Got {len(resp.text)} chars")
open("tests/fixtures/spitogatos/athens-centre-page1.html", "w").write(resp.text)
PY
```

Then **manually inspect** the saved fixture to confirm it has listings (should be ~50–100KB+, contain `tile__price` strings).

- [ ] **Step 2: Hand-craft `tests/fixtures/spitogatos/empty-results.html`**

A minimal HTML page representing zero results. Save to `backend/tests/fixtures/spitogatos/empty-results.html`:

```html
<!DOCTYPE html>
<html>
<head><title>No results</title></head>
<body>
<main>
  <div class="no-results">No listings match.</div>
</main>
</body>
</html>
```

- [ ] **Step 3: Write the failing test**

`backend/tests/scraper/test_parser.py`:
```python
from pathlib import Path

import pytest
from home_scanner.scraper.parser import parse_listings

FIXTURES = Path(__file__).parent.parent / "fixtures" / "spitogatos"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parses_real_athens_page():
    html = _load("athens-centre-page1.html")
    listings = parse_listings(html)
    assert len(listings) >= 5  # At least 5 listings on a centre-of-Athens page
    sample = listings[0]
    assert sample.external_id  # Non-empty
    assert sample.url.startswith("https://www.spitogatos.gr/")
    assert sample.price_eur > 0


def test_parses_empty_results_page():
    html = _load("empty-results.html")
    assert parse_listings(html) == []


def test_parser_skips_listings_without_price():
    # Construct minimal HTML with one good and one priceless card
    html = """
    <html><body>
    <article class="ordered-element" data-listing-id="111">
      <a href="/property/111">Link</a>
      <div class="tile__price">€800</div>
      <div class="tile__bedrooms">2 bedrooms</div>
    </article>
    <article class="ordered-element" data-listing-id="222">
      <a href="/property/222">Link</a>
      <!-- no price -->
    </article>
    </body></html>
    """
    listings = parse_listings(html)
    assert len(listings) == 1
    assert listings[0].external_id == "111"
    assert listings[0].price_eur == 800
```

- [ ] **Step 4: Run, expect failure**

```bash
poetry run pytest tests/scraper/test_parser.py -v
```

- [ ] **Step 5: Implement `home_scanner/scraper/parser.py`**

The selectors below are derived from the existing `main.py` (`article.ordered-element`, `div.tile__price`). When Spitogatos changes them, this is the only file that should need to change.

```python
"""Parse Spitogatos rental search results into ScrapedListing rows.

Selectors are intentionally narrow and well-named so that when Spitogatos changes
the markup, the breakage is localised here.
"""
from __future__ import annotations

import re
from typing import Iterable

from bs4 import BeautifulSoup, Tag

from .models import ScrapedListing

_PRICE_RE = re.compile(r"(\d[\d.,]*)")
_BEDROOMS_RE = re.compile(r"(\d+)\s*bedroom", re.IGNORECASE)
_AREA_RE = re.compile(r"(\d+)\s*m²", re.IGNORECASE)


def parse_listings(html: str) -> list[ScrapedListing]:
    soup = BeautifulSoup(html, "html.parser")
    cards: Iterable[Tag] = soup.find_all("article", class_="ordered-element")
    out: list[ScrapedListing] = []
    for card in cards:
        listing = _parse_card(card)
        if listing is not None:
            out.append(listing)
    return out


def _parse_card(card: Tag) -> ScrapedListing | None:
    external_id = card.get("data-listing-id")
    if not external_id:
        return None

    price = _extract_price(card)
    if price is None:
        # No price → skip; the alert flow needs price to filter
        return None

    link = card.find("a", href=True)
    href = link["href"] if isinstance(link, Tag) else None
    if not href:
        return None
    url = href if href.startswith("http") else f"https://www.spitogatos.gr{href}"

    return ScrapedListing(
        external_id=str(external_id),
        url=url,
        title=_text_or_none(card, "h3"),
        price_eur=price,
        bedrooms=_extract_int(card, "tile__bedrooms", _BEDROOMS_RE),
        area_m2=_extract_int(card, "tile__area", _AREA_RE),
        location_text=_text_or_none(card, "tile__location"),
    )


def _extract_price(card: Tag) -> int | None:
    div = card.find("div", class_="tile__price")
    if not isinstance(div, Tag):
        return None
    match = _PRICE_RE.search(div.get_text(strip=True))
    if not match:
        return None
    return int(match.group(1).replace(".", "").replace(",", ""))


def _extract_int(card: Tag, css_class: str, pattern: re.Pattern[str]) -> int | None:
    el = card.find(class_=css_class)
    if not isinstance(el, Tag):
        return None
    match = pattern.search(el.get_text())
    return int(match.group(1)) if match else None


def _text_or_none(card: Tag, css_class_or_tag: str) -> str | None:
    if css_class_or_tag.startswith("tile__"):
        el = card.find(class_=css_class_or_tag)
    else:
        el = card.find(css_class_or_tag)
    if not isinstance(el, Tag):
        return None
    text = el.get_text(strip=True)
    return text or None
```

- [ ] **Step 6: Run tests, expect pass**

```bash
poetry run pytest tests/scraper/test_parser.py -v
```
Expected: 3 passed. **If `test_parses_real_athens_page` fails**, inspect the saved HTML fixture and adjust selectors (`tile__price`, `ordered-element`, etc.) to match what's actually in the page. The fixture file is the authoritative spec for what the parser must handle.

- [ ] **Step 7: Commit**

```bash
git add backend/home_scanner/scraper/parser.py backend/tests/scraper/test_parser.py backend/tests/fixtures/spitogatos
git commit -m "feat: parse Spitogatos rental cards into ScrapedListing"
```

---

### Task 7: HTTP client with proxy + retries (TDD with respx)

**Files:**
- Create: `backend/home_scanner/scraper/client.py`
- Create: `backend/tests/scraper/test_client.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/scraper/test_client.py`:
```python
import httpx
import pytest
import respx
from home_scanner.scraper.client import SpitogatosClient, ScrapeError


@pytest.fixture
def client() -> SpitogatosClient:
    return SpitogatosClient(proxy_url="http://u:p@proxy.example.com:823")


@respx.mock
def test_fetch_returns_html_on_200(client: SpitogatosClient):
    respx.get("https://www.spitogatos.gr/enoikiaseis-katoikies/marousi").mock(
        return_value=httpx.Response(200, text="<html>ok</html>"),
    )
    html = client.fetch("https://www.spitogatos.gr/enoikiaseis-katoikies/marousi")
    assert html == "<html>ok</html>"


@respx.mock
def test_fetch_retries_on_503_then_succeeds(client: SpitogatosClient):
    route = respx.get("https://www.spitogatos.gr/enoikiaseis-katoikies/marousi")
    route.side_effect = [
        httpx.Response(503),
        httpx.Response(503),
        httpx.Response(200, text="<html>ok</html>"),
    ]
    html = client.fetch("https://www.spitogatos.gr/enoikiaseis-katoikies/marousi")
    assert html == "<html>ok</html>"
    assert route.call_count == 3


@respx.mock
def test_fetch_raises_after_max_retries(client: SpitogatosClient):
    respx.get("https://www.spitogatos.gr/enoikiaseis-katoikies/marousi").mock(
        return_value=httpx.Response(503),
    )
    with pytest.raises(ScrapeError):
        client.fetch("https://www.spitogatos.gr/enoikiaseis-katoikies/marousi")


@respx.mock
def test_fetch_does_not_retry_on_403(client: SpitogatosClient):
    route = respx.get("https://www.spitogatos.gr/enoikiaseis-katoikies/marousi").mock(
        return_value=httpx.Response(403),
    )
    with pytest.raises(ScrapeError, match="403"):
        client.fetch("https://www.spitogatos.gr/enoikiaseis-katoikies/marousi")
    assert route.call_count == 1
```

- [ ] **Step 2: Run, expect failure**

```bash
poetry run pytest tests/scraper/test_client.py -v
```

- [ ] **Step 3: Implement `home_scanner/scraper/client.py`**

```python
"""HTTP client for Spitogatos via DataImpulse, with retry policy."""
from __future__ import annotations

import httpx
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) "
        "Gecko/20100101 Firefox/120.0"
    ),
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.spitogatos.gr/",
}


class ScrapeError(Exception):
    """Raised when fetching a Spitogatos URL fails permanently."""


class _Transient5xx(Exception):
    """Internal — used to drive tenacity retries on 5xx-but-not-403/429."""


class SpitogatosClient:
    def __init__(self, proxy_url: str | None = None, timeout: float = 30.0) -> None:
        self._proxy_url = proxy_url
        self._timeout = timeout

    def fetch(self, url: str) -> str:
        try:
            return self._fetch_with_retries(url)
        except RetryError as exc:
            raise ScrapeError(f"Exhausted retries fetching {url}") from exc

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type(_Transient5xx),
        reraise=True,
    )
    def _fetch_with_retries(self, url: str) -> str:
        with httpx.Client(
            proxy=self._proxy_url, headers=_DEFAULT_HEADERS, timeout=self._timeout
        ) as client:
            resp = client.get(url)

        if 500 <= resp.status_code < 600:
            raise _Transient5xx(f"{resp.status_code} from {url}")
        if resp.status_code in (403, 429):
            raise ScrapeError(f"{resp.status_code} from {url} — bot detection")
        if resp.status_code != 200:
            raise ScrapeError(f"{resp.status_code} from {url}")
        return resp.text
```

- [ ] **Step 4: Run tests, expect pass**

```bash
poetry run pytest tests/scraper/test_client.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/home_scanner/scraper/client.py backend/tests/scraper/test_client.py
git commit -m "feat: add Spitogatos HTTP client with proxy and 5xx retry"
```

---

### Task 8: Scraper service — orchestrate URL → fetch → parse

**Files:**
- Create: `backend/home_scanner/scraper/service.py`
- Create: `backend/tests/scraper/test_service.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/scraper/test_service.py`:
```python
from unittest.mock import Mock

from home_scanner.scraper.models import SearchFilter
from home_scanner.scraper.service import scrape_search


def test_scrape_search_calls_client_with_built_url_and_returns_parsed():
    fake_html = """
    <html><body>
    <article class="ordered-element" data-listing-id="999">
      <a href="/property/999">Link</a>
      <div class="tile__price">€700</div>
    </article>
    </body></html>
    """
    client = Mock()
    client.fetch.return_value = fake_html

    f = SearchFilter(location_slug="marousi", max_price=1000)
    listings = scrape_search(f, client=client)

    args, _ = client.fetch.call_args
    assert "marousi" in args[0]
    assert "priceMax=1000" in args[0]

    assert len(listings) == 1
    assert listings[0].external_id == "999"
    assert listings[0].price_eur == 700
```

- [ ] **Step 2: Run, expect failure**

```bash
poetry run pytest tests/scraper/test_service.py -v
```

- [ ] **Step 3: Implement `home_scanner/scraper/service.py`**

```python
"""Top-level scraper entrypoint: SearchFilter → list[ScrapedListing]."""
from __future__ import annotations

from .client import SpitogatosClient
from .models import ScrapedListing, SearchFilter
from .parser import parse_listings
from .search_url import build_search_url


def scrape_search(
    f: SearchFilter,
    client: SpitogatosClient,
) -> list[ScrapedListing]:
    url = build_search_url(f)
    html = client.fetch(url)
    return parse_listings(html)
```

- [ ] **Step 4: Update `home_scanner/scraper/__init__.py`** to expose the public API:

```python
"""Spitogatos scraper module."""
from .client import ScrapeError, SpitogatosClient
from .models import ScrapedListing, SearchFilter
from .service import scrape_search

__all__ = [
    "ScrapeError",
    "ScrapedListing",
    "SearchFilter",
    "SpitogatosClient",
    "scrape_search",
]
```

- [ ] **Step 5: Run tests, expect pass**

```bash
poetry run pytest tests/scraper/ -v
```
Expected: all scraper tests passing.

- [ ] **Step 6: Commit**

```bash
git add backend/home_scanner/scraper/service.py backend/home_scanner/scraper/__init__.py backend/tests/scraper/test_service.py
git commit -m "feat: add scrape_search orchestrator combining URL → fetch → parse"
```

---

## Phase C — DB layer

### Task 9: SQLAlchemy ORM models for all 5 tables

**Files:**
- Create: `backend/home_scanner/db/__init__.py`
- Create: `backend/home_scanner/db/models.py`
- Create: `backend/home_scanner/db/session.py`
- Create: `backend/tests/db/__init__.py`
- Create: `backend/tests/db/test_models.py`

- [ ] **Step 1: Implement `home_scanner/db/models.py`**

```python
"""SQLAlchemy 2 ORM models matching the spec data model."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_chat_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False
    )
    telegram_username: Mapped[str | None] = mapped_column(Text)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    saved_searches: Mapped[list["SavedSearch"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class SavedSearch(Base):
    __tablename__ = "saved_searches"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str | None] = mapped_column(Text)
    location_slug: Mapped[str] = mapped_column(Text, nullable=False)
    min_price: Mapped[int | None] = mapped_column(Integer)
    max_price: Mapped[int | None] = mapped_column(Integer)
    min_bedrooms: Mapped[int | None] = mapped_column(SmallInteger)
    max_bedrooms: Mapped[int | None] = mapped_column(SmallInteger)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="saved_searches")


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    external_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    price_eur: Mapped[int] = mapped_column(Integer, nullable=False)
    bedrooms: Mapped[int | None] = mapped_column(SmallInteger)
    area_m2: Mapped[int | None] = mapped_column(SmallInteger)
    location_text: Mapped[str | None] = mapped_column(Text)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AlertSent(Base):
    __tablename__ = "alerts_sent"
    __table_args__ = (
        PrimaryKeyConstraint("saved_search_id", "listing_id"),
    )

    saved_search_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("saved_searches.id", ondelete="CASCADE"),
        nullable=False,
    )
    listing_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
    )
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger)


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text, nullable=False)  # running|ok|failed
    searches_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    listings_seen: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_alerts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errors: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
```

- [ ] **Step 2: Implement `home_scanner/db/session.py`**

```python
"""SQLAlchemy engine + session factory."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from home_scanner.settings import Settings


def make_engine(database_url: str | None = None) -> Engine:
    url = database_url or Settings().database_url
    return create_engine(url, future=True, pool_pre_ping=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
```

- [ ] **Step 3: Implement `home_scanner/db/__init__.py`**

```python
"""Database layer: ORM models, session factory, repositories."""
from .models import AlertSent, Base, Listing, SavedSearch, ScrapeRun, User
from .session import make_engine, make_session_factory

__all__ = [
    "AlertSent",
    "Base",
    "Listing",
    "SavedSearch",
    "ScrapeRun",
    "User",
    "make_engine",
    "make_session_factory",
]
```

- [ ] **Step 4: Add a fixture in `tests/conftest.py` that creates the schema once**

Append to `backend/tests/conftest.py`:

```python
@pytest.fixture(scope="session", autouse=True)
def _create_schema(db_engine: Engine) -> None:
    from home_scanner.db.models import Base
    Base.metadata.create_all(db_engine)
```

- [ ] **Step 5: Write `backend/tests/db/test_models.py`**

```python
from datetime import UTC, datetime

from home_scanner.db.models import Listing, SavedSearch, User
from sqlalchemy.orm import Session


def test_user_create(db_session: Session):
    u = User(telegram_chat_id=12345, telegram_username="someone")
    db_session.add(u)
    db_session.flush()
    assert u.id is not None
    assert u.created_at is not None


def test_saved_search_unique_per_user(db_session: Session):
    u = User(telegram_chat_id=99, telegram_username=None)
    db_session.add(u)
    db_session.flush()
    s = SavedSearch(
        user_id=u.id,
        location_slug="marousi",
        min_price=600,
        max_price=1200,
        min_bedrooms=2,
        max_bedrooms=2,
    )
    db_session.add(s)
    db_session.flush()
    assert s.is_active is True


def test_listing_external_id_unique(db_session: Session):
    now = datetime.now(UTC)
    l1 = Listing(
        external_id="abc-123",
        url="https://x",
        price_eur=800,
        first_seen_at=now,
        last_seen_at=now,
        is_active=True,
    )
    db_session.add(l1)
    db_session.flush()

    l2 = Listing(
        external_id="abc-123",
        url="https://x2",
        price_eur=900,
        first_seen_at=now,
        last_seen_at=now,
        is_active=True,
    )
    db_session.add(l2)
    import pytest
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        db_session.flush()
```

- [ ] **Step 6: Run tests, expect pass**

```bash
poetry run pytest tests/db/test_models.py -v
```
Expected: 3 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/home_scanner/db backend/tests/db backend/tests/conftest.py
git commit -m "feat: add SQLAlchemy models for users, searches, listings, alerts, scrape_runs"
```

---

### Task 10: Alembic migration for the full schema

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/0001_initial_schema.py`

- [ ] **Step 1: Initialise Alembic in `backend/`**

```bash
cd backend
poetry run alembic init alembic
```

This creates `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`, `alembic/versions/`.

- [ ] **Step 2: Edit `backend/alembic/env.py` to use our `Base` and env-var-driven URL**

Replace the body with:

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from home_scanner.db.models import Base
from home_scanner.settings import Settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", Settings().database_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 3: Generate the initial migration**

Make sure your `backend/.env` has a real `DATABASE_URL` pointing at a local Postgres (start one with `docker run -p 5432:5432 -e POSTGRES_PASSWORD=home_scanner -e POSTGRES_USER=home_scanner -e POSTGRES_DB=home_scanner -d postgres:16-alpine`).

```bash
cd backend
poetry run alembic revision --autogenerate -m "initial schema"
```

Inspect the generated file in `backend/alembic/versions/` — confirm it creates all 5 tables.

- [ ] **Step 4: Rename the generated file to `0001_initial_schema.py`** for stable ordering, then apply it

```bash
mv backend/alembic/versions/*_initial_schema.py backend/alembic/versions/0001_initial_schema.py
poetry run alembic upgrade head
```

- [ ] **Step 5: Verify schema applied**

```bash
poetry run python - <<'PY'
from sqlalchemy import create_engine, inspect
from home_scanner.settings import Settings
engine = create_engine(Settings().database_url)
print(sorted(inspect(engine).get_table_names()))
PY
```
Expected: `['alembic_version', 'alerts_sent', 'listings', 'saved_searches', 'scrape_runs', 'users']`.

- [ ] **Step 6: Commit**

```bash
git add backend/alembic.ini backend/alembic
git commit -m "feat: add Alembic with initial schema migration"
```

---

### Task 11: Repository helpers (CRUD) for the bot and notifier

**Files:**
- Create: `backend/home_scanner/db/repositories.py`
- Create: `backend/tests/db/test_repositories.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/db/test_repositories.py`:
```python
from datetime import UTC, datetime

from home_scanner.db.models import Listing, User
from home_scanner.db.repositories import (
    create_saved_search,
    delete_saved_search,
    get_or_create_user,
    list_active_saved_searches,
    list_user_saved_searches,
    set_saved_search_active,
    upsert_listing,
)
from sqlalchemy.orm import Session


def test_get_or_create_user_idempotent(db_session: Session):
    u1 = get_or_create_user(db_session, telegram_chat_id=42, telegram_username="x")
    u2 = get_or_create_user(db_session, telegram_chat_id=42, telegram_username="y")
    assert u1.id == u2.id


def test_create_and_list_saved_searches(db_session: Session):
    u = get_or_create_user(db_session, telegram_chat_id=1, telegram_username=None)
    s = create_saved_search(
        db_session,
        user_id=u.id,
        location_slug="marousi",
        min_price=500,
        max_price=900,
        min_bedrooms=1,
        max_bedrooms=2,
    )
    db_session.flush()
    assert s.id is not None

    rows = list_user_saved_searches(db_session, user_id=u.id)
    assert len(rows) == 1
    assert rows[0].location_slug == "marousi"


def test_set_active_and_delete(db_session: Session):
    u = get_or_create_user(db_session, telegram_chat_id=2, telegram_username=None)
    s = create_saved_search(db_session, user_id=u.id, location_slug="marousi")
    db_session.flush()

    set_saved_search_active(db_session, search_id=s.id, is_active=False)
    db_session.flush()
    refreshed = db_session.get(type(s), s.id)
    assert refreshed.is_active is False

    delete_saved_search(db_session, search_id=s.id)
    db_session.flush()
    assert db_session.get(type(s), s.id) is None


def test_list_active_saved_searches_skips_inactive(db_session: Session):
    u = get_or_create_user(db_session, telegram_chat_id=3, telegram_username=None)
    s_a = create_saved_search(db_session, user_id=u.id, location_slug="a")
    s_b = create_saved_search(db_session, user_id=u.id, location_slug="b")
    db_session.flush()
    set_saved_search_active(db_session, search_id=s_b.id, is_active=False)
    db_session.flush()
    rows = list_active_saved_searches(db_session)
    slugs = [r.location_slug for r in rows]
    assert "a" in slugs and "b" not in slugs


def test_upsert_listing_inserts_then_updates(db_session: Session):
    now = datetime.now(UTC)
    listing_data = dict(
        external_id="ext-1",
        url="https://x",
        title="t",
        price_eur=800,
        bedrooms=2,
        area_m2=60,
        location_text="loc",
    )
    upsert_listing(db_session, now=now, **listing_data)
    db_session.flush()

    later = datetime.now(UTC)
    listing_data["price_eur"] = 750  # price drop
    upsert_listing(db_session, now=later, **listing_data)
    db_session.flush()

    rows = db_session.query(Listing).filter_by(external_id="ext-1").all()
    assert len(rows) == 1
    assert rows[0].price_eur == 750
    assert rows[0].last_seen_at == later
    assert rows[0].first_seen_at == now
```

- [ ] **Step 2: Run, expect failure**

```bash
poetry run pytest tests/db/test_repositories.py -v
```

- [ ] **Step 3: Implement `home_scanner/db/repositories.py`**

```python
"""CRUD helpers used by the bot and notifier modules.

Functions take an explicit `Session` and never commit — the caller is responsible
for transaction lifecycle. This keeps tests transactional and the runtime free
to batch.
"""
from __future__ import annotations

from datetime import datetime
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from .models import AlertSent, Listing, SavedSearch, User


# --- users ---

def get_or_create_user(
    session: Session, *, telegram_chat_id: int, telegram_username: str | None
) -> User:
    existing = session.scalar(
        select(User).where(User.telegram_chat_id == telegram_chat_id)
    )
    if existing is not None:
        if telegram_username and existing.telegram_username != telegram_username:
            existing.telegram_username = telegram_username
        return existing
    new = User(
        telegram_chat_id=telegram_chat_id,
        telegram_username=telegram_username,
    )
    session.add(new)
    session.flush()
    return new


def deactivate_user(session: Session, *, user_id: int, at: datetime) -> None:
    user = session.get(User, user_id)
    if user is not None:
        user.deactivated_at = at


# --- saved searches ---

def create_saved_search(
    session: Session,
    *,
    user_id: int,
    location_slug: str,
    name: str | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    min_bedrooms: int | None = None,
    max_bedrooms: int | None = None,
) -> SavedSearch:
    s = SavedSearch(
        user_id=user_id,
        location_slug=location_slug,
        name=name,
        min_price=min_price,
        max_price=max_price,
        min_bedrooms=min_bedrooms,
        max_bedrooms=max_bedrooms,
    )
    session.add(s)
    session.flush()
    return s


def list_user_saved_searches(
    session: Session, *, user_id: int
) -> Sequence[SavedSearch]:
    return session.scalars(
        select(SavedSearch).where(SavedSearch.user_id == user_id).order_by(SavedSearch.id)
    ).all()


def list_active_saved_searches(session: Session) -> Sequence[SavedSearch]:
    return session.scalars(
        select(SavedSearch)
        .join(User, User.id == SavedSearch.user_id)
        .where(SavedSearch.is_active.is_(True))
        .where(User.deactivated_at.is_(None))
    ).all()


def set_saved_search_active(
    session: Session, *, search_id: int, is_active: bool
) -> None:
    s = session.get(SavedSearch, search_id)
    if s is not None:
        s.is_active = is_active


def delete_saved_search(session: Session, *, search_id: int) -> None:
    s = session.get(SavedSearch, search_id)
    if s is not None:
        session.delete(s)


# --- listings ---

def upsert_listing(
    session: Session,
    *,
    now: datetime,
    external_id: str,
    url: str,
    title: str | None,
    price_eur: int,
    bedrooms: int | None,
    area_m2: int | None,
    location_text: str | None,
) -> Listing:
    """Insert or update by external_id. Sets first_seen_at on insert, last_seen_at always."""
    stmt = insert(Listing).values(
        external_id=external_id,
        url=url,
        title=title,
        price_eur=price_eur,
        bedrooms=bedrooms,
        area_m2=area_m2,
        location_text=location_text,
        first_seen_at=now,
        last_seen_at=now,
        is_active=True,
    ).on_conflict_do_update(
        index_elements=[Listing.external_id],
        set_={
            "url": url,
            "title": title,
            "price_eur": price_eur,
            "bedrooms": bedrooms,
            "area_m2": area_m2,
            "location_text": location_text,
            "last_seen_at": now,
            "is_active": True,
        },
    )
    session.execute(stmt)
    return session.scalar(select(Listing).where(Listing.external_id == external_id))


def listings_matching_search(
    session: Session, *, search: SavedSearch
) -> Sequence[Listing]:
    """Active listings whose price/bedrooms fall within the saved search's bounds."""
    q = select(Listing).where(Listing.is_active.is_(True))
    if search.min_price is not None:
        q = q.where(Listing.price_eur >= search.min_price)
    if search.max_price is not None:
        q = q.where(Listing.price_eur <= search.max_price)
    if search.min_bedrooms is not None:
        q = q.where(
            (Listing.bedrooms.is_(None)) | (Listing.bedrooms >= search.min_bedrooms)
        )
    if search.max_bedrooms is not None:
        q = q.where(
            (Listing.bedrooms.is_(None)) | (Listing.bedrooms <= search.max_bedrooms)
        )
    return session.scalars(q.order_by(Listing.first_seen_at.desc())).all()


# --- alerts_sent ---

def listing_ids_already_alerted(
    session: Session, *, search_id: int
) -> set[int]:
    return set(
        session.scalars(
            select(AlertSent.listing_id).where(AlertSent.saved_search_id == search_id)
        ).all()
    )


def record_alert(
    session: Session,
    *,
    saved_search_id: int,
    listing_id: int,
    sent_at: datetime,
    telegram_message_id: int | None = None,
) -> None:
    a = AlertSent(
        saved_search_id=saved_search_id,
        listing_id=listing_id,
        sent_at=sent_at,
        telegram_message_id=telegram_message_id,
    )
    session.add(a)
```

- [ ] **Step 4: Run tests, expect pass**

```bash
poetry run pytest tests/db/test_repositories.py -v
```
Expected: 5 passed. **If `upsert_listing` test fails on `first_seen_at == now`** — the upsert's `on_conflict_do_update` should NOT overwrite `first_seen_at`. The test asserts that.

- [ ] **Step 5: Commit**

```bash
git add backend/home_scanner/db/repositories.py backend/tests/db/test_repositories.py
git commit -m "feat: add repository helpers for users, searches, listings, alerts"
```

---

## Phase D — Notifier

### Task 12: Pure diff function (TDD — the load-bearing logic)

**Files:**
- Create: `backend/home_scanner/notifier/__init__.py`
- Create: `backend/home_scanner/notifier/diff.py`
- Create: `backend/tests/notifier/__init__.py`
- Create: `backend/tests/notifier/test_diff.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/notifier/test_diff.py`:
```python
from datetime import UTC, datetime
from types import SimpleNamespace

from home_scanner.notifier.diff import compute_alerts_to_send


def _listing(lid: int, price: int, bedrooms: int) -> SimpleNamespace:
    return SimpleNamespace(
        id=lid, price_eur=price, bedrooms=bedrooms, is_active=True
    )


def _search(sid: int, **bounds) -> SimpleNamespace:
    return SimpleNamespace(id=sid, location_slug="x", is_active=True, **{
        "min_price": bounds.get("min_price"),
        "max_price": bounds.get("max_price"),
        "min_bedrooms": bounds.get("min_bedrooms"),
        "max_bedrooms": bounds.get("max_bedrooms"),
    })


def test_listing_within_bounds_is_alerted():
    s = _search(1, min_price=500, max_price=1000, min_bedrooms=1, max_bedrooms=3)
    listings = [_listing(101, price=800, bedrooms=2)]
    already_alerted = set()
    out = compute_alerts_to_send(s, listings, already_alerted_listing_ids=already_alerted)
    assert out == [(1, 101)]


def test_listing_already_alerted_is_skipped():
    s = _search(1, max_price=1000)
    listings = [_listing(101, price=800, bedrooms=2)]
    out = compute_alerts_to_send(s, listings, already_alerted_listing_ids={101})
    assert out == []


def test_listing_above_max_price_is_skipped():
    s = _search(1, max_price=700)
    listings = [_listing(101, price=800, bedrooms=2)]
    out = compute_alerts_to_send(s, listings, already_alerted_listing_ids=set())
    assert out == []


def test_listing_below_min_bedrooms_is_skipped():
    s = _search(1, min_bedrooms=2)
    listings = [_listing(101, price=800, bedrooms=1)]
    out = compute_alerts_to_send(s, listings, already_alerted_listing_ids=set())
    assert out == []


def test_listing_with_null_bedrooms_passes_bounds():
    """Null bedrooms shouldn't exclude — Spitogatos sometimes omits the field."""
    s = _search(1, min_bedrooms=2, max_bedrooms=2)
    listings = [_listing(101, price=800, bedrooms=None)]
    out = compute_alerts_to_send(s, listings, already_alerted_listing_ids=set())
    assert out == [(1, 101)]


def test_inactive_listing_is_skipped():
    s = _search(1)
    listing = _listing(101, price=800, bedrooms=2)
    listing.is_active = False
    out = compute_alerts_to_send(s, [listing], already_alerted_listing_ids=set())
    assert out == []
```

- [ ] **Step 2: Run, expect failure**

```bash
poetry run pytest tests/notifier/test_diff.py -v
```

- [ ] **Step 3: Implement `home_scanner/notifier/diff.py`**

```python
"""Pure logic: given a saved search, candidate listings, and the set of already-alerted
listing IDs, return the list of (saved_search_id, listing_id) tuples to alert.

This module knows nothing about the DB or Telegram — it's deterministic and unit-testable.
"""
from __future__ import annotations

from typing import Iterable, Protocol


class _SavedSearchLike(Protocol):
    id: int
    is_active: bool
    min_price: int | None
    max_price: int | None
    min_bedrooms: int | None
    max_bedrooms: int | None


class _ListingLike(Protocol):
    id: int
    price_eur: int
    bedrooms: int | None
    is_active: bool


def compute_alerts_to_send(
    search: _SavedSearchLike,
    candidates: Iterable[_ListingLike],
    *,
    already_alerted_listing_ids: set[int],
) -> list[tuple[int, int]]:
    if not search.is_active:
        return []
    out: list[tuple[int, int]] = []
    for listing in candidates:
        if not listing.is_active:
            continue
        if listing.id in already_alerted_listing_ids:
            continue
        if not _matches(search, listing):
            continue
        out.append((search.id, listing.id))
    return out


def _matches(search: _SavedSearchLike, listing: _ListingLike) -> bool:
    if search.min_price is not None and listing.price_eur < search.min_price:
        return False
    if search.max_price is not None and listing.price_eur > search.max_price:
        return False
    # null bedrooms always passes — we don't have data, don't exclude
    if listing.bedrooms is not None:
        if search.min_bedrooms is not None and listing.bedrooms < search.min_bedrooms:
            return False
        if search.max_bedrooms is not None and listing.bedrooms > search.max_bedrooms:
            return False
    return True
```

- [ ] **Step 4: Run tests, expect pass**

```bash
poetry run pytest tests/notifier/test_diff.py -v
```
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/home_scanner/notifier/__init__.py backend/home_scanner/notifier/diff.py backend/tests/notifier
git commit -m "feat: add pure diff function deciding which listings warrant alerts"
```

---

### Task 13: Dispatch — send Telegram messages and record alerts

**Files:**
- Create: `backend/home_scanner/notifier/dispatch.py`
- Create: `backend/home_scanner/bot/__init__.py` (empty for now — created here so the import path is stable)
- Create: `backend/home_scanner/bot/messages.py`
- Create: `backend/tests/notifier/test_dispatch.py`

- [ ] **Step 1: Implement `home_scanner/bot/messages.py`** (formatters used by both bot and dispatch)

```python
"""Outgoing-message formatting (Telegram MarkdownV2-safe)."""
from __future__ import annotations


def escape_md(text: str) -> str:
    """Escape MarkdownV2 metacharacters. Telegram's escape rules are strict."""
    chars = r"_*[]()~`>#+-=|{}.!"
    return "".join("\\" + c if c in chars else c for c in text)


def format_listing_alert(
    *,
    price_eur: int,
    bedrooms: int | None,
    area_m2: int | None,
    location_text: str | None,
    url: str,
) -> str:
    bedrooms_str = f"{bedrooms} BR" if bedrooms is not None else "—"
    area_str = f" · {area_m2} m²" if area_m2 is not None else ""
    location = location_text or ""
    return (
        f"🏠 *€{price_eur:,}* · {escape_md(bedrooms_str)}{escape_md(area_str)}\n"
        f"{escape_md(location)}\n"
        f"[View on spitogatos →]({escape_md(url)})"
    )
```

- [ ] **Step 2: Write the failing test**

`backend/tests/notifier/test_dispatch.py`:
```python
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from home_scanner.db.models import Listing, SavedSearch, User
from home_scanner.db.repositories import (
    create_saved_search,
    get_or_create_user,
    listing_ids_already_alerted,
    upsert_listing,
)
from home_scanner.notifier.dispatch import dispatch_alerts
from sqlalchemy.orm import Session


@pytest.mark.asyncio
async def test_dispatch_sends_messages_and_records_alerts(db_session: Session):
    user = get_or_create_user(db_session, telegram_chat_id=42, telegram_username=None)
    search = create_saved_search(db_session, user_id=user.id, location_slug="x")
    db_session.flush()

    listing = upsert_listing(
        db_session,
        now=datetime.now(UTC),
        external_id="ext-1",
        url="https://x/1",
        title="t",
        price_eur=900,
        bedrooms=2,
        area_m2=70,
        location_text="Athens",
    )
    db_session.flush()

    bot = AsyncMock()
    bot.send_message.return_value.message_id = 12345

    sent = await dispatch_alerts(
        db_session,
        bot=bot,
        alerts=[(search.id, listing.id)],
        chat_id_for_search={search.id: user.telegram_chat_id},
        now=datetime.now(UTC),
    )

    assert sent == 1
    bot.send_message.assert_awaited_once()
    assert listing_ids_already_alerted(db_session, search_id=search.id) == {listing.id}


@pytest.mark.asyncio
async def test_dispatch_skips_user_blocked_bot(db_session: Session):
    from telegram.error import Forbidden

    user = get_or_create_user(db_session, telegram_chat_id=43, telegram_username=None)
    search = create_saved_search(db_session, user_id=user.id, location_slug="x")
    db_session.flush()
    listing = upsert_listing(
        db_session, now=datetime.now(UTC),
        external_id="ext-2", url="https://x/2", title=None,
        price_eur=900, bedrooms=2, area_m2=None, location_text=None,
    )
    db_session.flush()

    bot = AsyncMock()
    bot.send_message.side_effect = Forbidden("bot was blocked by the user")

    sent = await dispatch_alerts(
        db_session, bot=bot,
        alerts=[(search.id, listing.id)],
        chat_id_for_search={search.id: user.telegram_chat_id},
        now=datetime.now(UTC),
    )
    assert sent == 0
    db_session.refresh(user)
    assert user.deactivated_at is not None
```

- [ ] **Step 3: Run, expect failure**

```bash
poetry run pytest tests/notifier/test_dispatch.py -v
```

- [ ] **Step 4: Implement `home_scanner/notifier/dispatch.py`**

```python
"""Send Telegram alert messages, record `alerts_sent` rows. Side-effecting."""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Mapping

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session
from telegram import Bot
from telegram.error import Forbidden, TelegramError
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from home_scanner.bot.messages import format_listing_alert
from home_scanner.db.models import Listing, SavedSearch, User
from home_scanner.db.repositories import deactivate_user, record_alert

log = structlog.get_logger(__name__)


async def dispatch_alerts(
    session: Session,
    *,
    bot: Bot,
    alerts: list[tuple[int, int]],
    chat_id_for_search: Mapping[int, int],
    now: datetime,
) -> int:
    """Send a Telegram message per (search_id, listing_id) tuple. Returns count sent."""
    sent = 0
    for search_id, listing_id in alerts:
        chat_id = chat_id_for_search.get(search_id)
        if chat_id is None:
            log.warning("dispatch.chat_id_missing", search_id=search_id)
            continue
        listing = session.get(Listing, listing_id)
        if listing is None:
            continue
        try:
            message = await _send_with_retry(bot, chat_id, listing)
        except Forbidden:
            log.info("dispatch.user_blocked_bot", chat_id=chat_id)
            search = session.get(SavedSearch, search_id)
            if search is not None:
                deactivate_user(session, user_id=search.user_id, at=now)
            continue
        except (TelegramError, RetryError) as exc:
            log.error("dispatch.telegram_error", error=str(exc), chat_id=chat_id)
            continue

        record_alert(
            session,
            saved_search_id=search_id,
            listing_id=listing_id,
            sent_at=now,
            telegram_message_id=message.message_id if message else None,
        )
        sent += 1
    return sent


async def _send_with_retry(bot: Bot, chat_id: int, listing: Listing):
    text = format_listing_alert(
        price_eur=listing.price_eur,
        bedrooms=listing.bedrooms,
        area_m2=listing.area_m2,
        location_text=listing.location_text,
        url=listing.url,
    )
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type(TelegramError) & ~retry_if_exception_type(Forbidden),
        reraise=True,
    ):
        with attempt:
            return await bot.send_message(
                chat_id=chat_id, text=text, parse_mode="MarkdownV2"
            )
```

- [ ] **Step 5: Update `home_scanner/notifier/__init__.py`**

```python
"""Notifier: scrape → diff → dispatch."""
from .diff import compute_alerts_to_send
from .dispatch import dispatch_alerts

__all__ = ["compute_alerts_to_send", "dispatch_alerts"]
```

- [ ] **Step 6: Run tests, expect pass**

```bash
poetry run pytest tests/notifier/test_dispatch.py -v
```
Expected: 2 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/home_scanner/notifier/dispatch.py backend/home_scanner/notifier/__init__.py backend/home_scanner/bot/__init__.py backend/home_scanner/bot/messages.py backend/tests/notifier/test_dispatch.py
git commit -m "feat: dispatch Telegram alerts with retry and bot-blocked handling"
```

---

### Task 14: Notifier runner — top-level orchestrator

**Files:**
- Create: `backend/home_scanner/notifier/runner.py`
- Create: `backend/tests/notifier/test_runner.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/notifier/test_runner.py`:
```python
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from home_scanner.db.models import ScrapeRun
from home_scanner.db.repositories import (
    create_saved_search,
    get_or_create_user,
)
from home_scanner.notifier.runner import run_one_scrape_cycle
from home_scanner.scraper.models import ScrapedListing
from sqlalchemy.orm import Session


@pytest.mark.asyncio
async def test_run_one_cycle_records_run_and_alerts(db_session: Session):
    user = get_or_create_user(db_session, telegram_chat_id=11, telegram_username=None)
    create_saved_search(db_session, user_id=user.id, location_slug="marousi")
    db_session.flush()

    scraper = Mock()
    scraper.return_value = [
        ScrapedListing(
            external_id="ext-1", url="https://x/1", title="t",
            price_eur=900, bedrooms=2, area_m2=60, location_text="Marousi",
        )
    ]
    bot = AsyncMock()
    bot.send_message.return_value.message_id = 1

    summary = await run_one_scrape_cycle(
        session=db_session,
        bot=bot,
        scrape_search_fn=scraper,
        now=datetime.now(UTC),
    )

    assert summary.searches_processed == 1
    assert summary.listings_seen == 1
    assert summary.new_alerts == 1
    assert bot.send_message.await_count == 1

    # ScrapeRun row written
    runs = db_session.query(ScrapeRun).all()
    assert len(runs) == 1
    assert runs[0].status == "ok"


@pytest.mark.asyncio
async def test_run_one_cycle_isolates_per_search_failures(db_session: Session):
    user = get_or_create_user(db_session, telegram_chat_id=12, telegram_username=None)
    create_saved_search(db_session, user_id=user.id, location_slug="marousi")
    create_saved_search(db_session, user_id=user.id, location_slug="kallithea")
    db_session.flush()

    from home_scanner.scraper import ScrapeError
    def scraper(f, client=None):
        if f.location_slug == "marousi":
            raise ScrapeError("503")
        return [
            ScrapedListing(
                external_id="ok", url="https://x/ok", title=None,
                price_eur=800, bedrooms=2, area_m2=None, location_text=None,
            )
        ]
    bot = AsyncMock()
    bot.send_message.return_value.message_id = 1

    summary = await run_one_scrape_cycle(
        session=db_session,
        bot=bot,
        scrape_search_fn=scraper,
        now=datetime.now(UTC),
    )
    assert summary.searches_processed == 2
    assert "marousi" in summary.errors["failed"]

    runs = db_session.query(ScrapeRun).all()
    assert runs[0].status == "ok"  # partial failure → still 'ok' (not catastrophic)
    assert runs[0].errors == {"failed": {"marousi": "503"}}
```

- [ ] **Step 2: Run, expect failure**

```bash
poetry run pytest tests/notifier/test_runner.py -v
```

- [ ] **Step 3: Implement `home_scanner/notifier/runner.py`**

```python
"""Top-level scrape cycle: per-search scrape → upsert listings → diff → dispatch.

This is the function called by the CLI in Plan 1, and by `/internal/scrape` in Plan 2.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Iterable

import structlog
from sqlalchemy.orm import Session
from telegram import Bot

from home_scanner.db.models import ScrapeRun
from home_scanner.db.repositories import (
    list_active_saved_searches,
    listing_ids_already_alerted,
    listings_matching_search,
    upsert_listing,
)
from home_scanner.scraper import (
    ScrapeError,
    ScrapedListing,
    SearchFilter,
    SpitogatosClient,
)

from .diff import compute_alerts_to_send
from .dispatch import dispatch_alerts

log = structlog.get_logger(__name__)


@dataclass
class RunSummary:
    searches_processed: int = 0
    listings_seen: int = 0
    new_alerts: int = 0
    errors: dict[str, Any] = field(default_factory=lambda: {"failed": {}})


ScrapeFn = Callable[..., Iterable[ScrapedListing]]


async def run_one_scrape_cycle(
    *,
    session: Session,
    bot: Bot,
    scrape_search_fn: ScrapeFn,
    client: SpitogatosClient | None = None,
    now: datetime,
) -> RunSummary:
    summary = RunSummary()
    run = ScrapeRun(started_at=now, status="running")
    session.add(run)
    session.flush()

    searches = list_active_saved_searches(session)
    chat_id_for_search = {s.id: s.user.telegram_chat_id for s in searches}

    all_alerts: list[tuple[int, int]] = []

    for search in searches:
        summary.searches_processed += 1
        f = SearchFilter(
            location_slug=search.location_slug,
            min_price=search.min_price,
            max_price=search.max_price,
            min_bedrooms=search.min_bedrooms,
            max_bedrooms=search.max_bedrooms,
        )
        try:
            scraped = list(scrape_search_fn(f, client=client))
        except ScrapeError as exc:
            log.warning("runner.search_failed", slug=search.location_slug, error=str(exc))
            summary.errors["failed"][search.location_slug] = str(exc)
            continue

        summary.listings_seen += len(scraped)

        # Upsert listings, then re-query DB-side matches (handles previously-seen ones too)
        for s in scraped:
            upsert_listing(
                session, now=now,
                external_id=s.external_id, url=s.url, title=s.title,
                price_eur=s.price_eur, bedrooms=s.bedrooms,
                area_m2=s.area_m2, location_text=s.location_text,
            )
        session.flush()

        candidates = listings_matching_search(session, search=search)
        already = listing_ids_already_alerted(session, search_id=search.id)
        alerts = compute_alerts_to_send(
            search, candidates, already_alerted_listing_ids=already
        )
        all_alerts.extend(alerts)

    summary.new_alerts = await dispatch_alerts(
        session, bot=bot, alerts=all_alerts,
        chat_id_for_search=chat_id_for_search, now=now,
    )

    run.finished_at = now
    run.searches_processed = summary.searches_processed
    run.listings_seen = summary.listings_seen
    run.new_alerts = summary.new_alerts
    run.errors = summary.errors
    run.status = "ok"
    session.flush()

    log.info(
        "runner.done",
        searches=summary.searches_processed,
        listings=summary.listings_seen,
        alerts=summary.new_alerts,
        failed=list(summary.errors["failed"].keys()),
    )
    return summary
```

- [ ] **Step 4: Run tests, expect pass**

```bash
poetry run pytest tests/notifier/ -v
```
Expected: all notifier tests passing.

- [ ] **Step 5: Commit**

```bash
git add backend/home_scanner/notifier/runner.py backend/tests/notifier/test_runner.py
git commit -m "feat: add notifier runner orchestrating scrape → diff → dispatch"
```

---

## Phase E — Bot

### Task 15: Bot Application factory + /start + /help (TDD-light)

**Files:**
- Create: `backend/home_scanner/bot/app.py`
- Create: `backend/home_scanner/bot/handlers/__init__.py`
- Create: `backend/home_scanner/bot/handlers/start_help.py`

- [ ] **Step 1: Implement `home_scanner/bot/handlers/start_help.py`**

```python
"""/start and /help — trivial reply handlers."""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

WELCOME = (
    "Hey 👋 I watch *spitogatos\\.gr* for new rentals matching your filters and ping you "
    "when something matches\\.\n\n"
    "Use /new to create a saved search\\. /help for everything else\\."
)

HELP = (
    "*Commands*\n"
    "/new — create a saved search \\(location, price, bedrooms\\)\n"
    "/list — list your saved searches\n"
    "/pause `<id>` — pause a saved search\n"
    "/resume `<id>` — resume a paused search\n"
    "/delete `<id>` — delete a saved search\n"
    "/help — this message"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_markdown_v2(WELCOME)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_markdown_v2(HELP)
```

- [ ] **Step 2: Implement `home_scanner/bot/app.py`** (the Application factory; long-polling for local dev)

```python
"""telegram.ext.Application factory. Long-polling in Plan 1; webhook adapter in Plan 2."""
from __future__ import annotations

from sqlalchemy.orm import sessionmaker
from telegram.ext import Application, CommandHandler

from home_scanner.bot.handlers.start_help import help_cmd, start
from home_scanner.settings import Settings


def build_application(*, session_factory: sessionmaker) -> Application:
    settings = Settings()
    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .build()
    )
    # Stash the session factory in app.bot_data for handlers to grab
    app.bot_data["session_factory"] = session_factory

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    # /new, /list, /pause, /resume, /delete added in Tasks 16–18

    return app
```

- [ ] **Step 3: Implement `home_scanner/bot/handlers/__init__.py`**

```python
"""Bot command handlers."""
```

- [ ] **Step 4: Smoke-test the import path**

```bash
poetry run python -c "from home_scanner.bot.app import build_application; print('ok')"
```
Expected: `ok`.

- [ ] **Step 5: Commit**

```bash
git add backend/home_scanner/bot/app.py backend/home_scanner/bot/handlers
git commit -m "feat: bot Application factory with /start and /help"
```

---

### Task 16: `/new` wizard ConversationHandler (TDD with PTB test utils)

**Files:**
- Create: `backend/home_scanner/bot/handlers/new_search.py`
- Create: `backend/tests/bot/__init__.py`
- Create: `backend/tests/bot/test_new_wizard.py`
- Modify: `backend/home_scanner/bot/app.py` (register the handler)

- [ ] **Step 1: Write the failing test**

`backend/tests/bot/test_new_wizard.py`:
```python
"""Functional tests for the /new wizard. Uses the real ConversationHandler against
in-memory Telegram updates; the bot itself is mocked.
"""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from home_scanner.bot.handlers.new_search import (
    LOCATION,
    PRICE_MAX,
    PRICE_MIN,
    BEDROOMS,
    handle_bedrooms,
    handle_location_text,
    handle_price_max,
    handle_price_min,
    start_new,
)
from home_scanner.db.repositories import list_user_saved_searches
from sqlalchemy.orm import sessionmaker, Session


def _fake_update(text: str | None = None, chat_id: int = 100):
    update = MagicMock()
    update.effective_chat.id = chat_id
    update.effective_user.id = chat_id
    update.effective_user.username = "tester"
    update.effective_message.text = text
    update.effective_message.reply_text = AsyncMock()
    update.effective_message.reply_markdown_v2 = AsyncMock()
    update.message = update.effective_message
    return update


def _fake_context(session_factory: sessionmaker, user_data: dict | None = None):
    ctx = MagicMock()
    ctx.bot_data = {"session_factory": session_factory}
    ctx.user_data = user_data if user_data is not None else {}
    return ctx


@pytest.mark.asyncio
async def test_start_new_asks_for_location(db_engine):
    sf = sessionmaker(bind=db_engine, expire_on_commit=False)
    update = _fake_update()
    ctx = _fake_context(sf)
    next_state = await start_new(update, ctx)
    assert next_state == LOCATION
    update.effective_message.reply_markdown_v2.assert_awaited_once()


@pytest.mark.asyncio
async def test_full_happy_path_creates_saved_search(db_session: Session, db_engine):
    sf = sessionmaker(bind=db_engine, expire_on_commit=False)
    ctx_user_data: dict = {}

    update = _fake_update(text="Marousi")
    ctx = _fake_context(sf, ctx_user_data)
    next_state = await handle_location_text(update, ctx)
    assert next_state == PRICE_MIN
    assert ctx_user_data["location_slug"] == "marousi"

    update = _fake_update(text="600")
    next_state = await handle_price_min(update, ctx)
    assert next_state == PRICE_MAX
    assert ctx_user_data["min_price"] == 600

    update = _fake_update(text="1200")
    next_state = await handle_price_max(update, ctx)
    assert next_state == BEDROOMS
    assert ctx_user_data["max_price"] == 1200

    update = _fake_update(text="2")
    end_state = await handle_bedrooms(update, ctx)
    assert end_state == -1  # ConversationHandler.END

    # Pull from a fresh session to verify persisted
    with sf() as verify_session:
        from home_scanner.db.repositories import get_or_create_user
        u = get_or_create_user(
            verify_session, telegram_chat_id=100, telegram_username="tester"
        )
        rows = list_user_saved_searches(verify_session, user_id=u.id)
        assert len(rows) == 1
        s = rows[0]
        assert s.location_slug == "marousi"
        assert s.min_price == 600 and s.max_price == 1200
        assert s.min_bedrooms == 2 and s.max_bedrooms == 2
        verify_session.rollback()


@pytest.mark.asyncio
async def test_unknown_location_offers_close_matches(db_engine):
    sf = sessionmaker(bind=db_engine, expire_on_commit=False)
    ctx = _fake_context(sf, {})
    update = _fake_update(text="xyzzy nowhere")
    next_state = await handle_location_text(update, ctx)
    # Stays in LOCATION state, asks again
    assert next_state == LOCATION
```

- [ ] **Step 2: Run, expect failure**

```bash
poetry run pytest tests/bot/test_new_wizard.py -v
```

- [ ] **Step 3: Implement `home_scanner/bot/handlers/new_search.py`**

```python
"""/new wizard: location → min price → max price → bedrooms → save.

Implemented as a ConversationHandler with explicit per-state handlers so each
state is unit-testable without spinning up the Application.
"""
from __future__ import annotations

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from home_scanner.db.repositories import (
    create_saved_search,
    get_or_create_user,
)
from home_scanner.locations import find_locations

LOCATION, PRICE_MIN, PRICE_MAX, BEDROOMS = range(4)


async def start_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    if update.effective_message:
        await update.effective_message.reply_markdown_v2(
            "Where? Type a city or Athens neighbourhood "
            "\\(e\\.g\\. *Marousi*, *Athens centre*, *Thessaloniki*\\)\\."
        )
    return LOCATION


async def handle_location_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.effective_message.text or "").strip() if update.effective_message else ""
    matches = find_locations(text)
    if not matches:
        if update.effective_message:
            await update.effective_message.reply_text(
                "I don't recognise that area. Try a major Greek city or Athens neighbourhood."
            )
        return LOCATION
    chosen = matches[0]
    context.user_data["location_slug"] = chosen.slug
    context.user_data["location_name"] = chosen.name
    if update.effective_message:
        await update.effective_message.reply_text(
            f"Got it — {chosen.name}. Min monthly rent in € ('skip' for no minimum)?"
        )
    return PRICE_MIN


async def handle_price_min(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = _parse_int_or_skip(update.effective_message.text if update.effective_message else "")
    context.user_data["min_price"] = value
    if update.effective_message:
        await update.effective_message.reply_text("Max monthly rent in €?")
    return PRICE_MAX


async def handle_price_max(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = _parse_int_or_skip(update.effective_message.text if update.effective_message else "")
    context.user_data["max_price"] = value
    if update.effective_message:
        await update.effective_message.reply_text("Bedrooms? (Studio, 1, 2, 3, 4+, Any)")
    return BEDROOMS


async def handle_bedrooms(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.effective_message.text or "").strip().lower() if update.effective_message else ""
    min_br, max_br = _parse_bedrooms(text)

    sf = context.bot_data["session_factory"]
    with sf() as session:
        chat = update.effective_chat
        usr = update.effective_user
        u = get_or_create_user(
            session,
            telegram_chat_id=chat.id if chat else 0,
            telegram_username=usr.username if usr else None,
        )
        s = create_saved_search(
            session,
            user_id=u.id,
            location_slug=context.user_data["location_slug"],
            name=context.user_data.get("location_name"),
            min_price=context.user_data.get("min_price"),
            max_price=context.user_data.get("max_price"),
            min_bedrooms=min_br,
            max_bedrooms=max_br,
        )
        session.commit()

    if update.effective_message:
        await update.effective_message.reply_markdown_v2(
            f"Saved ✓ Watching for new matches in *{context.user_data['location_name']}*\\."
        )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_message:
        await update.effective_message.reply_text("OK, cancelled. Run /new when ready.")
    return ConversationHandler.END


def _parse_int_or_skip(text: str) -> int | None:
    text = text.strip().lower()
    if text in {"skip", "no", "none", "no min", "no max", ""}:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _parse_bedrooms(text: str) -> tuple[int | None, int | None]:
    text = text.strip().lower()
    if text in {"any", ""}:
        return None, None
    if text == "studio":
        return 0, 0
    if text.endswith("+"):
        try:
            return int(text[:-1]), None
        except ValueError:
            return None, None
    try:
        n = int(text)
        return n, n
    except ValueError:
        return None, None


def build_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("new", start_new)],
        states={
            LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_location_text)],
            PRICE_MIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_price_min)],
            PRICE_MAX: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_price_max)],
            BEDROOMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bedrooms)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        conversation_timeout=300,
    )
```

- [ ] **Step 4: Register handler in `home_scanner/bot/app.py`** — modify the import section and `add_handler` calls:

Replace `app.add_handler(CommandHandler("start", start))` and `app.add_handler(CommandHandler("help", help_cmd))` block with:

```python
from home_scanner.bot.handlers.new_search import build_handler as build_new_handler

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_cmd))
app.add_handler(build_new_handler())
```

- [ ] **Step 5: Run tests, expect pass**

```bash
poetry run pytest tests/bot/test_new_wizard.py -v
```
Expected: 3 passed. **If `test_full_happy_path` flakes** — likely a session-isolation issue. The test session and the wizard session aren't the same; the wizard commits its session, so the test queries through a fresh session.

- [ ] **Step 6: Commit**

```bash
git add backend/home_scanner/bot/handlers/new_search.py backend/home_scanner/bot/app.py backend/tests/bot
git commit -m "feat: bot /new wizard for creating saved searches"
```

---

### Task 17: `/list` handler

**Files:**
- Create: `backend/home_scanner/bot/handlers/list_searches.py`
- Create: `backend/tests/bot/test_list_searches.py`
- Modify: `backend/home_scanner/bot/app.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/bot/test_list_searches.py`:
```python
from unittest.mock import AsyncMock, MagicMock

import pytest
from home_scanner.bot.handlers.list_searches import list_searches
from home_scanner.db.repositories import create_saved_search, get_or_create_user
from sqlalchemy.orm import Session, sessionmaker


@pytest.mark.asyncio
async def test_list_shows_user_saved_searches(db_session: Session, db_engine):
    user = get_or_create_user(db_session, telegram_chat_id=200, telegram_username="me")
    create_saved_search(
        db_session, user_id=user.id,
        location_slug="marousi", min_price=600, max_price=1200,
        min_bedrooms=2, max_bedrooms=2,
    )
    create_saved_search(db_session, user_id=user.id, location_slug="kallithea")
    db_session.commit()

    update = MagicMock()
    update.effective_chat.id = 200
    update.effective_user.id = 200
    update.effective_user.username = "me"
    update.effective_message.reply_markdown_v2 = AsyncMock()

    sf = sessionmaker(bind=db_engine, expire_on_commit=False)
    ctx = MagicMock()
    ctx.bot_data = {"session_factory": sf}

    await list_searches(update, ctx)

    body = update.effective_message.reply_markdown_v2.await_args.args[0]
    assert "marousi" in body.lower()
    assert "kallithea" in body.lower()


@pytest.mark.asyncio
async def test_list_empty(db_engine):
    update = MagicMock()
    update.effective_chat.id = 999
    update.effective_user.id = 999
    update.effective_user.username = None
    update.effective_message.reply_markdown_v2 = AsyncMock()

    sf = sessionmaker(bind=db_engine, expire_on_commit=False)
    ctx = MagicMock()
    ctx.bot_data = {"session_factory": sf}

    await list_searches(update, ctx)
    body = update.effective_message.reply_markdown_v2.await_args.args[0]
    assert "no saved searches" in body.lower() or "create" in body.lower()
```

- [ ] **Step 2: Implement `home_scanner/bot/handlers/list_searches.py`**

```python
"""/list — show the user's saved searches."""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from home_scanner.bot.messages import escape_md
from home_scanner.db.repositories import get_or_create_user, list_user_saved_searches


async def list_searches(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    sf = context.bot_data["session_factory"]
    chat = update.effective_chat
    usr = update.effective_user
    if not (chat and usr and update.effective_message):
        return

    with sf() as session:
        u = get_or_create_user(
            session,
            telegram_chat_id=chat.id,
            telegram_username=usr.username,
        )
        rows = list_user_saved_searches(session, user_id=u.id)
        session.commit()

    if not rows:
        await update.effective_message.reply_markdown_v2(
            "You have no saved searches yet\\. Run /new to create one\\."
        )
        return

    lines = ["*Your saved searches*"]
    for s in rows:
        bounds = []
        if s.min_price is not None or s.max_price is not None:
            bounds.append(f"€{s.min_price or '–'}-{s.max_price or '–'}")
        if s.min_bedrooms is not None or s.max_bedrooms is not None:
            bounds.append(f"{s.min_bedrooms or '–'}-{s.max_bedrooms or '–'} BR")
        status = "active" if s.is_active else "paused"
        bounds_str = ", ".join(bounds) if bounds else "any"
        lines.append(
            f"`#{s.id}` {escape_md(s.location_slug)} \\({escape_md(bounds_str)}\\) — {status}"
        )
    lines.append("\nUse /pause `<id>`, /resume `<id>`, or /delete `<id>`\\.")
    await update.effective_message.reply_markdown_v2("\n".join(lines))
```

- [ ] **Step 3: Register in `home_scanner/bot/app.py`**

Add: `from home_scanner.bot.handlers.list_searches import list_searches`
Then: `app.add_handler(CommandHandler("list", list_searches))`

- [ ] **Step 4: Run tests, expect pass**

```bash
poetry run pytest tests/bot/test_list_searches.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/home_scanner/bot/handlers/list_searches.py backend/home_scanner/bot/app.py backend/tests/bot/test_list_searches.py
git commit -m "feat: bot /list command showing user's saved searches"
```

---

### Task 18: `/pause`, `/resume`, `/delete` handlers

**Files:**
- Create: `backend/home_scanner/bot/handlers/manage.py`
- Create: `backend/tests/bot/test_manage.py`
- Modify: `backend/home_scanner/bot/app.py`

- [ ] **Step 1: Implement `home_scanner/bot/handlers/manage.py`**

```python
"""/pause /resume /delete — manage existing saved searches by ID."""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from home_scanner.db.models import SavedSearch
from home_scanner.db.repositories import (
    delete_saved_search,
    get_or_create_user,
    set_saved_search_active,
)


def _parse_id(args: list[str]) -> int | None:
    if not args:
        return None
    try:
        return int(args[0])
    except ValueError:
        return None


async def pause(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _toggle(update, context, is_active=False, verb="paused")


async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _toggle(update, context, is_active=True, verb="resumed")


async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not (update.effective_message and update.effective_user):
        return
    search_id = _parse_id(context.args or [])
    if search_id is None:
        await update.effective_message.reply_text("Usage: /delete <id>")
        return
    sf = context.bot_data["session_factory"]
    with sf() as session:
        chat = update.effective_chat
        usr = update.effective_user
        u = get_or_create_user(
            session, telegram_chat_id=chat.id if chat else 0,
            telegram_username=usr.username,
        )
        s = session.get(SavedSearch, search_id)
        if s is None or s.user_id != u.id:
            session.commit()
            await update.effective_message.reply_text("No such saved search.")
            return
        delete_saved_search(session, search_id=search_id)
        session.commit()
    await update.effective_message.reply_text(f"Deleted #{search_id}.")


async def _toggle(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    is_active: bool,
    verb: str,
) -> None:
    if not (update.effective_message and update.effective_user):
        return
    search_id = _parse_id(context.args or [])
    if search_id is None:
        await update.effective_message.reply_text(f"Usage: /{verb[:-1]} <id>")
        return
    sf = context.bot_data["session_factory"]
    with sf() as session:
        chat = update.effective_chat
        usr = update.effective_user
        u = get_or_create_user(
            session, telegram_chat_id=chat.id if chat else 0,
            telegram_username=usr.username,
        )
        s = session.get(SavedSearch, search_id)
        if s is None or s.user_id != u.id:
            session.commit()
            await update.effective_message.reply_text("No such saved search.")
            return
        set_saved_search_active(session, search_id=search_id, is_active=is_active)
        session.commit()
    await update.effective_message.reply_text(f"#{search_id} {verb}.")
```

- [ ] **Step 2: Write the test**

`backend/tests/bot/test_manage.py`:
```python
from unittest.mock import AsyncMock, MagicMock

import pytest
from home_scanner.bot.handlers.manage import delete, pause, resume
from home_scanner.db.models import SavedSearch
from home_scanner.db.repositories import create_saved_search, get_or_create_user
from sqlalchemy.orm import Session, sessionmaker


def _ctx(args: list[str], db_engine):
    sf = sessionmaker(bind=db_engine, expire_on_commit=False)
    ctx = MagicMock()
    ctx.bot_data = {"session_factory": sf}
    ctx.args = args
    return ctx


def _update(chat_id: int = 300):
    update = MagicMock()
    update.effective_chat.id = chat_id
    update.effective_user.id = chat_id
    update.effective_user.username = "u"
    update.effective_message.reply_text = AsyncMock()
    return update


@pytest.mark.asyncio
async def test_pause_resume(db_session: Session, db_engine):
    user = get_or_create_user(db_session, telegram_chat_id=300, telegram_username="u")
    s = create_saved_search(db_session, user_id=user.id, location_slug="marousi")
    db_session.commit()

    await pause(_update(), _ctx([str(s.id)], db_engine))
    sf = sessionmaker(bind=db_engine, expire_on_commit=False)
    with sf() as v:
        assert v.get(SavedSearch, s.id).is_active is False
        v.rollback()

    await resume(_update(), _ctx([str(s.id)], db_engine))
    with sf() as v:
        assert v.get(SavedSearch, s.id).is_active is True
        v.rollback()


@pytest.mark.asyncio
async def test_delete(db_session: Session, db_engine):
    user = get_or_create_user(db_session, telegram_chat_id=300, telegram_username="u")
    s = create_saved_search(db_session, user_id=user.id, location_slug="kallithea")
    db_session.commit()
    sid = s.id

    await delete(_update(), _ctx([str(sid)], db_engine))
    sf = sessionmaker(bind=db_engine, expire_on_commit=False)
    with sf() as v:
        assert v.get(SavedSearch, sid) is None
        v.rollback()


@pytest.mark.asyncio
async def test_delete_other_users_search_refused(db_session: Session, db_engine):
    other = get_or_create_user(db_session, telegram_chat_id=999, telegram_username=None)
    s = create_saved_search(db_session, user_id=other.id, location_slug="x")
    db_session.commit()
    sid = s.id

    update = _update(chat_id=300)  # different user
    await delete(update, _ctx([str(sid)], db_engine))
    sf = sessionmaker(bind=db_engine, expire_on_commit=False)
    with sf() as v:
        assert v.get(SavedSearch, sid) is not None
        v.rollback()
    update.effective_message.reply_text.assert_awaited_with("No such saved search.")
```

- [ ] **Step 3: Register in `home_scanner/bot/app.py`**

Add: `from home_scanner.bot.handlers.manage import delete, pause, resume`
Then add three handlers:
```python
app.add_handler(CommandHandler("pause", pause))
app.add_handler(CommandHandler("resume", resume))
app.add_handler(CommandHandler("delete", delete))
```

- [ ] **Step 4: Run tests**

```bash
poetry run pytest tests/bot/test_manage.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/home_scanner/bot/handlers/manage.py backend/home_scanner/bot/app.py backend/tests/bot/test_manage.py
git commit -m "feat: bot /pause /resume /delete handlers"
```

---

## Phase F — Wire-up

### Task 19: CLI entrypoint + structlog setup

**Files:**
- Create: `backend/home_scanner/logging.py`
- Create: `backend/home_scanner/cli.py`
- Create: `backend/home_scanner/__main__.py`

- [ ] **Step 1: Implement `home_scanner/logging.py`**

```python
"""structlog configuration with correlation IDs."""
from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar

import structlog

_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")


def new_correlation_id() -> str:
    cid = uuid.uuid4().hex[:8]
    _correlation_id.set(cid)
    return cid


def _add_correlation_id(_, __, event_dict):
    event_dict["cid"] = _correlation_id.get()
    return event_dict


def configure(level: str = "INFO") -> None:
    logging.basicConfig(stream=sys.stdout, level=getattr(logging, level.upper()))
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _add_correlation_id,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper())),
    )
```

- [ ] **Step 2: Implement `home_scanner/cli.py`**

```python
"""CLI entrypoints. Run with `poetry run python -m home_scanner <command>`.

Subcommands:
- scrape: Run one full scrape cycle synchronously, then exit
- bot: Start the Telegram bot in long-polling mode (blocks)
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime

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


def main() -> None:
    parser = argparse.ArgumentParser(prog="home-scanner")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("scrape", help="Run one scrape cycle, then exit")
    sub.add_parser("bot", help="Run the Telegram bot in long-polling mode")
    args = parser.parse_args()

    configure_logging(Settings().log_level)

    if args.cmd == "scrape":
        asyncio.run(_scrape_once())
    elif args.cmd == "bot":
        _run_bot()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Implement `home_scanner/__main__.py`**

```python
from home_scanner.cli import main

main()
```

- [ ] **Step 4: Smoke-test the CLI argument parsing**

```bash
poetry run python -m home_scanner --help
```
Expected: argparse help output listing `scrape` and `bot` subcommands.

- [ ] **Step 5: Run the full backend test suite**

```bash
poetry run pytest -v
```
Expected: all tests pass. Total runtime ~30–60s including the Postgres testcontainer.

- [ ] **Step 6: Commit**

```bash
git add backend/home_scanner/logging.py backend/home_scanner/cli.py backend/home_scanner/__main__.py
git commit -m "feat: add CLI entrypoint and structlog configuration"
```

---

## Phase G — Polish

### Task 20: README update + manual end-to-end smoke test

**Files:**
- Modify: `README.md` (root)

- [ ] **Step 1: Replace `README.md` with the project description and dev setup**

```markdown
# home-scanner

Telegram alerts for new Greek apartment rentals on **spitogatos.gr**. Scrapes hourly, alerts you when a listing matches your saved filters.

## Status

Backend MVP complete (see [`docs/superpowers/specs/2026-05-08-home-scanner-portfolio-design.md`](docs/superpowers/specs/2026-05-08-home-scanner-portfolio-design.md) for the full design and [`docs/superpowers/plans/2026-05-08-backend-mvp.md`](docs/superpowers/plans/2026-05-08-backend-mvp.md) for the build plan).

Plan 2 (production deploy) and Plan 3 (Next.js frontend) are upcoming.

## Local setup

Requirements: Python 3.12, Poetry, Docker (for local Postgres), a [DataImpulse](https://dataimpulse.com) proxy account, a Telegram bot token from [@BotFather](https://t.me/botfather).

```bash
# 1. Install Python deps
cd backend
poetry install

# 2. Start a local Postgres
docker run -d --name home_scanner_pg \
  -p 5432:5432 \
  -e POSTGRES_PASSWORD=home_scanner \
  -e POSTGRES_USER=home_scanner \
  -e POSTGRES_DB=home_scanner \
  postgres:16-alpine

# 3. Configure secrets
cp .env.example .env
# Edit .env: fill DATAIMPULSE_*, TELEGRAM_BOT_TOKEN

# 4. Apply migrations
poetry run alembic upgrade head
```

## Running

```bash
# Start the bot (long-polling — blocks the terminal)
poetry run python -m home_scanner bot

# In another terminal: trigger one scrape cycle
poetry run python -m home_scanner scrape
```

## End-to-end smoke test

1. Start the bot: `python -m home_scanner bot`
2. In Telegram: open your bot, send `/start`, then `/new`, follow the wizard.
3. Confirm a saved search appears via `/list`.
4. Stop the bot, then run: `python -m home_scanner scrape`
5. Confirm Telegram messages arrive for matching listings.

## Tests

```bash
poetry run pytest -v
```

The test suite spins up a real Postgres in a testcontainer, so Docker must be running.

## Architecture

See [`docs/superpowers/specs/2026-05-08-home-scanner-portfolio-design.md`](docs/superpowers/specs/2026-05-08-home-scanner-portfolio-design.md).

## License

MIT — see `LICENSE`.
```

- [ ] **Step 2: Manual end-to-end smoke test**

Following the README, do a real run — make sure scrape produces actual listings in DB, the bot responds to `/start`/`/help`/`/new`/`/list`, and a `/scrape` produces Telegram messages for any matching listings.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: rewrite README with backend MVP setup and run instructions"
```

---

## Self-review

Done after writing the plan, before handoff. Findings fixed inline:

**1. Spec coverage:** every spec section has corresponding tasks:
- §3 Scope decisions → reflected in `SearchFilter` shape (T5), the rentals-only URL prefix in `build_search_url` (T5), and the location/price/bedrooms-only fields in models (T9).
- §4 Architecture & components → modules `scraper` (T5–8), `db` (T9–11), `bot` (T15–18), `notifier` (T12–14), `cli` (T19). FastAPI/api module deferred to Plan 2 ✓.
- §5 Data model → all 5 tables in T9; full migration in T10; repository helpers in T11.
- §6 Bot UX → `/start` `/help` (T15), `/new` wizard (T16), `/list` (T17), `/pause` `/resume` `/delete` (T18). Cold-start digest is implemented implicitly via `listings_matching_search` returning all current matches and `dispatch_alerts` recording them — but the digest "Found N matches" message is NOT yet shown by `/new`. Adding this to T16 is a small addition; **noted as gap**.
- §8 Error handling → 5xx retries (T7), 403/429 hard fail (T7), per-search isolation (T14), bot-blocked deactivates user (T13).
- §9 Testing → fixtures (T6), pytest infra (T4), per-module test files. Daily live canary deferred to Plan 2 (it's a CI workflow, not Python code).

**2. Placeholder scan:** ran a manual scan for "TODO", "TBD", "implement later", "Add error handling", "Similar to Task". None found in the plan. Code blocks are present in every code step. Commands are exact.

**3. Type consistency:** `SearchFilter` and `ScrapedListing` shape consistent across T5, T6, T8, T14. `compute_alerts_to_send` signature in T12 matches usage in T14. `dispatch_alerts` signature in T13 matches usage in T14. Repository helper names (`get_or_create_user`, `create_saved_search`, etc.) consistent across T11, T16, T17, T18.

**Gap fix — cold-start digest in `/new`:**

The plan's `/new` happy-path test (T16) only asserts the saved search row is created. The spec §6 says the bot's confirmation message should include "Found N current matches — latest 3 below" *and* insert all current matches into `alerts_sent` so the next hourly scrape doesn't ping the user about all of them. This is missing from T16. Adding here as **T16 amendment** — append to T16 after Step 6:

- [ ] **Step 7 (T16 amendment): Add cold-start digest to `/new` final state**

Modify `home_scanner/bot/handlers/new_search.py` `handle_bedrooms` function — after `session.commit()` in the original, before the success reply, add:

```python
from datetime import UTC, datetime

from home_scanner.db.repositories import (
    listings_matching_search,
    record_alert,
)

# inside handle_bedrooms, after `session.commit()`, before the reply:
with sf() as session:
    fresh = session.get(SavedSearch, s.id)
    matches = listings_matching_search(session, search=fresh)
    now = datetime.now(UTC)
    for listing in matches:
        record_alert(
            session,
            saved_search_id=fresh.id,
            listing_id=listing.id,
            sent_at=now,
            telegram_message_id=None,  # not actually sent — just baseline
        )
    session.commit()
    match_count = len(matches)
    sample_text = "\n\n".join(
        f"€{m.price_eur:,} · {m.bedrooms or '—'} BR · {m.location_text or ''}"
        for m in matches[:3]
    )

if update.effective_message:
    if match_count == 0:
        await update.effective_message.reply_markdown_v2(
            f"Saved ✓ Watching for new matches in *{escape_md(context.user_data['location_name'])}*\\.\n"
            f"_No current matches; you'll be pinged on new ones\\._"
        )
    else:
        await update.effective_message.reply_markdown_v2(
            f"Saved ✓ Watching *{escape_md(context.user_data['location_name'])}*\\.\n\n"
            f"Found *{match_count}* current matches — latest 3:\n\n{escape_md(sample_text)}\n\n"
            f"_New ones will arrive here as they appear\\._"
        )
return ConversationHandler.END
```

Add a corresponding test in `tests/bot/test_new_wizard.py` after the happy-path test:

```python
@pytest.mark.asyncio
async def test_cold_start_digest_records_existing_matches(db_session: Session, db_engine):
    """Existing listings matching the new search are recorded into alerts_sent
    so the user isn't flooded on the next scrape."""
    from datetime import UTC, datetime
    from home_scanner.db.repositories import listing_ids_already_alerted, upsert_listing

    upsert_listing(
        db_session, now=datetime.now(UTC),
        external_id="cold-1", url="https://x", title=None,
        price_eur=900, bedrooms=2, area_m2=None, location_text=None,
    )
    db_session.commit()

    sf = sessionmaker(bind=db_engine, expire_on_commit=False)
    ctx_user_data: dict = {}

    update = _fake_update(text="Marousi")
    ctx = _fake_context(sf, ctx_user_data)
    await handle_location_text(update, ctx)
    await handle_price_min(_fake_update(text="skip"), ctx)
    await handle_price_max(_fake_update(text="skip"), ctx)
    await handle_bedrooms(_fake_update(text="2"), ctx)

    with sf() as v:
        from home_scanner.db.repositories import get_or_create_user, list_user_saved_searches
        u = get_or_create_user(v, telegram_chat_id=100, telegram_username="tester")
        searches = list_user_saved_searches(v, user_id=u.id)
        assert len(searches) == 1
        already = listing_ids_already_alerted(v, search_id=searches[0].id)
        assert len(already) == 1
        v.rollback()
```

This closes the §6 cold-start UX gap. After applying these amendments, re-run T16's commit step (or fold into a follow-up commit titled `feat: bot /new cold-start digest seeds alerts_sent`).
