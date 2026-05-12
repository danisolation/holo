"""add simulator tables

Revision ID: 273292a3289a
Revises: 032
Create Date: 2026-05-12 17:05:19.308383

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '273292a3289a'
down_revision: Union[str, Sequence[str], None] = '032'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create simulator_portfolios, simulator_trades, simulator_lots tables."""
    op.create_table('simulator_portfolios',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), server_default='default', nullable=False),
        sa.Column('starting_capital', sa.Numeric(precision=16, scale=2), server_default='100000000', nullable=False),
        sa.Column('current_cash', sa.Numeric(precision=16, scale=2), server_default='100000000', nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('simulator_trades',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('portfolio_id', sa.BigInteger(), nullable=False),
        sa.Column('ticker_id', sa.Integer(), nullable=False),
        sa.Column('daily_pick_id', sa.BigInteger(), nullable=True),
        sa.Column('side', sa.String(length=4), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('broker_fee', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('sell_tax', sa.Numeric(precision=12, scale=2), server_default='0', nullable=False),
        sa.Column('total_fee', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('gross_pnl', sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column('net_pnl', sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('source', sa.String(length=10), nullable=False),
        sa.Column('ai_signal_skipped', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('user_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['daily_pick_id'], ['daily_picks.id'], ),
        sa.ForeignKeyConstraint(['portfolio_id'], ['simulator_portfolios.id'], ),
        sa.ForeignKeyConstraint(['ticker_id'], ['tickers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('simulator_lots',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('portfolio_id', sa.BigInteger(), nullable=False),
        sa.Column('ticker_id', sa.Integer(), nullable=False),
        sa.Column('trade_id', sa.BigInteger(), nullable=False),
        sa.Column('buy_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('remaining_quantity', sa.Integer(), nullable=False),
        sa.Column('buy_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['portfolio_id'], ['simulator_portfolios.id'], ),
        sa.ForeignKeyConstraint(['ticker_id'], ['tickers.id'], ),
        sa.ForeignKeyConstraint(['trade_id'], ['simulator_trades.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Drop simulator tables."""
    op.drop_table('simulator_lots')
    op.drop_table('simulator_trades')
    op.drop_table('simulator_portfolios')
