"""dual_portfolio_split

Revision ID: ad67af37a9a1
Revises: 069904041094
Create Date: 2026-05-15 11:55:27.816875

Phase 107: Split single simulator portfolio into dual AI/User portfolios.
- Rename existing "default" portfolio to "user" (preserves trade history)
- Create fresh "ai" portfolio with 100M VND starting capital
- Add unique constraint on portfolio name
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'ad67af37a9a1'
down_revision: Union[str, Sequence[str], None] = '069904041094'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Split default portfolio into ai + user."""
    # Rename existing "default" portfolio to "user" (preserves manual trade history)
    op.execute("UPDATE simulator_portfolios SET name = 'user' WHERE name = 'default'")

    # Create "ai" portfolio with 100M VND starting capital
    op.execute("""
        INSERT INTO simulator_portfolios (name, starting_capital, current_cash)
        VALUES ('ai', 100000000, 100000000)
    """)

    # Add unique constraint on name (prevent duplicates)
    op.create_unique_constraint('uq_simulator_portfolios_name', 'simulator_portfolios', ['name'])


def downgrade() -> None:
    """Revert to single default portfolio."""
    op.drop_constraint('uq_simulator_portfolios_name', 'simulator_portfolios')
    op.execute("DELETE FROM simulator_portfolios WHERE name = 'ai'")
    op.execute("UPDATE simulator_portfolios SET name = 'default' WHERE name = 'user'")
