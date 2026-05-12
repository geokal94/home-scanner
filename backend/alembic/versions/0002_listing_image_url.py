"""add image_url to listings

Revision ID: 0002_listing_image
Revises: 679da7d0f446
Create Date: 2026-05-12 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_listing_image"
down_revision: str | Sequence[str] | None = "679da7d0f446"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("listings", sa.Column("image_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("listings", "image_url")
