"""Create rumors table for Fireant community posts.

Revision ID: 028
Revises: 027
Create Date: 2025-07-25
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "028"
down_revision: Union[str, None] = "027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rumors",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ticker_id", sa.Integer(), nullable=False),
        sa.Column("post_id", sa.BigInteger(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("author_name", sa.String(200), nullable=False),
        sa.Column("is_authentic", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("total_likes", sa.Integer(), server_default=sa.text("0")),
        sa.Column("total_replies", sa.Integer(), server_default=sa.text("0")),
        sa.Column("fireant_sentiment", sa.Integer(), server_default=sa.text("0")),
        sa.Column("posted_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["ticker_id"], ["tickers.id"]),
        sa.UniqueConstraint("post_id", name="uq_rumors_post_id"),
    )
    op.create_index(
        "ix_rumors_ticker_posted",
        "rumors",
        ["ticker_id", sa.text("posted_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_rumors_ticker_posted", table_name="rumors")
    op.drop_table("rumors")
