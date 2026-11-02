"""add_event_type_to_pk_team_logs

Revision ID: 3dfbd3e3f6c9
Revises: 0ed8a8675133
Create Date: 2026-11-02
"""

from collections.abc import Sequence

from alembic import op


revision: str = '3dfbd3e3f6c9'
down_revision: str | None = '0ed8a8675133'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE team_logs DROP CONSTRAINT IF EXISTS team_logs_pkey")
    op.execute("ALTER TABLE team_logs ADD CONSTRAINT team_logs_pkey PRIMARY KEY (team_id, created_at, event_type)")


def downgrade() -> None:
    op.execute("ALTER TABLE team_logs DROP CONSTRAINT IF EXISTS team_logs_pkey")
    op.execute("ALTER TABLE team_logs ADD CONSTRAINT team_logs_pkey PRIMARY KEY (team_id, created_at)")
