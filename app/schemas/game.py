from typing import Literal

from pydantic import BaseModel


class GameStateOut(BaseModel):
    message: Literal["ACTIVE", "PASSIVE", "PAUSED"]
