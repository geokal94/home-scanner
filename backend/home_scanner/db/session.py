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
