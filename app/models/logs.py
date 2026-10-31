import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, PrimaryKeyConstraint, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.models.base import Base


class TeamLog(Base):
    __tablename__ = "team_logs"
    __table_args__ = (
        PrimaryKeyConstraint("team_id", "created_at", name="pk_team_logs"),
        Index("ix_team_logs_team_created", "team_id", "created_at"),
    )

    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.team_id", ondelete="CASCADE"), primary_key=True
    )
    question_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.question_id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(primary_key=True, default=utcnow)
    points: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True, default=None)


class TeamPathEvent(Base):
    __tablename__ = "team_path_events"
    __table_args__ = (
        PrimaryKeyConstraint("team_id", "path_id", "created_at", name="pk_team_path_events"),
        Index("ix_team_path_events_team_id", "team_id"),
    )

    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.team_id", ondelete="CASCADE"), primary_key=True
    )
    path_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("paths.path_id", ondelete="CASCADE"), primary_key=True
    )
    question_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.question_id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(primary_key=True, default=utcnow)
    points: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True, default=None)
