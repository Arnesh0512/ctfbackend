from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0f15edd787b8"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("paths", "start_region")


def downgrade() -> None:
    op.add_column("paths", sa.Column("start_region", sa.Text(), nullable=False))
