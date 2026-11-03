"""update_game_state_pause_columns

Revision ID: efc854ac8669
Revises: 3dfbd3e3f6c9
Create Date: 2026-11-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'efc854ac8669'
down_revision: str | None = '3dfbd3e3f6c9'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("game_state", "paused_until")
    op.add_column("game_state", sa.Column("pause_start_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("game_state", sa.Column("pause_end_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("game_state", "pause_end_at")
    op.drop_column("game_state", "pause_start_at")
    op.add_column("game_state", sa.Column("paused_until", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
