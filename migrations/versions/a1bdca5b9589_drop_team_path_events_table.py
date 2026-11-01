from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "a1bdca5b9589"
down_revision: str | None = "4cf779b15979"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_team_path_events_team_id", table_name="team_path_events")
    op.drop_table("team_path_events")


def downgrade() -> None:
    op.create_table(
        "team_path_events",
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("path_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("points", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.ForeignKeyConstraint(
            ["path_id"],
            ["paths.path_id"],
            name=op.f("fk_team_path_events_path_id_paths"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.question_id"],
            name=op.f("fk_team_path_events_question_id_questions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.team_id"],
            name=op.f("fk_team_path_events_team_id_teams"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "team_id", "path_id", "created_at", name=op.f("pk_team_path_events")
        ),
    )
    op.create_index(
        "ix_team_path_events_team_id",
        "team_path_events",
        ["team_id"],
        unique=False,
    )
