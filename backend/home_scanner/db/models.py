"""SQLAlchemy 2 ORM models matching the spec data model."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    SmallInteger,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_chat_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False
    )
    telegram_username: Mapped[str | None] = mapped_column(Text)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    saved_searches: Mapped[list[SavedSearch]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class SavedSearch(Base):
    __tablename__ = "saved_searches"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str | None] = mapped_column(Text)
    location_slug: Mapped[str] = mapped_column(Text, nullable=False)
    min_price: Mapped[int | None] = mapped_column(Integer)
    max_price: Mapped[int | None] = mapped_column(Integer)
    min_bedrooms: Mapped[int | None] = mapped_column(SmallInteger)
    max_bedrooms: Mapped[int | None] = mapped_column(SmallInteger)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="saved_searches")


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    external_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    price_eur: Mapped[int] = mapped_column(Integer, nullable=False)
    bedrooms: Mapped[int | None] = mapped_column(SmallInteger)
    area_m2: Mapped[int | None] = mapped_column(SmallInteger)
    location_text: Mapped[str | None] = mapped_column(Text)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AlertSent(Base):
    __tablename__ = "alerts_sent"
    __table_args__ = (
        PrimaryKeyConstraint("saved_search_id", "listing_id"),
    )

    saved_search_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("saved_searches.id", ondelete="CASCADE"),
        nullable=False,
    )
    listing_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
    )
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger)


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text, nullable=False)  # running|ok|failed
    searches_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    listings_seen: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_alerts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errors: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
