"""Create gemini_usage table for API token tracking.

Revision ID: 009
Revises: 008
Create Date: 2026-04-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "gemini_usage",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("analysis_type", sa.String(30), nullable=False),
        sa.Column("batch_size", sa.Integer, nullable=False, server_default="0"),
        sa.Column("prompt_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("model_name", sa.String(50), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    # Index for daily aggregation queries
    op.create_index(
        "idx_gemini_usage_created_at",
        "gemini_usage",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_gemini_usage_created_at")
    op.drop_table("gemini_usage")
