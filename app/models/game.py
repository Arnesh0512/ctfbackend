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
    pause_start_at: Mapped[datetime | None] = mapped_column(nullable=True, default=None)
    pause_end_at: Mapped[datetime | None] = mapped_column(nullable=True, default=None)
    last: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, default=None)

    @property
    def paused_until(self) -> datetime | None:
        """Compatibility property for legacy code that has not migrated yet."""
        return self.pause_end_at or self.pause_start_at

    @paused_until.setter
    def paused_until(self, value: datetime | None) -> None:
        self.pause_end_at = value


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
