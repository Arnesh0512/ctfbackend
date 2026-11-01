import uuid

from pydantic import BaseModel, ConfigDict, Field


class LastQuestionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: uuid.UUID | None = Field(
        default=None,
        description="UUID of the question to set as the last/final question, or null to clear it",
    )


class LastQuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str = Field(..., description="Status message")
    question_id: uuid.UUID | None = Field(
        default=None,
        description="The current last question UUID, or null if cleared",
    )
    last: uuid.UUID | None = Field(
        default=None,
        description="Alias for question_id",
    )
