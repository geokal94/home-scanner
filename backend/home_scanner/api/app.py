"""FastAPI application factory."""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

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
    """Assemble the FastAPI app. `session_factory` is injected so tests can swap
    in a test sessionmaker bound to a testcontainer Postgres."""
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
