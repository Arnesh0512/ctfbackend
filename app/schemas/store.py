from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

ALLOWED_POWER_UPS = (
    "RETRY",
    "HINT1",
    "HINT2",
    "HINT12",
    "BLOCK",
    "UNBLOCK",
    "DEVTIME",
    "PATHCHANGEC",
    "PATHCHANGET",
)

PowerUpName = Literal[
    "RETRY",
    "HINT1",
    "HINT2",
    "HINT12",
    "BLOCK",
    "UNBLOCK",
    "DEVTIME",
    "PATHCHANGEC",
    "PATHCHANGET",
]


class StorePriceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    power_up: PowerUpName = Field(
        ...,
        description="Name of the power-up (RETRY, HINT1, HINT2, HINT12, BLOCK, UNBLOCK, DEVTIME, PATHCHANGEC, PATHCHANGET)",
    )
    value: Decimal = Field(..., ge=0, description="Cost / value of the power-up")

    @field_validator("power_up", mode="before")
    @classmethod
    def validate_power_up(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.strip().upper()
        if v not in ALLOWED_POWER_UPS:
            raise ValueError(
                f"Invalid power_up '{v}'. Allowed power-ups: {', '.join(ALLOWED_POWER_UPS)}"
            )
        return v


# Alias for backward compatibility
StorePriceIn = StorePriceUpdate


class StorePriceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    power_up: str
    value: Decimal | None = None
