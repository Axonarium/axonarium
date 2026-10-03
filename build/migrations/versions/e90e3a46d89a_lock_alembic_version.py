"""Keep Supabase's API roles out of Alembic's version table.

Supabase gives anon and authenticated full access to every new table in public by default, so the public
key could read and rewrite alembic_version. Row-level security with no policy for them, plus revoking their
privileges, closes that; the deploy role owns the table and is unaffected.

Revision ID: e90e3a46d89a
Revises: acc8ca5f39d2
Create Date: 2026-10-03 12:32:42.972030

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e90e3a46d89a'
down_revision: Union[str, Sequence[str], None] = 'acc8ca5f39d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("alter table public.alembic_version enable row level security")
    op.execute("revoke all on public.alembic_version from anon, authenticated")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("alter table public.alembic_version disable row level security")
