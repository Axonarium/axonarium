"""Sources: how many claims cite each, set by the build, for the site's source pages.

Revision ID: 5e0c1d7a9b42
Revises: ebfab78bd77e
Create Date: 2026-10-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '5e0c1d7a9b42'
down_revision: Union[str, Sequence[str], None] = 'ebfab78bd77e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('sources', sa.Column('n_claims', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('sources', 'n_claims')
