"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-08-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # create_all on startup covers SQLite/Postgres for MVP.
    # This revision exists so Alembic has a baseline.
    pass


def downgrade() -> None:
    pass
