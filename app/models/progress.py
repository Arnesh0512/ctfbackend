import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, PrimaryKeyConstraint, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TeamQuestionState(Base):
    __tablename__ = "team_question_states"
    __table_args__ = (
        PrimaryKeyConstraint("team_id", "question_id", name="pk_team_question_states"),
    )

    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.team_id", ondelete="CASCADE"), primary_key=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.question_id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    attempts_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extra_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hint1_owned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    hint2_owned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    points_awarded: Mapped[Decimal] = mapped_column(Numeric, nullable=False, default=Decimal(0))
    viewed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    solved_at: Mapped[datetime | None] = mapped_column(nullable=True)
