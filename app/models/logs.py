import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, PrimaryKeyConstraint, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.models.base import Base
from app.models.enums import QuestionEvent, str_enum


class TeamLog(Base):
    __tablename__ = "team_logs"
    __table_args__ = (
        PrimaryKeyConstraint("team_id", "created_at", name="pk_team_logs"),
        Index("ix_team_logs_team_created", "team_id", "created_at"),
    )

    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.team_id", ondelete="CASCADE"), primary_key=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.question_id", ondelete="CASCADE"), nullable=False
    )
    path_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("paths.path_id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[QuestionEvent] = mapped_column(str_enum(QuestionEvent), nullable=False)
    created_at: Mapped[datetime] = mapped_column(primary_key=True, default=utcnow)
    points: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
