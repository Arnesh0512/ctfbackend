from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "4cf779b15979"
down_revision: str | None = "73b50807c987"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Remove last field from game_state
    op.drop_column("game_state", "last")

    # 2. Update team_logs columns to NOT NULL and foreign keys to CASCADE
    op.drop_constraint("fk_team_logs_question_id_questions", "team_logs", type_="foreignkey")
    op.alter_column("team_logs", "question_id", nullable=False)
    op.create_foreign_key(
        "fk_team_logs_question_id_questions",
        "team_logs",
        "questions",
        ["question_id"],
        ["question_id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("fk_team_logs_path_id_paths", "team_logs", type_="foreignkey")
    op.alter_column("team_logs", "path_id", nullable=False)
    op.create_foreign_key(
        "fk_team_logs_path_id_paths",
        "team_logs",
        "paths",
        ["path_id"],
        ["path_id"],
        ondelete="CASCADE",
    )

    op.alter_column("team_logs", "points", nullable=False)


def downgrade() -> None:
    op.add_column("game_state", sa.Column("last", postgresql.UUID(as_uuid=True), nullable=True))

    op.alter_column("team_logs", "points", nullable=True)

    op.drop_constraint("fk_team_logs_path_id_paths", "team_logs", type_="foreignkey")
    op.alter_column("team_logs", "path_id", nullable=True)
    op.create_foreign_key(
        "fk_team_logs_path_id_paths",
        "team_logs",
        "paths",
        ["path_id"],
        ["path_id"],
        ondelete="SET NULL",
    )

    op.drop_constraint("fk_team_logs_question_id_questions", "team_logs", type_="foreignkey")
    op.alter_column("team_logs", "question_id", nullable=True)
    op.create_foreign_key(
        "fk_team_logs_question_id_questions",
        "team_logs",
        "questions",
        ["question_id"],
        ["question_id"],
        ondelete="SET NULL",
    )
