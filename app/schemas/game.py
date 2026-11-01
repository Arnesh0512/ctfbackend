from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class GameStateOut(BaseModel):
    message: Literal["ACTIVE", "PASSIVE", "PAUSED"]
    start_at: datetime | None = None
    end_at: datetime | None = None
