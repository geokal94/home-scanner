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
