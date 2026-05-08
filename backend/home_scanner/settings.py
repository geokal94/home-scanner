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
