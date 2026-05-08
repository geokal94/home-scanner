"""FastAPI dependency injection helpers."""
from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session, sessionmaker

from home_scanner.settings import Settings


def get_settings() -> Settings:
    """Override-able in tests via FastAPI's app.dependency_overrides."""
    return Settings()


def make_get_session(session_factory: sessionmaker):
    """Factory that returns a FastAPI dependency yielding a Session."""
    def _get_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session
    return _get_session


def require_scrape_secret(
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> None:
    """401 unless `Authorization: Bearer <SCRAPE_SECRET>` header matches."""
    if not settings.scrape_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scrape endpoint not configured",
        )
    expected = f"Bearer {settings.scrape_secret}"
    if authorization != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
