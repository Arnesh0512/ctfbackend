import uuid
from datetime import datetime, time
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, Numeric, String, Text, Time
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.content import Path
from app.models.question import Question


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (
        CheckConstraint("points >= 0", name="ck_teams_points_non_negative"),
        CheckConstraint(
            "leader_details ? 'name' AND leader_details ? 'contact' AND leader_details ? 'email' AND leader_details ? 'enrollment' AND leader_details ? 'college'",
            name="ck_teams_leader_details_fields",
        ),
    )

    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    team_name: Mapped[str] = mapped_column(String(256), nullable=False)
    team_members: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True, default=list)
    leader_details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    username: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(256), nullable=False)
    points: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    powerups_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    playthrough: Mapped[time] = mapped_column(Time, nullable=False, default=time(0, 0, 0))
    has_reached_delhi: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reached_delhi_at: Mapped[datetime | None] = mapped_column(nullable=True, default=None)

    current_path_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("paths.path_id", ondelete="SET NULL"), nullable=True, default=None
    )
    current_question_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, default=None
    )
    frozen_until: Mapped[datetime | None] = mapped_column(nullable=True, default=None)
    developer_time: Mapped[time | None] = mapped_column(Time, nullable=True, default=time(0, 0, 0))
    skip: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, default=None)
