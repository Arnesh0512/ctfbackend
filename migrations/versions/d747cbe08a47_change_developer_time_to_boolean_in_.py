"""change_developer_time_to_boolean_in_teams

Revision ID: d747cbe08a47
Revises: d324971d226c
Create Date: 2026-11-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'd747cbe08a47'
down_revision: str | None = 'd324971d226c'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE teams 
          ALTER COLUMN developer_time DROP DEFAULT,
          ALTER COLUMN developer_time TYPE BOOLEAN USING (FALSE),
          ALTER COLUMN developer_time SET DEFAULT FALSE,
          ALTER COLUMN developer_time SET NOT NULL;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE teams 
          ALTER COLUMN developer_time DROP DEFAULT,
          ALTER COLUMN developer_time TYPE TIME WITHOUT TIME ZONE USING ('00:00:00'::TIME),
          ALTER COLUMN developer_time SET DEFAULT '00:00:00'::TIME,
          ALTER COLUMN developer_time DROP NOT NULL;
        """
    )
