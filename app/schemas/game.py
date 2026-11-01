from datetime import datetime
from typing import Literal

from pydantic import BaseModel, model_validator

from app.core.clock import LOCAL_TZ
from app.schemas.common import LocalDatetime


class GameStateOut(BaseModel):
    message: Literal["ACTIVE", "PASSIVE", "PAUSED"]
    start_at: datetime | None = None
    end_at: datetime | None = None


class TimeIn(BaseModel):
    time: datetime | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    paused_until: datetime | None = None

    @model_validator(mode="after")
    def validate_and_localize(self) -> "TimeIn":
        val = self.time or self.start_at or self.end_at or self.paused_until
        if val is None:
            raise ValueError("A datetime must be provided (e.g. {'time': '2026-11-01T10:00:00'})")
        if val.tzinfo is None:
            self.time = val.replace(tzinfo=LOCAL_TZ)
        else:
            self.time = val.astimezone(LOCAL_TZ)
        return self


class TimeOut(BaseModel):
    message: str
    start_at: LocalDatetime
    end_at: LocalDatetime
    paused_until: LocalDatetime
