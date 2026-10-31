import uuid
from datetime import datetime, time
from decimal import Decimal

from sqlalchemy import Boolean, Integer, Numeric, String, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GameState(Base):
    __tablename__ = "game_state"

    start_at: Mapped[datetime] = mapped_column(primary_key=True)
    end_at: Mapped[datetime] = mapped_column(nullable=False)
    paused_until: Mapped[datetime] = mapped_column(nullable=False)


class StorePrice(Base):
    __tablename__ = "store_prices"

    power_up: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    multiplier: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)


class FinalLeaderboard(Base):
    __tablename__ = "final_leaderboards"

    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    team_name: Mapped[str] = mapped_column(String(256), nullable=False)
    has_reached_delhi: Mapped[bool] = mapped_column(Boolean, nullable=False)
    playthrough: Mapped[time] = mapped_column(Time, nullable=False)
    points: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    power_ups_used: Mapped[int] = mapped_column(Integer, nullable=False)
