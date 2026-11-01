from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class GameStateOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message: Literal["ACTIVE", "PASSIVE", "PAUSED"]
    status: Literal["ACTIVE", "PASSIVE", "PAUSED"]
    start_at: datetime | None = None
    end_at: datetime | None = None
    paused_until: datetime | None = None
