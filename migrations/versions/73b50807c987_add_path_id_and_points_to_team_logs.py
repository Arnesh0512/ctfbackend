from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "73b50807c987"
down_revision: str | None = "0d51a23e7e09"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "team_logs",
        sa.Column("path_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "team_logs",
        sa.Column("points", sa.Numeric(precision=10, scale=2), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_team_logs_path_id_paths"),
        "team_logs",
        "paths",
        ["path_id"],
        ["path_id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_team_logs_path_id_paths"),
        "team_logs",
        type_="foreignkey",
    )
    op.drop_column("team_logs", "points")
    op.drop_column("team_logs", "path_id")
