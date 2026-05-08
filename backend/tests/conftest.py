"""Shared pytest fixtures.

Spins up a real Postgres container per test session for DB-backed tests.
Tests that don't need a DB simply don't request the `db_session` fixture.
"""
from __future__ import annotations

from collections.abc import Generator

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
    """A fresh session per test; TRUNCATEs all tables at end so commits made by
    code under test (e.g. bot handlers opening their own sessions) are still
    cleaned up."""
    session_factory = sessionmaker(bind=db_engine, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        # Clean up: truncate all tables so committed data (from this session or
        # from other sessions opened during the test) doesn't leak between tests.
        from home_scanner.db.models import Base
        with db_engine.begin() as conn:
            table_names = ", ".join(
                f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables)
            )
            from sqlalchemy import text
            conn.execute(text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE"))


@pytest.fixture(scope="session", autouse=True)
def _create_schema(db_engine: Engine) -> None:
    from home_scanner.db.models import Base
    Base.metadata.create_all(db_engine)
