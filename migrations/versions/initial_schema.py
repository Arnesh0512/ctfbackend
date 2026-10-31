from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Admins
    op.create_table(
        "admins",
        sa.Column("admin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("admin_name", sa.String(length=256), nullable=False),
        sa.Column("passcode", sa.String(length=256), nullable=False),
        sa.PrimaryKeyConstraint("admin_id", name=op.f("pk_admins")),
        sa.UniqueConstraint("admin_name", name=op.f("uq_admins_admin_name")),
    )

    # 2. Game State
    op.create_table(
        "game_state",
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paused_until", sa.DateTime(timezone=True), nullable=False),
    )

    # 3. Paths
    op.create_table(
        "paths",
        sa.Column("path_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("path_name", sa.Text(), nullable=False),
        sa.Column("start_region", sa.Text(), nullable=False),
        sa.Column("questions", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False),
        sa.PrimaryKeyConstraint("path_id", name=op.f("pk_paths")),
        sa.UniqueConstraint("path_name", name=op.f("uq_paths_path_name")),
    )

    # 4. Store Prices
    op.create_table(
        "store_prices",
        sa.Column("power_up", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Numeric(), nullable=True),
        sa.Column("multiplier", sa.Numeric(), nullable=True),
        sa.PrimaryKeyConstraint("power_up", name=op.f("pk_store_prices")),
    )

    # 5. Final Leaderboards
    op.create_table(
        "final_leaderboards",
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_name", sa.String(length=256), nullable=False),
        sa.Column("has_reached_delhi", sa.Boolean(), nullable=False),
        sa.Column("playthrough", sa.Time(), nullable=False),
        sa.Column("points", sa.Numeric(), nullable=False),
        sa.Column("power_ups_used", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("team_id", name=op.f("pk_final_leaderboards")),
    )

    # 6. Teams
    op.create_table(
        "teams",
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_name", sa.String(length=256), nullable=False),
        sa.Column("leader_details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("team_members", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("username", sa.String(length=256), nullable=False),
        sa.Column("password", sa.String(length=256), nullable=False),
        sa.Column("points", sa.Numeric(), nullable=False, server_default="0.00"),
        sa.Column("powerups_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("playthrough", sa.Time(), nullable=False, server_default="00:00:00"),
        sa.Column("has_reached_delhi", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("current_path_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("current_question_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("frozen_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("developer_time", sa.Time(), nullable=True),
        sa.Column("skip", postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint("points >= 0", name=op.f("ck_teams_points_non_negative")),
        sa.CheckConstraint(
            "leader_details ? 'name' AND leader_details ? 'contact' AND leader_details ? 'email'",
            name=op.f("ck_teams_leader_details_fields"),
        ),
        sa.ForeignKeyConstraint(
            ["current_path_id"],
            ["paths.path_id"],
            name=op.f("fk_teams_current_path_id_paths"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("team_id", name=op.f("pk_teams")),
        sa.UniqueConstraint("username", name=op.f("uq_teams_username")),
    )

    # 7. Questions
    op.create_table(
        "questions",
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("monument", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("story", sa.Text(), nullable=False),
        sa.Column("hint1", sa.Text(), nullable=False),
        sa.Column("hint2", sa.Text(), nullable=False),
        sa.Column("file_path", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("flag", sa.Text(), nullable=False),
        sa.Column("base_points", sa.Numeric(), nullable=False),
        sa.Column("current_points", sa.Numeric(), nullable=False),
        sa.Column("decay_rate", sa.Numeric(), nullable=False),
        sa.Column("retries", sa.Integer(), nullable=False),
        sa.Column("is_viewed", sa.Boolean(), nullable=False),
        sa.Column("first_solved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_solved_by_team_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_blocked", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "unlocked_by_team_id",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["first_solved_by_team_id"],
            ["teams.team_id"],
            name=op.f("fk_questions_first_solved_by_team_id_teams"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("question_id", name=op.f("pk_questions")),
    )

    # 8. Team Logs
    op.create_table(
        "team_logs",
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.question_id"],
            name=op.f("fk_team_logs_question_id_questions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.team_id"],
            name=op.f("fk_team_logs_team_id_teams"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("team_id", "created_at", name=op.f("pk_team_logs")),
    )
    op.create_index(
        "ix_team_logs_team_created",
        "team_logs",
        ["team_id", "created_at"],
        unique=False,
    )

    # 9. Team Path Events
    op.create_table(
        "team_path_events",
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("path_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
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

    # 10. Team Question States
    op.create_table(
        "team_question_states",
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("attempts_used", sa.Integer(), nullable=False),
        sa.Column("extra_retries", sa.Integer(), nullable=False),
        sa.Column("hint1_owned", sa.Boolean(), nullable=False),
        sa.Column("hint2_owned", sa.Boolean(), nullable=False),
        sa.Column("points_awarded", sa.Numeric(), nullable=False),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("solved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.question_id"],
            name=op.f("fk_team_question_states_question_id_questions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.team_id"],
            name=op.f("fk_team_question_states_team_id_teams"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "team_id", "question_id", name=op.f("pk_team_question_states")
        ),
    )


def downgrade() -> None:
    op.drop_table("team_question_states")
    op.drop_index("ix_team_path_events_team_id", table_name="team_path_events")
    op.drop_table("team_path_events")
    op.drop_index("ix_team_logs_team_created", table_name="team_logs")
    op.drop_table("team_logs")
    op.drop_table("questions")
    op.drop_table("teams")
    op.drop_table("final_leaderboards")
    op.drop_table("store_prices")
    op.drop_table("paths")
    op.drop_table("game_state")
    op.drop_table("admins")
