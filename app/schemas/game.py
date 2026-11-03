from typing import Literal
import uuid

from pydantic import BaseModel, model_validator

from app.core.clock import to_local
from app.schemas.common import LocalDatetime


class GameStateOut(BaseModel):
    message: Literal["ACTIVE", "PASSIVE", "PAUSED"]
    start_at: LocalDatetime | None = None
    end_at: LocalDatetime | None = None
    pause_start_at: LocalDatetime | None = None
    pause_end_at: LocalDatetime | None = None
    last: uuid.UUID | None = None


class TimeIn(BaseModel):
    time: LocalDatetime | None = None
    start_at: LocalDatetime | None = None
    end_at: LocalDatetime | None = None
    paused_until: LocalDatetime | None = None

    @model_validator(mode="after")
    def validate_and_localize(self) -> "TimeIn":
        val = self.time or self.start_at or self.end_at or self.paused_until
        if val is None:
            raise ValueError("A datetime must be provided (e.g. {'time': '2026-11-01T10:00:00'})")
        self.time = to_local(val)
        return self


class TimeOut(BaseModel):
    message: str
    start_at: LocalDatetime
    end_at: LocalDatetime
    paused_until: LocalDatetime | None = None
    pause_start_at: LocalDatetime | None = None
    pause_end_at: LocalDatetime | None = None
