from decimal import Decimal
from typing import Literal
import uuid

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import LocalDatetime


class PathCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    path_name: str = Field(..., min_length=1, description="Unique name of the path")
    question_ids: list[uuid.UUID] = Field(
        ...,
        validation_alias=AliasChoices("question_ids", "questions"),
        serialization_alias="question_ids",
        min_length=1,
        description="List of question UUIDs for this path",
    )

    @field_validator("path_name")
    @classmethod
    def _validate_path_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("path_name cannot be empty or only whitespace")
        return stripped

    @field_validator("question_ids")
    @classmethod
    def _validate_question_ids(cls, v: list[uuid.UUID]) -> list[uuid.UUID]:
        if not v:
            raise ValueError("question_ids cannot be empty")
        seen = set()
        duplicates = []
        for qid in v:
            if qid in seen:
                duplicates.append(str(qid))
            seen.add(qid)
        if duplicates:
            raise ValueError(f"Duplicate question_ids provided in request: {duplicates}")
        return v


class PathCreateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    path_id: uuid.UUID = Field(..., description="Generated path ID")


class PathQuestionItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question_id: uuid.UUID = Field(..., description="Question ID")
    location: str = Field(..., description="Formatted location <state-monument>")


class PathSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    path_id: uuid.UUID = Field(..., description="Path ID")
    path_name: str = Field(..., description="Path name")
    questions: list[PathQuestionItem] = Field(
        default_factory=list,
        description="Ordered list of questions with formatted locations",
    )


class PathUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    path_name: str | None = Field(default=None, min_length=1, description="Path name")
    question_ids: list[uuid.UUID] | None = Field(
        default=None,
        validation_alias=AliasChoices("question_ids", "questions"),
        serialization_alias="question_ids",
        min_length=1,
        description="List of question UUIDs for this path",
    )

    @field_validator("path_name")
    @classmethod
    def _validate_path_name(cls, v: str | None) -> str | None:
        if v is not None:
            stripped = v.strip()
            if not stripped:
                raise ValueError("path_name cannot be empty or only whitespace")
            return stripped
        return v

    @field_validator("question_ids")
    @classmethod
    def _validate_question_ids(cls, v: list[uuid.UUID] | None) -> list[uuid.UUID] | None:
        if v is not None:
            if not v:
                raise ValueError("question_ids cannot be empty")
            seen = set()
            duplicates = []
            for qid in v:
                if qid in seen:
                    duplicates.append(str(qid))
                seen.add(qid)
            if duplicates:
                raise ValueError(f"Duplicate question_ids provided in request: {duplicates}")
        return v


class PathDeleteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str = Field(..., description="Status message")
    path_id: uuid.UUID = Field(..., description="Deleted path ID")


class TeamPathQuestionItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question_id: uuid.UUID = Field(..., description="Question UUID")
    state: str = Field(..., description="State name")
    monument: str = Field(..., description="Monument name")


class TeamPathOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    path_id: uuid.UUID = Field(..., description="Path ID")
    question_list: list[TeamPathQuestionItem] = Field(
        default_factory=list,
        description="Ordered list of questions in the path with location details",
    )


class TeamCurrentPathOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    current_path_id: uuid.UUID | None = Field(
        default=None, description="Current path ID assigned to the team"
    )


PathChangeType = Literal["COST", "TIME"]


class TeamPathChangeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_path_id: uuid.UUID = Field(..., description="ID of the new path to change to")
    type: PathChangeType = Field(..., description="Change mechanism: COST (deduct points) or TIME (freeze team)")
    question_id: uuid.UUID = Field(..., description="Current question ID team is on")
    frontend_timestamp: LocalDatetime = Field(..., description="Client interaction timestamp in IST")


class TeamPathChangeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str = Field(..., description="Status message")
    current_path_id: uuid.UUID = Field(..., description="New current path ID")
    current_question_id: uuid.UUID = Field(..., description="New current question ID")
    points: Decimal = Field(..., description="Current team points")
    frozen_until: LocalDatetime | None = Field(default=None, description="Frozen until timestamp (if TIME type)")
