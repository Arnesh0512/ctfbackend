import uuid
from datetime import datetime, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import LocalDatetime


class LeaderDetails(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=256, description="Leader full name")
    contact: str = Field(..., min_length=1, max_length=64, description="Leader contact phone number")
    email: str = Field(..., min_length=1, max_length=256, description="Leader email address")


class CreateTeamIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    team_name: str = Field(..., min_length=1, max_length=256, description="Display name of the team")
    team_members: list[str] = Field(default_factory=list, description="List of team member names")
    leader_details: LeaderDetails = Field(..., description="Leader contact details")
    username: str = Field(..., min_length=1, max_length=256, description="Unique login username")
    password: str = Field(..., min_length=1, max_length=256, description="Team login password")


class TeamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    team_id: uuid.UUID
    team_name: str
    team_members: list[str] | None = None
    leader_details: LeaderDetails
    username: str
    points: Decimal
    powerups_used: int
    playthrough: time
    has_reached_delhi: bool
    current_path_id: uuid.UUID | None = None
    current_question_id: uuid.UUID | None = None
    frozen_until: datetime | None = None
    developer_time: time | None = None
    skip: uuid.UUID | None = None


# Team authentication & session models
class TeamLogin(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)


class TeamSession(BaseModel):
    team_id: uuid.UUID
    team_name: str
    access_token: str
    token_type: str = "bearer"


class TeamMe(BaseModel):
    team_id: uuid.UUID
    team_name: str
    points: Decimal
    powerups_used: int
    playthrough: time
    has_reached_delhi: bool
    current_path_id: uuid.UUID | None = None
    frozen_until: LocalDatetime | None = None
    leader_details: LeaderDetails | None = None
    team_members: list[str] = Field(default_factory=list)
