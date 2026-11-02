"""change_is_viewed_to_timestamptz_in_questions

Revision ID: 0ed8a8675133
Revises: d747cbe08a47
Create Date: 2026-11-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0ed8a8675133'
down_revision: str | None = 'd747cbe08a47'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE questions 
          ALTER COLUMN is_viewed DROP DEFAULT,
          ALTER COLUMN is_viewed TYPE TIMESTAMPTZ USING (NULL),
          ALTER COLUMN is_viewed DROP NOT NULL;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE questions 
          ALTER COLUMN is_viewed DROP DEFAULT,
          ALTER COLUMN is_viewed TYPE BOOLEAN USING (false),
          ALTER COLUMN is_viewed SET DEFAULT false,
          ALTER COLUMN is_viewed SET NOT NULL;
        """
    )
