"""apply_final_schema_revisions

Revision ID: fc263c31c5dd
Revises: a1bdca5b9589
Create Date: 2026-11-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = 'fc263c31c5dd'
down_revision: str | None = 'a1bdca5b9589'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. game_state: add 'last' UUID column
    op.add_column("game_state", sa.Column("last", postgresql.UUID(as_uuid=True), nullable=True))

    # 2. store_prices: drop 'multiplier' column
    op.drop_column("store_prices", "multiplier")

    # 3. questions: drop 'decay_rate' column, add 'end_point' column
    op.drop_column("questions", "decay_rate")
    op.add_column(
        "questions",
        sa.Column("end_point", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
    )

    # 4. teams: add 'otp_valid', drop 'playthrough', alter 'has_reached_delhi' to TIMESTAMPTZ, add FK to questions
    op.add_column(
        "teams",
        sa.Column("otp_valid", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.drop_column("teams", "playthrough")
    # Drop existing boolean default and not-null before altering type to timestamptz
    op.alter_column("teams", "has_reached_delhi", server_default=None)
    op.alter_column("teams", "has_reached_delhi", nullable=True)
    op.alter_column(
        "teams",
        "has_reached_delhi",
        type_=sa.DateTime(timezone=True),
        postgresql_using="CASE WHEN has_reached_delhi THEN now() ELSE NULL END",
    )
    op.create_foreign_key(
        "fk_teams_current_question_id_questions",
        "teams",
        "questions",
        ["current_question_id"],
        ["question_id"],
        ondelete="SET NULL",
    )

    # 5. final_leaderboards: drop 'playthrough', alter 'has_reached_delhi' to TIMESTAMPTZ, add FK to teams
    op.drop_column("final_leaderboards", "playthrough")
    # Drop existing boolean default and not-null before altering type to timestamptz
    op.alter_column("final_leaderboards", "has_reached_delhi", server_default=None)
    op.alter_column("final_leaderboards", "has_reached_delhi", nullable=True)
    op.alter_column(
        "final_leaderboards",
        "has_reached_delhi",
        type_=sa.DateTime(timezone=True),
        postgresql_using="CASE WHEN has_reached_delhi THEN now() ELSE NULL END",
    )
    op.create_foreign_key(
        "fk_final_leaderboards_team_id_teams",
        "final_leaderboards",
        "teams",
        ["team_id"],
        ["team_id"],
        ondelete="NO ACTION",
    )

    # 6. team_logs: update foreign keys to ON DELETE NO ACTION
    op.drop_constraint("fk_team_logs_question_id_questions", "team_logs", type_="foreignkey")
    op.create_foreign_key(
        "fk_team_logs_question_id_questions",
        "team_logs",
        "questions",
        ["question_id"],
        ["question_id"],
        ondelete="NO ACTION",
    )
    op.drop_constraint("fk_team_logs_path_id_paths", "team_logs", type_="foreignkey")
    op.create_foreign_key(
        "fk_team_logs_path_id_paths",
        "team_logs",
        "paths",
        ["path_id"],
        ["path_id"],
        ondelete="NO ACTION",
    )


def downgrade() -> None:
    # 6. team_logs: revert foreign keys to ON DELETE CASCADE
    op.drop_constraint("fk_team_logs_path_id_paths", "team_logs", type_="foreignkey")
    op.create_foreign_key(
        "fk_team_logs_path_id_paths",
        "team_logs",
        "paths",
        ["path_id"],
        ["path_id"],
        ondelete="CASCADE",
    )
    op.drop_constraint("fk_team_logs_question_id_questions", "team_logs", type_="foreignkey")
    op.create_foreign_key(
        "fk_team_logs_question_id_questions",
        "team_logs",
        "questions",
        ["question_id"],
        ["question_id"],
        ondelete="CASCADE",
    )

    # 5. final_leaderboards: drop FK, revert 'has_reached_delhi' to boolean, add 'playthrough'
    op.drop_constraint("fk_final_leaderboards_team_id_teams", "final_leaderboards", type_="foreignkey")
    op.alter_column(
        "final_leaderboards",
        "has_reached_delhi",
        type_=sa.Boolean(),
        postgresql_using="CASE WHEN has_reached_delhi IS NOT NULL THEN true ELSE false END",
        server_default=sa.text("false"),
        nullable=False,
    )
    op.add_column(
        "final_leaderboards",
        sa.Column("playthrough", sa.Time(), nullable=False, server_default="00:00:00"),
    )

    # 4. teams: drop FK, revert 'has_reached_delhi' to boolean, add 'playthrough', drop 'otp_valid'
    op.drop_constraint("fk_teams_current_question_id_questions", "teams", type_="foreignkey")
    op.alter_column(
        "teams",
        "has_reached_delhi",
        type_=sa.Boolean(),
        postgresql_using="CASE WHEN has_reached_delhi IS NOT NULL THEN true ELSE false END",
        server_default=sa.text("false"),
        nullable=False,
    )
    op.add_column(
        "teams",
        sa.Column("playthrough", sa.Time(), nullable=False, server_default="00:00:00"),
    )
    op.drop_column("teams", "otp_valid")

    # 3. questions: drop 'end_point', add 'decay_rate'
    op.drop_column("questions", "end_point")
    op.add_column(
        "questions",
        sa.Column("decay_rate", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
    )

    # 2. store_prices: add 'multiplier'
    op.add_column("store_prices", sa.Column("multiplier", sa.Numeric(10, 2), nullable=True))

    # 1. game_state: drop 'last'
    op.drop_column("game_state", "last")
