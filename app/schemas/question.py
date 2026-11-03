from datetime import datetime
from decimal import Decimal
from enum import StrEnum
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import LocalDatetime


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
    end_point: Decimal = Field(..., ge=0, description="Floor / minimum score for the question")
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


class QuestionSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question_id: uuid.UUID = Field(..., description="Question ID")
    title: str = Field(..., description="Question title")
    current_points: Decimal = Field(..., description="Current point value")
    location: str = Field(..., description="Formatted location <state-monument>")


class QuestionDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question_id: uuid.UUID = Field(..., description="Question ID")
    title: str = Field(..., description="Question title")
    monument: str = Field(..., description="Monument name")
    state: str = Field(..., description="State name")
    story: str = Field(..., description="Challenge story/description")
    hint1: str = Field(..., description="First hint")
    hint2: str = Field(..., description="Second hint")
    file_path: list[str] | None = Field(default=None, description="List of file links")
    flag: str = Field(..., description="Flag string")
    base_points: Decimal = Field(..., description="Base points")
    current_points: Decimal = Field(..., description="Current points")
    end_point: Decimal = Field(..., description="Minimum points floor")
    retries: int = Field(..., description="Allowed retries")
    is_viewed: LocalDatetime | None = Field(default=None, description="First viewed timestamp")
    first_solved_at: LocalDatetime | None = Field(default=None, description="First solved timestamp")
    first_solved_by_team_id: uuid.UUID | None = Field(default=None, description="First solver team ID")
    is_blocked: LocalDatetime | None = Field(default=None, description="Blocked until timestamp")
    unlocked_by_team_id: list[uuid.UUID] | None = Field(default=None, description="Teams that unlocked question")


class QuestionUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, description="Question title")
    monument: str | None = Field(default=None, min_length=1, description="Monument name")
    state: str | None = Field(default=None, min_length=1, description="State name")
    story: str | None = Field(default=None, min_length=1, description="Challenge story")
    hint1: str | None = Field(default=None, min_length=1, description="First hint")
    hint2: str | None = Field(default=None, min_length=1, description="Second hint")
    flag: str | None = Field(default=None, min_length=1, description="Flag string")
    base_points: Decimal | None = Field(default=None, ge=0, description="Base points")
    end_point: Decimal | None = Field(default=None, ge=0, description="Floor / minimum score")
    retries: int | None = Field(default=None, ge=0, description="Allowed retry count")

    @field_validator("title", "monument", "state", "story", "hint1", "hint2", "flag")
    @classmethod
    def _validate_non_empty(cls, v: str | None) -> str | None:
        if v is not None:
            stripped = v.strip()
            if not stripped:
                raise ValueError("Field cannot be empty or only whitespace")
            return stripped
        return v


class QuestionDeleteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str = Field(..., description="Status message")
    question_id: uuid.UUID = Field(..., description="Deleted question ID")


class TeamCurrentQuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    current_question_id: uuid.UUID | None = Field(
        default=None, description="Current question ID assigned to the team"
    )
    current_path_id: uuid.UUID | None = Field(
        default=None, description="Current path ID assigned to the team"
    )


class TeamQuestionViewIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path_id: uuid.UUID = Field(..., description="Selected route/path ID")
    frontend_timestamp: LocalDatetime = Field(..., description="Client interaction timestamp")


class TeamQuestionViewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question_id: uuid.UUID
    title: str
    monument: str
    state: str
    story: str
    file_path: list[str] | None = None
    base_points: Decimal
    is_viewed: LocalDatetime | None = None
    is_blocked: LocalDatetime | None = None


class TeamQuestionSaveIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path_id: uuid.UUID = Field(..., description="Active path ID")
    frontend_timestamp: LocalDatetime = Field(..., description="Client interaction timestamp")
    answer: str = Field(..., min_length=1, description="Submitted flag answer")


class TeamQuestionSaveOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    correct: bool = Field(..., description="Whether the answer was correct")
    message: str = Field(..., description="Result message")
    next_question_id: uuid.UUID | None = Field(default=None, description="Next question UUID if available")
    has_reached_delhi: bool = Field(default=False, description="Whether the team has reached Delhi")
    points_awarded: Decimal = Field(default=Decimal("0.00"), description="Points awarded for this question")
    current_points: Decimal = Field(..., description="Updated total team points")
    actions: list[dict[str, str]] = Field(default_factory=list, description="Enabled actions")
    remaining_retries: int | None = Field(default=None, description="Remaining retries if answer is wrong")


class HintType(StrEnum):
    HINT1 = "HINT1"
    HINT2 = "HINT2"
    HINT12 = "HINT12"


class TeamQuestionHintIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path_id: uuid.UUID = Field(..., description="Active path ID")
    frontend_timestamp: LocalDatetime = Field(..., description="Client interaction timestamp")
    hint_type: HintType = Field(..., description="Hint type to purchase or view (HINT1, HINT2, HINT12)")


class TeamQuestionHintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    hint1: str | None = Field(default=None, description="Hint 1 text if unlocked")
    hint2: str | None = Field(default=None, description="Hint 2 text if unlocked")
    points_deducted: Decimal = Field(default=Decimal("0.00"), description="Points deducted for hint purchase")
    current_points: Decimal = Field(..., description="Updated total team points")


class TeamQuestionRetryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path_id: uuid.UUID = Field(..., description="Active path ID")
    frontend_timestamp: LocalDatetime = Field(..., description="Client interaction timestamp")


class TeamQuestionRetryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str = Field(default="Retry purchased successfully", description="Status message")
    points_deducted: Decimal = Field(default=Decimal("0.00"), description="Points deducted for retry purchase")
    current_points: Decimal = Field(..., description="Updated total team points")
    remaining_retries: int = Field(default=1, description="Remaining retries available after purchase")


class TeamQuestionBlockIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path_id: uuid.UUID = Field(..., description="Active path ID")
    frontend_timestamp: LocalDatetime = Field(..., description="Client interaction timestamp")
    point: Decimal = Field(..., gt=0, description="Points to spend on blocking the question")


class TeamQuestionBlockOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str = Field(default="Question blocked successfully", description="Status message")
    is_blocked: LocalDatetime = Field(..., description="Blocked until timestamp in IST")
    points_deducted: Decimal = Field(default=Decimal("0.00"), description="Points deducted for blocking")
    current_points: Decimal = Field(..., description="Updated total team points")


class TeamQuestionUnblockIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path_id: uuid.UUID = Field(..., description="Active path ID")
    frontend_timestamp: LocalDatetime = Field(..., description="Client interaction timestamp")


class TeamQuestionUnblockOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str = Field(default="Question unblocked successfully", description="Status message")
    points_deducted: Decimal = Field(default=Decimal("0.00"), description="Points deducted for unblocking")
    current_points: Decimal = Field(..., description="Updated total team points")


class TeamQuestionSkipIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path_id: uuid.UUID = Field(..., description="Active path ID")
    frontend_timestamp: LocalDatetime = Field(..., description="Client interaction timestamp")


class TeamQuestionSkipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str = Field(default="Question skipped successfully", description="Status message")
    next_question_id: uuid.UUID = Field(..., description="Next question UUID")
    current_points: Decimal = Field(..., description="Current team points")
