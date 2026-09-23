"""Add webhook delivery timestamp.

Revision ID: 20260923_0002
Revises: 20260923_0001
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260923_0002"
down_revision: str | None = "20260923_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "payments",
        sa.Column("webhook_delivered_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("payments", "webhook_delivered_at")
