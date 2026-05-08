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
