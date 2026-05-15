"""merge simulator and sector_analyses branches

Revision ID: 069904041094
Revises: 273292a3289a, 6ae2a74c3387
Create Date: 2026-05-15 11:29:03.964213

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '069904041094'
down_revision: Union[str, Sequence[str], None] = ('273292a3289a', '6ae2a74c3387')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
