"""Create rumor_scores table for AI-generated rumor assessments.

Revision ID: 029
Revises: 028
Create Date: 2025-07-25
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "029"
down_revision: Union[str, None] = "028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rumor_scores",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ticker_id", sa.Integer(), nullable=False),
        sa.Column("scored_date", sa.Date(), nullable=False),
        sa.Column("credibility_score", sa.Integer(), nullable=False),
        sa.Column("impact_score", sa.Integer(), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("key_claims", JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("post_ids", JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["ticker_id"], ["tickers.id"]),
        sa.UniqueConstraint("ticker_id", "scored_date", name="uq_rumor_scores_ticker_date"),
    )
    op.create_index(
        "ix_rumor_scores_ticker_date",
        "rumor_scores",
        ["ticker_id", sa.text("scored_date DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_rumor_scores_ticker_date", table_name="rumor_scores")
    op.drop_table("rumor_scores")
