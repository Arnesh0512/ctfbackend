from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class StorePriceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    power_up: str = Field(..., min_length=1, max_length=64, description="Power-up name")
    value: Decimal | None = Field(default=None, ge=0, description="Cost / value of the power-up")


class StorePriceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    power_up: str
    value: Decimal | None = None
