"""Shared fixtures for API tests."""
from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture(autouse=True)
def _api_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings() reads required env vars at app build time. Provide dummy
    values so build_app() doesn't KeyError in tests."""
    monkeypatch.setenv("DATAIMPULSE_USER", "test_user")
    monkeypatch.setenv("DATAIMPULSE_PASS", "test_pass")
    monkeypatch.setenv("DATAIMPULSE_HOST", "gw.example.com")
    monkeypatch.setenv("DATAIMPULSE_PORT", "823")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@h:5432/db")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")


@pytest.fixture(autouse=True)
def _mock_telegram_bot(monkeypatch: pytest.MonkeyPatch) -> None:
    """The FastAPI lifespan calls bot.initialize() which hits the real Telegram
    API to verify the token. Stub out the network calls so tests can run offline.
    Also seed `_bot_user` so Application.start()/Bot.id don't blow up."""
    from telegram import Bot, User

    fake_user = User(id=42, is_bot=True, first_name="test", username="test_bot")

    async def fake_initialize(self: Bot) -> None:  # type: ignore[no-redef]
        if self._initialized:
            return
        self._bot_user = fake_user
        self._initialized = True

    async def fake_shutdown(self: Bot) -> None:  # type: ignore[no-redef]
        self._initialized = False

    monkeypatch.setattr(Bot, "initialize", fake_initialize)
    monkeypatch.setattr(Bot, "shutdown", fake_shutdown)
    monkeypatch.setattr(Bot, "get_me", AsyncMock(return_value=fake_user))


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
