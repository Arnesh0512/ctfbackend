import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Path(Base):
    __tablename__ = "paths"

    path_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    path_name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    start_region: Mapped[str] = mapped_column(Text, nullable=False)
    questions: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False
    )


class Question(Base):
    __tablename__ = "questions"

    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    monument: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False)
    story: Mapped[str] = mapped_column(Text, nullable=False)
    hint1: Mapped[str] = mapped_column(Text, nullable=False)
    hint2: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    flag: Mapped[str] = mapped_column(Text, nullable=False)
    base_points: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    current_points: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    decay_rate: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    retries: Mapped[int] = mapped_column(Integer, nullable=False)
    is_viewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    first_solved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    first_solved_by_team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.team_id", ondelete="SET NULL"), nullable=True
    )
    is_blocked: Mapped[datetime | None] = mapped_column(nullable=True)
    unlocked_by_team_id: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=True
    )
