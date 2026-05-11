"""Centralised settings, loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()  # No-op in production; reads .env in local dev


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    telegram_bot_token: str
    log_level: str = "INFO"
    # DataImpulse proxy is optional. xe.gr does not require a Greek-residential IP;
    # the fields stay so we can re-enable proxying for other sources in the future.
    dataimpulse_user: str = ""
    dataimpulse_pass: str = ""
    dataimpulse_host: str = ""
    dataimpulse_port: str = ""
    # Plan 2 (production deploy):
    scrape_secret: str = ""
    telegram_webhook_secret: str = ""
    sentry_dsn: str = ""
    public_base_url: str = ""
    cors_origins: str = ""  # comma-separated list of allowed origins

    def __init__(self) -> None:  # type: ignore[no-redef]
        # frozen dataclass + env-driven init: bypass __setattr__ via object.__setattr__
        object.__setattr__(self, "database_url", os.environ["DATABASE_URL"])
        object.__setattr__(self, "telegram_bot_token", os.environ["TELEGRAM_BOT_TOKEN"])
        object.__setattr__(self, "log_level", os.environ.get("LOG_LEVEL", "INFO"))
        object.__setattr__(self, "dataimpulse_user", os.environ.get("DATAIMPULSE_USER", ""))
        object.__setattr__(self, "dataimpulse_pass", os.environ.get("DATAIMPULSE_PASS", ""))
        object.__setattr__(self, "dataimpulse_host", os.environ.get("DATAIMPULSE_HOST", ""))
        object.__setattr__(self, "dataimpulse_port", os.environ.get("DATAIMPULSE_PORT", ""))
        object.__setattr__(self, "scrape_secret", os.environ.get("SCRAPE_SECRET", ""))
        object.__setattr__(
            self, "telegram_webhook_secret", os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
        )
        object.__setattr__(self, "sentry_dsn", os.environ.get("SENTRY_DSN", ""))
        object.__setattr__(self, "public_base_url", os.environ.get("PUBLIC_BASE_URL", ""))
        object.__setattr__(self, "cors_origins", os.environ.get("CORS_ORIGINS", ""))

    @property
    def proxy_url(self) -> str | None:
        """Return the proxy URL if all DataImpulse fields are configured, else None.

        xe.gr scraping doesn't need a proxy; callers should pass None to
        ListingClient in the common path.
        """
        if not (
            self.dataimpulse_user
            and self.dataimpulse_pass
            and self.dataimpulse_host
            and self.dataimpulse_port
        ):
            return None
        return (
            f"http://{self.dataimpulse_user}:{self.dataimpulse_pass}"
            f"@{self.dataimpulse_host}:{self.dataimpulse_port}"
        )

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS env var (comma-separated) into a list. Empty → []."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
