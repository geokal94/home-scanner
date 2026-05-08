"""FastAPI application factory."""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

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
