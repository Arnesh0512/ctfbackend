import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QuestionCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, description="Question title")
    monument: str = Field(..., min_length=1, description="Monument name")
    state: str = Field(..., min_length=1, description="State name")
    story: str = Field(..., min_length=1, description="Challenge story/description")
    hint1: str = Field(..., min_length=1, description="First hint")
    hint2: str = Field(..., min_length=1, description="Second hint")
    file_path: list[str] | None = Field(
        default=None,
        description="Optional list of file URLs / links",
    )
    flag: str = Field(..., min_length=1, description="Flag string")
    base_points: Decimal = Field(..., ge=0, description="Base points for the question")
    retries: int = Field(..., ge=0, description="Allowed retry count")

    @field_validator("title", "monument", "state", "story", "hint1", "hint2", "flag")
    @classmethod
    def _validate_non_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Field cannot be empty or only whitespace")
        return stripped


class QuestionCreateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question_id: uuid.UUID = Field(..., description="Generated question ID")
