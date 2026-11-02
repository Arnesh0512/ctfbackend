import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GameState(Base):
    __tablename__ = "game_state"

    start_at: Mapped[datetime] = mapped_column(primary_key=True)
    end_at: Mapped[datetime] = mapped_column(nullable=False)
    paused_until: Mapped[datetime] = mapped_column(nullable=False)
    last: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, default=None)


class StorePrice(Base):
    __tablename__ = "store_prices"

    power_up: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)


class FinalLeaderboard(Base):
    __tablename__ = "final_leaderboards"

    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.team_id", ondelete="NO ACTION"), primary_key=True
    )
    team_name: Mapped[str] = mapped_column(String(256), nullable=False)
    has_reached_delhi: Mapped[datetime | None] = mapped_column(nullable=True, default=None)
    points: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    power_ups_used: Mapped[int] = mapped_column(Integer, nullable=False)
